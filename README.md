# Finance Tracker - Production-Ready Local Edition

A secure, robust personal finance analyzer that runs entirely on your local computer. Upload bank statements, credit card bills, and investment reports to automatically categorize transactions and visualize your spending habits.

## Features

### Core Functionality
- **Drag & Drop Upload**: Simply drop CSV or Excel files from any bank
- **Smart Auto-Categorization**: Transactions are automatically sorted into categories like Food, Transportation, Utilities, etc.
- **Customizable Rules**: Teach the system new keywords or create custom categories
- **Interactive Dashboard**: Visual charts showing spending by category and monthly trends
- **Search & Filter**: Find any transaction quickly with real-time search
- **100% Local**: All data stays on your computer - nothing is sent to the cloud

### Production-Ready Enhancements
- **Automatic Backups**: Every change creates a timestamped backup before modifying data
- **File Validation**: Checks file types, sizes (max 16MB), and column formats
- **Structured Logging**: Detailed logs for troubleshooting stored in the `logs/` folder
- **Health Monitoring**: Built-in health endpoint to check system status
- **Duplicate Prevention**: Smart ID generation prevents importing the same transaction twice
- **Multi-Encoding Support**: Handles CSV files from different regions and banks

## Quick Start

### Requirements
- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. Install dependencies:
```bash
pip install flask pandas openpyxl python-dateutil
```

2. Run the application:
```bash
python app.py
```

3. Open your browser to: **http://localhost:5000**

That's it! The app will automatically create the necessary folders for data, backups, and logs.

## Directory Structure

```
finance_tracker/
├── app.py              # Main application
├── index.html          # User interface
├── data/               # Your financial data (auto-created)
│   ├── transactions.json
│   └── rules.json
├── backups/            # Automatic backups (auto-created)
├── uploads/            # Temporary upload folder (auto-created)
├── logs/               # Application logs (auto-created)
│   └── app.log
└── README.md           # This file
```

## How to Use

### 1. Upload Statements
- Drag and drop your bank statement (CSV, XLS, or XLSX) onto the upload zone
- Or click "Browse Files" to select a file
- The app will automatically detect columns for Date, Description, and Amount

### 2. View Dashboard
- See total income, expenses, and net balance
- Visual breakdown of spending by category
- Monthly trend chart showing cash flow over time

### 3. Manage Transactions
- Click "Transactions" to see all imported data
- Use the search box to find specific transactions
- Transactions are sorted by date (newest first)

### 4. Customize Categories
- Click "Rules" to edit categorization logic
- Add keywords to existing categories (comma-separated)
- Create new categories or rename existing ones
- Click "Save All Changes" to re-categorize all transactions

### 5. Access Backups
- Click "Backups" to see all automatic backups
- Download any backup file for safekeeping
- Backups are created before every data change

## Supported File Formats

The app accepts:
- **CSV** (UTF-8, Latin-1, or CP1252 encoding)
- **Excel** (.xlsx, .xls)

Expected columns (auto-detected):
- Date column (containing "date")
- Description column (containing "desc", "name", or "merchant")
- Amount column (containing "amount", "value", or "charge")

If columns can't be auto-detected, the app will use the first three columns.

## Default Categories

The app comes with these pre-configured categories:
- **Food & Dining**: restaurants, cafes, grocery stores
- **Transportation**: uber, gas, parking, transit
- **Utilities**: electric, water, internet, phone
- **Entertainment**: netflix, spotify, movies, games
- **Shopping**: amazon, target, clothing, electronics
- **Healthcare**: pharmacy, doctor, dentist
- **Income**: payroll, salary, dividends
- **Fees & Charges**: bank fees, penalties, ATM fees
- **Uncategorized**: transactions that don't match any rules

You can fully customize these in the Rules section.

## API Endpoints

For advanced users, the app provides a REST API:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | System health check |
| `/api/upload` | POST | Upload a statement file |
| `/api/transactions` | GET | Get all transactions |
| `/api/rules` | GET | Get categorization rules |
| `/api/rules` | POST | Update rules |
| `/api/stats` | GET | Get dashboard statistics |
| `/api/backups` | GET | List available backups |
| `/backup/<filename>` | GET | Download a backup file |

## Data Safety

### Automatic Backups
- Backups are created before every data modification
- Stored in the `backups/` folder with timestamps
- Automatically cleaned up after 10 backups (keeps most recent)

### What Gets Backed Up
- Transaction data (transactions_YYYYMMDD_HHMMSS.json)
- Categorization rules (rules_YYYYMMDD_HHMMSS.json)

### Manual Backup Recommendation
Periodically copy the entire `data/` and `backups/` folders to an external drive or cloud storage for extra safety.

## Troubleshooting

### App Won't Start
- Check if port 5000 is already in use
- Ensure all dependencies are installed: `pip install flask pandas openpyxl python-dateutil`
- Check `logs/app.log` for error messages

### File Upload Fails
- Verify file format is CSV, XLS, or XLSX
- Check file size is under 16MB
- Ensure file has at least 3 columns
- Look for specific error messages in the upload status area

### Transactions Not Categorizing
- Review keywords in the Rules section
- Add merchant names that aren't being caught
- Remember: matching is case-insensitive and partial (e.g., "starbucks" matches "Starbucks Coffee")

### Data Lost or Corrupted
- Go to the Backups section
- Download the most recent backup before the issue
- Restore manually by replacing files in the `data/` folder

## Privacy & Security

- **No Internet Required**: The app runs completely offline after installation
- **Local Storage Only**: All data is stored on your computer
- **No Telemetry**: Nothing is sent to external servers
- **Access Control**: Anyone with access to your computer can view the data while the app is running

## Performance Notes

- Designed for personal use (hundreds to thousands of transactions)
- File upload limit: 16MB
- Transaction list shows first 100 entries for performance
- Search and filtering happen instantly in the browser

## License

This software is provided as-is for personal use. Feel free to modify and adapt for your needs.

---

**Built with**: Python, Flask, Pandas, Tailwind CSS, Chart.js

**Version**: 2.0 (Production-Ready Local Edition)
