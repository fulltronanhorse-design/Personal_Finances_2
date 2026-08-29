"""
Finance Tracker - Personal Finance Statement Analyzer
A secure, locally-run application for managing bank statements and expenses.
"""

import os
import json
import csv
import shutil
import hashlib
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DATA_FOLDER'] = 'data'
app.config['BACKUP_FOLDER'] = 'backup'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure directories exist
for folder in ['UPLOAD_FOLDER', 'DATA_FOLDER', 'BACKUP_FOLDER']:
    os.makedirs(app.config[folder], exist_ok=True)

# Default categorization rules
DEFAULT_RULES = {
    "Food & Dining": ["restaurant", "cafe", "starbucks", "mcdonalds", "pizza", "burger", "grill", "bistro", "diner", "food", "delivery", "doordash", "ubereats"],
    "Groceries": ["grocery", "supermarket", "walmart", "target", "costco", "trader joe", "whole foods", "safeway", "kroger", "aldi"],
    "Transportation": ["uber", "lyft", "taxi", "gas", "fuel", "parking", "toll", "metro", "transit", "airline", "hotel"],
    "Shopping": ["amazon", "ebay", "mall", "store", "clothing", "shoes", "electronics", "best buy", "apple"],
    "Entertainment": ["netflix", "spotify", "movie", "theater", "concert", "game", "steam", "playstation", "xbox"],
    "Bills & Utilities": ["electric", "water", "gas", "internet", "phone", "cable", "utility", "bill"],
    "Healthcare": ["pharmacy", "doctor", "hospital", "clinic", "dental", "medical", "cvs", "walgreens"],
    "Income": ["salary", "paycheck", "deposit", "transfer", "refund", "dividend", "interest"],
    "Investment": ["brokerage", "401k", "ira", "stock", "bond", "mutual fund", "etf"],
    "Fees & Charges": ["fee", "charge", "penalty", "late fee", "overdraft", "service charge"],
    "Cash Withdrawal": ["atm", "withdrawal", "cash back"],
    "Uncategorized": []
}

def get_rules():
    """Load categorization rules from file or return defaults."""
    rules_file = os.path.join(app.config['DATA_FOLDER'], 'rules.json')
    if os.path.exists(rules_file):
        with open(rules_file, 'r') as f:
            return json.load(f)
    return DEFAULT_RULES

def save_rules(rules):
    """Save rules with backup."""
    rules_file = os.path.join(app.config['DATA_FOLDER'], 'rules.json')
    create_backup(rules_file)
    with open(rules_file, 'w') as f:
        json.dump(rules, f, indent=2)

def get_transactions():
    """Load all transactions from file."""
    tx_file = os.path.join(app.config['DATA_FOLDER'], 'transactions.json')
    if os.path.exists(tx_file):
        with open(tx_file, 'r') as f:
            return json.load(f)
    return []

def save_transactions(transactions):
    """Save transactions with backup."""
    tx_file = os.path.join(app.config['DATA_FOLDER'], 'transactions.json')
    create_backup(tx_file)
    with open(tx_file, 'w') as f:
        json.dump(transactions, f, indent=2)

def create_backup(file_path):
    """Create a timestamped backup of a file before modification."""
    if os.path.exists(file_path):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.basename(file_path)
        backup_name = f"{filename}.{timestamp}.bak"
        backup_path = os.path.join(app.config['BACKUP_FOLDER'], backup_name)
        shutil.copy2(file_path, backup_path)

def generate_transaction_id(description, timestamp=None):
    """Generate a unique ID for a transaction."""
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    unique_string = f"{timestamp}-{description}"
    return hashlib.md5(unique_string.encode()).hexdigest()[:16]

def categorize_transaction(description, rules):
    """Categorize a transaction based on description and rules."""
    desc_lower = description.lower()
    
    for category, keywords in rules.items():
        if not keywords:
            continue
        for keyword in keywords:
            if keyword.lower() in desc_lower:
                return category
    
    return "Uncategorized"

def parse_csv_file(filepath):
    """Parse a CSV file and extract transactions."""
    transactions = []
    
    try:
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    sample = f.read(4096)
                    f.seek(0)
                    
                    try:
                        dialect = csv.Sniffer().sniff(sample)
                    except csv.Error:
                        dialect = csv.excel
                    
                    reader = csv.DictReader(f, dialect=dialect)
                    
                    if not reader.fieldnames:
                        continue
                    
                    fieldnames_lower = [f.lower() if f else '' for f in reader.fieldnames]
                    
                    date_col = None
                    desc_col = None
                    amount_col = None
                    
                    for i, name in enumerate(fieldnames_lower):
                        if any(x in name for x in ['date', 'time', 'posted']):
                            date_col = reader.fieldnames[i]
                            break
                    if date_col is None and reader.fieldnames:
                        date_col = reader.fieldnames[0]
                    
                    for i, name in enumerate(fieldnames_lower):
                        if any(x in name for x in ['desc', 'narrative', 'memo', 'detail', 'merchant']):
                            desc_col = reader.fieldnames[i]
                            break
                    if desc_col is None and len(reader.fieldnames) > 1:
                        desc_col = reader.fieldnames[1]
                    
                    for i, name in enumerate(fieldnames_lower):
                        if any(x in name for x in ['amount', 'value', 'debit', 'credit', 'sum']):
                            amount_col = reader.fieldnames[i]
                            break
                    if amount_col is None and len(reader.fieldnames) > 2:
                        amount_col = reader.fieldnames[2]
                    
                    if not all([date_col, desc_col, amount_col]):
                        continue
                    
                    for row in reader:
                        try:
                            date_str = row.get(date_col, '')
                            description = row.get(desc_col, '')
                            amount_str = row.get(amount_col, '0')
                            
                            amount_str = amount_str.replace('$', '').replace(',', '').strip()
                            try:
                                amount = float(amount_str)
                            except ValueError:
                                amount = 0.0
                            
                            if description.strip():
                                transactions.append({
                                    'id': generate_transaction_id(description, date_str),
                                    'date': date_str,
                                    'description': description,
                                    'amount': amount,
                                    'category': 'Uncategorized',
                                    'source': os.path.basename(filepath),
                                    'imported_at': datetime.now().isoformat()
                                })
                        except Exception:
                            continue
                    
                    if transactions:
                        break
                        
            except UnicodeDecodeError:
                continue
                
    except Exception as e:
        raise Exception(f"Error parsing file: {str(e)}")
    
    return transactions

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/rules', methods=['GET'])
def get_rules_api():
    return jsonify(get_rules())

@app.route('/api/rules', methods=['POST'])
def update_rules_api():
    try:
        new_rules = request.json
        if not isinstance(new_rules, dict):
            return jsonify({'error': 'Invalid rules format'}), 400
        
        save_rules(new_rules)
        
        transactions = get_transactions()
        for tx in transactions:
            tx['category'] = categorize_transaction(tx['description'], new_rules)
        save_transactions(transactions)
        
        return jsonify({'success': True, 'message': 'Rules updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions', methods=['GET'])
def get_transactions_api():
    transactions = get_transactions()
    
    category = request.args.get('category')
    search = request.args.get('search')
    
    if category:
        transactions = [tx for tx in transactions if tx['category'] == category]
    
    if search:
        search_lower = search.lower()
        transactions = [tx for tx in transactions 
                       if search_lower in tx['description'].lower() 
                       or search_lower in tx.get('date', '').lower()]
    
    transactions.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    return jsonify(transactions)

@app.route('/api/transactions', methods=['POST'])
def add_transaction_api():
    try:
        data = request.json
        transactions = get_transactions()
        
        tx_id = data.get('id')
        if tx_id:
            for tx in transactions:
                if tx['id'] == tx_id:
                    tx.update(data)
                    save_transactions(transactions)
                    return jsonify({'success': True, 'transaction': tx})
        
        new_tx = {
            'id': generate_transaction_id(data.get('description', '')),
            'date': data.get('date', datetime.now().strftime('%Y-%m-%d')),
            'description': data.get('description', ''),
            'amount': float(data.get('amount', 0)),
            'category': data.get('category', 'Uncategorized'),
            'source': 'manual',
            'imported_at': datetime.now().isoformat()
        }
        
        transactions.append(new_tx)
        save_transactions(transactions)
        
        return jsonify({'success': True, 'transaction': new_tx}), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/transactions/bulk-update', methods=['POST'])
def bulk_update_transactions():
    try:
        updates = request.json
        if not isinstance(updates, list):
            return jsonify({'error': 'Expected list of updates'}), 400
        
        transactions = get_transactions()
        updated_count = 0
        
        for update in updates:
            tx_id = update.get('id')
            if tx_id:
                for tx in transactions:
                    if tx['id'] == tx_id:
                        if 'category' in update:
                            tx['category'] = update['category']
                        if 'description' in update:
                            tx['description'] = update['description']
                        if 'amount' in update:
                            tx['amount'] = float(update['amount'])
                        updated_count += 1
                        break
        
        save_transactions(transactions)
        return jsonify({'success': True, 'updated': updated_count})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        allowed_extensions = {'csv', 'xlsx', 'xls'}
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if ext not in allowed_extensions:
            return jsonify({'error': 'File type not supported. Please upload CSV or Excel files.'}), 400
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        if ext == 'csv':
            transactions = parse_csv_file(filepath)
        else:
            return jsonify({'error': 'Excel support requires pandas. Please convert to CSV or install pandas.'}), 400
        
        if not transactions:
            return jsonify({'error': 'No valid transactions found in file. Please check the format.'}), 400
        
        rules = get_rules()
        for tx in transactions:
            tx['category'] = categorize_transaction(tx['description'], rules)
        
        existing = get_transactions()
        existing_ids = {tx['id'] for tx in existing}
        
        new_count = 0
        for tx in transactions:
            if tx['id'] not in existing_ids:
                existing.append(tx)
                new_count += 1
        
        save_transactions(existing)
        
        return jsonify({
            'success': True,
            'message': f'Successfully imported {new_count} new transactions',
            'total_processed': len(transactions),
            'new_transactions': new_count
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    transactions = get_transactions()
    rules = get_rules()
    
    category_totals = {}
    monthly_totals = {}
    
    for tx in transactions:
        amount = tx.get('amount', 0)
        category = tx.get('category', 'Uncategorized')
        date_str = tx.get('date', '')
        
        if category not in category_totals:
            category_totals[category] = 0
        category_totals[category] += amount
        
        if len(date_str) >= 7:
            month = date_str[:7]
            if month not in monthly_totals:
                monthly_totals[month] = 0
            monthly_totals[month] += amount
    
    income_categories = {'Income', 'Investment'}
    total_income = sum(category_totals.get(cat, 0) for cat in income_categories)
    total_expenses = sum(amount for cat, amount in category_totals.items() if cat not in income_categories)
    
    return jsonify({
        'total_transactions': len(transactions),
        'category_breakdown': category_totals,
        'monthly_breakdown': monthly_totals,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'net': total_income - total_expenses,
        'categories': list(rules.keys())
    })

@app.route('/api/backup/list', methods=['GET'])
def list_backups():
    backups = []
    backup_dir = app.config['BACKUP_FOLDER']
    
    if os.path.exists(backup_dir):
        for filename in sorted(os.listdir(backup_dir)):
            filepath = os.path.join(backup_dir, filename)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                backups.append({
                    'filename': filename,
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
    
    return jsonify(backups)

@app.route('/api/backup/restore/<filename>', methods=['POST'])
def restore_backup(filename):
    try:
        backup_path = os.path.join(app.config['BACKUP_FOLDER'], secure_filename(filename))
        
        if not os.path.exists(backup_path):
            return jsonify({'error': 'Backup file not found'}), 404
        
        if filename.endswith('transactions.json.bak'):
            target_path = os.path.join(app.config['DATA_FOLDER'], 'transactions.json')
        elif filename.endswith('rules.json.bak'):
            target_path = os.path.join(app.config['DATA_FOLDER'], 'rules.json')
        else:
            return jsonify({'error': 'Unknown backup type'}), 400
        
        create_backup(target_path)
        shutil.copy2(backup_path, target_path)
        
        return jsonify({'success': True, 'message': 'Backup restored successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    print("=" * 60)
    print("Finance Tracker - Personal Finance Manager")
    print("=" * 60)
    print("Starting server...")
    print("Access the app at: http://localhost:5000")
    print("Data stored in: data/")
    print("Backups stored in: backup/")
    print("=" * 60)
    app.run(debug=False, host='0.0.0.0', port=5000)
