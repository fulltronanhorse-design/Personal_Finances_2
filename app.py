"""
Finance Tracker - Production-Ready Local Edition
A secure, robust, and observable personal finance analyzer.
"""

import os
import json
import logging
import shutil
import datetime
import hashlib
import pandas as pd
from flask import Flask, request, jsonify, send_from_directory, send_file
from dateutil import parser as date_parser
from werkzeug.utils import secure_filename

# --- Configuration (Centralized Settings) ---
class Config:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    LOG_DIR = os.path.join(BASE_DIR, 'logs')
    
    TRANSACTIONS_FILE = os.path.join(DATA_DIR, 'transactions.json')
    RULES_FILE = os.path.join(DATA_DIR, 'rules.json')
    
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB Max File Size
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
    PORT = 5000
    DEBUG = False  # Set to True for development debugging
    
    # Default Categories if rules file is missing
    DEFAULT_RULES = {
        "Food & Dining": ["restaurant", "cafe", "starbucks", "mcdonalds", "pizza", "grocery", "supermarket", "trader joe", "whole foods"],
        "Transportation": ["uber", "lyft", "taxi", "gas", "shell", "exxon", "parking", "toll", "transit", "metro"],
        "Utilities": ["electric", "water", "gas utility", "internet", "comcast", "verizon", "phone bill", "mobile"],
        "Entertainment": ["netflix", "spotify", "cinema", "movie", "theater", "concert", "game", "steam"],
        "Shopping": ["amazon", "target", "walmart", "clothing", "shoes", "electronics", "best buy"],
        "Healthcare": ["pharmacy", "cvs", "walgreens", "doctor", "hospital", "dentist", "vision"],
        "Income": ["payroll", "direct deposit", "salary", "refund", "dividend", "interest"],
        "Fees & Charges": ["fee", "penalty", "late charge", "service charge", "atm fee"],
        "Uncategorized": []
    }

# --- Initialize App & Logging ---
app = Flask(__name__, static_folder='static')
app.config.from_object(Config)

# Ensure directories exist
for directory in [Config.DATA_DIR, Config.BACKUP_DIR, Config.UPLOAD_FOLDER, Config.LOG_DIR]:
    os.makedirs(directory, exist_ok=True)

# Setup Structured Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(funcName)s] - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(Config.LOG_DIR, 'app.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Limit file size for uploads
app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH

# --- Helper Functions ---

def get_rules():
    """Load categorization rules from file or defaults."""
    if os.path.exists(Config.RULES_FILE):
        try:
            with open(Config.RULES_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading rules file: {e}")
            return Config.DEFAULT_RULES
    return Config.DEFAULT_RULES

def save_rules(rules):
    """Save rules with backup."""
    create_backup()
    try:
        with open(Config.RULES_FILE, 'w') as f:
            json.dump(rules, f, indent=2)
        logger.info("Rules updated successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to save rules: {e}")
        return False

def get_transactions():
    """Load transactions from file."""
    if os.path.exists(Config.TRANSACTIONS_FILE):
        try:
            with open(Config.TRANSACTIONS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading transactions file: {e}")
            return []
    return []

def save_transactions(transactions):
    """Save transactions with backup."""
    create_backup()
    try:
        with open(Config.TRANSACTIONS_FILE, 'w') as f:
            json.dump(transactions, f, indent=2)
        logger.info(f"Saved {len(transactions)} transactions.")
        return True
    except Exception as e:
        logger.error(f"Failed to save transactions: {e}")
        return False

def create_backup():
    """Create a timestamped backup of data files."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    try:
        if os.path.exists(Config.TRANSACTIONS_FILE):
            shutil.copy2(
                Config.TRANSACTIONS_FILE, 
                os.path.join(Config.BACKUP_DIR, f"transactions_{timestamp}.json")
            )
        if os.path.exists(Config.RULES_FILE):
            shutil.copy2(
                Config.RULES_FILE, 
                os.path.join(Config.BACKUP_DIR, f"rules_{timestamp}.json")
            )
        logger.info(f"Backup created: {timestamp}")
        
        # Cleanup old backups (keep last 10)
        backups = sorted([os.path.join(Config.BACKUP_DIR, f) for f in os.listdir(Config.BACKUP_DIR)])
        while len(backups) > 10:
            os.remove(backups.pop(0))
            
    except Exception as e:
        logger.error(f"Backup failed: {e}")

def generate_transaction_id(date_str, description, amount):
    """Generate a unique ID for a transaction."""
    content = f"{date_str}{description}{amount}"
    return hashlib.md5(content.encode()).hexdigest()

def categorize_transaction(description, rules):
    """Categorize a transaction based on rules."""
    desc_lower = description.lower()
    for category, keywords in rules.items():
        if category == "Uncategorized":
            continue
        for keyword in keywords:
            if keyword.lower() in desc_lower:
                return category
    return "Uncategorized"

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def parse_file(filepath):
    """Parse CSV or Excel file into standardized transactions."""
    logger.info(f"Parsing file: {filepath}")
    try:
        if filepath.endswith('.csv'):
            # Try multiple encodings for CSV
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    df = pd.read_csv(filepath, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
        else:
            df = pd.read_excel(filepath)
        
        if df.empty:
            raise ValueError("File is empty")
        
        # Normalize column names
        df.columns = [str(c).lower().strip() for c in df.columns]
        
        # Identify columns (Heuristic)
        date_col = next((c for c in df.columns if 'date' in c), None)
        desc_col = next((c for c in df.columns if 'desc' in c or 'name' in c or 'merchant' in c), None)
        amount_col = next((c for c in df.columns if 'amount' in c or 'value' in c or 'charge' in c), None)
        
        if not all([date_col, desc_col, amount_col]):
            # Fallback: assume first 3 columns
            if len(df.columns) >= 3:
                date_col, desc_col, amount_col = df.columns[0], df.columns[1], df.columns[2]
                logger.warning(f"Could not auto-detect columns. Using first 3: {date_col}, {desc_col}, {amount_col}")
            else:
                raise ValueError("Could not identify Date, Description, and Amount columns.")
        
        transactions = []
        rules = get_rules()
        
        for _, row in df.iterrows():
            try:
                date_val = row[date_col]
                # Handle Excel dates vs string dates
                if isinstance(date_val, pd.Timestamp):
                    date_str = date_val.strftime('%Y-%m-%d')
                else:
                    date_str = str(date_val)
                    # Try to parse if messy
                    try:
                        date_str = date_parser.parse(date_str).strftime('%Y-%m-%d')
                    except:
                        pass
                
                description = str(row[desc_col])
                amount_raw = row[amount_col]
                
                # Clean amount (handle strings like "$1,200.00" or "(100.00)")
                if isinstance(amount_raw, str):
                    amount_clean = amount_raw.replace('$', '').replace(',', '').replace(' ', '')
                    if amount_clean.startswith('(') and amount_clean.endswith(')'):
                        amount = float(amount_clean[1:-1]) * -1
                    else:
                        amount = float(amount_clean)
                else:
                    amount = float(amount_raw)
                
                category = categorize_transaction(description, rules)
                tx_id = generate_transaction_id(date_str, description, amount)
                
                transactions.append({
                    "id": tx_id,
                    "date": date_str,
                    "description": description,
                    "amount": amount,
                    "category": category,
                    "source": "upload"
                })
            except Exception as row_err:
                logger.warning(f"Skipping malformed row: {row_err}")
                continue
        
        logger.info(f"Parsed {len(transactions)} valid transactions.")
        return transactions
        
    except Exception as e:
        logger.error(f"File parsing failed: {e}")
        raise ValueError(f"Failed to parse file: {str(e)}")

# --- Routes ---

@app.route('/health')
def health_check():
    """Production-style health check endpoint."""
    usage = shutil.disk_usage(Config.BASE_DIR)
    percent_used = (usage.used / usage.total) * 100
    status = {
        "status": "healthy",
        "disk_usage_percent": round(percent_used, 2),
        "data_exists": os.path.exists(Config.TRANSACTIONS_FILE)
    }
    if percent_used > 90:
        status["status"] = "warning: disk full"
    return jsonify(status), 200

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Allowed: CSV, XLSX, XLS"}), 400
    
    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        new_transactions = parse_file(filepath)
        
        # Merge with existing
        existing = get_transactions()
        existing_ids = {t['id'] for t in existing}
        
        count_new = 0
        for tx in new_transactions:
            if tx['id'] not in existing_ids:
                existing.append(tx)
                count_new += 1
        
        save_transactions(existing)
        
        # Clean up upload
        os.remove(filepath)
        
        logger.info(f"Upload successful: {count_new} new transactions added.")
        return jsonify({
            "message": f"Successfully processed {len(new_transactions)} rows. Added {count_new} new transactions.",
            "count": count_new
        }), 200
        
    except ValueError as ve:
        logger.error(f"Validation error: {ve}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        # Clean up on error
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({"error": "Internal server error during processing"}), 500

@app.route('/api/transactions', methods=['GET'])
def get_all_transactions():
    transactions = get_transactions()
    # Sort by date descending
    transactions.sort(key=lambda x: x.get('date', ''), reverse=True)
    return jsonify(transactions)

@app.route('/api/rules', methods=['GET'])
def get_all_rules():
    return jsonify(get_rules())

@app.route('/api/rules', methods=['POST'])
def update_rules():
    new_rules = request.json
    if not new_rules:
        return jsonify({"error": "No data provided"}), 400
    
    if save_rules(new_rules):
        # Re-categorize existing transactions
        transactions = get_transactions()
        for tx in transactions:
            tx['category'] = categorize_transaction(tx['description'], new_rules)
        save_transactions(transactions)
        return jsonify({"message": "Rules updated and transactions re-categorized"}), 200
    return jsonify({"error": "Failed to save rules"}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    transactions = get_transactions()
    if not transactions:
        return jsonify({"total": 0, "by_category": {}, "monthly": {}})
    
    total_income = sum(t['amount'] for t in transactions if t['amount'] > 0)
    total_expense = sum(t['amount'] for t in transactions if t['amount'] < 0)
    
    by_category = {}
    for t in transactions:
        cat = t['category']
        by_category[cat] = by_category.get(cat, 0) + t['amount']
    
    # Simple monthly aggregation
    monthly = {}
    for t in transactions:
        month = t['date'][:7] # YYYY-MM
        monthly[month] = monthly.get(month, 0) + t['amount']
    
    return jsonify({
        "total_income": total_income,
        "total_expense": total_expense,
        "net": total_income + total_expense,
        "by_category": by_category,
        "monthly": dict(sorted(monthly.items(), reverse=True))
    })

@app.route('/backup/<filename>')
def download_backup(filename):
    return send_from_directory(Config.BACKUP_DIR, filename, as_attachment=True)

@app.route('/api/backups', methods=['GET'])
def list_backups():
    files = sorted(os.listdir(Config.BACKUP_DIR), reverse=True)
    return jsonify(files)

if __name__ == '__main__':
    logger.info(f"Starting Finance Tracker on port {Config.PORT}")
    logger.info(f"Data directory: {Config.DATA_DIR}")
    logger.info(f"Backup directory: {Config.BACKUP_DIR}")
    
    # Initialize data files if missing
    if not os.path.exists(Config.RULES_FILE):
        save_rules(Config.DEFAULT_RULES)
    if not os.path.exists(Config.TRANSACTIONS_FILE):
        save_transactions([])
        
    app.run(host='0.0.0.0', port=Config.PORT, debug=Config.DEBUG)
