# Inventory Management System (IMS)

A comprehensive PyQt6-based desktop application for managing inventory, sales, purchases, customers, suppliers, and accounting operations.

## Features

- **Dashboard**: Real-time statistics, low stock alerts, recent transactions
- **Product Management**: CRUD operations, category management, cost/sale price tracking
- **Sales & Purchases**: Multi-item invoices, payment methods (cash/credit/partial)
- **Returns**: Sales and purchase return processing with refund tracking
- **Customer & Supplier Management**: Credit limits, payment tracking, statements
- **Stock Tracking**: Real-time inventory counts with movement history
- **Accounting**: Double-entry journal system, trial balance, chart of accounts
- **Financial Reports**: Sales, purchases, P&L, stock, and cash flow reports
- **Invoicing**: Professional A4 PDF invoices and POS thermal paper receipts
- **Printing**: Print preview, direct printer output, PDF export

## Requirements

- Python 3.9+
- PyQt6 6.6.0+

## Setup

### Option 1: Using the run script (Recommended)

```bash
chmod +x run.sh
./run.sh
```

This will automatically create a virtual environment and install dependencies.

### Option 2: Manual setup with uv

```bash
# Create virtual environment
uv venv .venv

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Install dependencies
uv pip install -r requirements.txt
```

### Option 3: Using pip

```bash
python -m pip install -r requirements.txt
```

## Build artifacts

### Build Windows executable

You must build the Windows `.exe` artifact on Windows.

```powershell
uv venv .venv
.\.venv\Scripts\activate
uv pip install -r requirements.txt
python build.py --target exe --name inventory_ms
```

Output:

- `dist\inventory_ms.exe`

### Build Linux DEB package

Build the Debian package on Linux.

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
sudo apt install dpkg-dev
python build.py --target deb --name inventory_ms
```

Output:

- `dist/inventory_ms_2.0.0_amd64.deb`

### Build macOS app bundle

Build the `.app` bundle on macOS.

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
python build.py --target app --name inventory_ms
```

Output:

- `dist/inventory_ms.app`

### Notes

- A Windows `.exe` cannot be reliably built on Linux without cross-compilation tooling.
- The macOS `.app` must be built on macOS.
- The build scripts use `asset/logo/LogoIMS.png` as the icon source for generated artifacts.
- The `.deb` package contains the built executable under `/usr/bin/inventory_ms`.

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Running the Application

After setting up the virtual environment:

```bash
# With venv activated
python main.py
```

Or simply use the run script:

```bash
./run.sh
```

## Project Structure

```
IMS/
├── main.py                 # Application entry point
├── database.py             # SQLite database wrapper
├── styles.py               # UI styling constants and helpers
├── pages/                  # Feature modules
│   ├── dashboard.py
│   ├── products.py
│   ├── sales.py
│   ├── purchases.py
│   ├── sales_return.py
│   ├── purchase_return.py
│   ├── customers.py
│   ├── suppliers.py
│   ├── stock.py
│   ├── cash.py
│   ├── credit.py
│   ├── accounting.py
│   ├── reports.py
│   └── categories.py
├── invoices/               # Invoice generation and printing
│   ├── templates.py        # HTML template builders
│   └── printer.py          # Print handling system
├── pyproject.toml          # Project metadata
├── requirements.txt        # Python dependencies
├── run.sh                  # Application launcher script
└── README.md               # This file
```

## Database

The application uses SQLite3 with the following tables:
- products
- categories
- customers
- suppliers
- sales
- sale_items
- purchases
- purchase_items
- sales_returns
- purchase_returns
- stock_movements
- cash_transactions
- journal_entries
- settings

Database is automatically created on first run as `ims.db`.

## Features Overview

### Inventory Management
- Track product stock with real-time updates
- Categorize products
- Monitor low stock levels
- View stock movement history

### Sales & Purchases
- Create multi-item invoices/purchase orders
- Support multiple payment methods (cash, credit, partial)
- Apply discounts and taxes
- Generate professional invoices in A4 and POS formats

### Returns Processing
- Process sales and purchase returns
- Automatic inventory reversion
- Refund type selection (cash/payable adjustment)
- Return tracking with reasons and notes

### Financial Management
- Double-entry accounting system
- Journal entry tracking
- Chart of accounts
- Trial balance verification
- Financial reports with CSV export

### Reporting
- Sales reports with filters
- Purchase reports with filters
- Profit & Loss statement
- Stock summary
- Cash flow reports

## Printing Options

### A4 Invoices
- Professional layout with color
- Company information and logo space
- Itemized line items with totals
- Payment status badge

### POS Receipts
- 80mm thermal paper format
- Monospace text layout
- Compact item listing
- Receipt-ready formatting

### Export Options
- PDF export (A4 and POS formats)
- Print preview before printing
- Direct printer output
- Batch printing support

## Troubleshooting

### PyQt6 Installation Issues
If you encounter issues installing PyQt6, you may need to use the system package manager:

```bash
# On Ubuntu/Debian
sudo apt-get install python3-pyqt6

# Then use --break-system-packages with uv
uv pip install --break-system-packages PyQt6

```

### Database Issues
If the database becomes corrupted, delete `ims.db` and restart the application to recreate it.


```
# admin
# admin123
```
### Port Conflicts
The application uses local SQLite, so no ports are involved. No conflicts should occur.

## Version

v2.0.0 - Complete IMS system with printing support

## License

MIT License

## Support

For issues or feature requests, contact the development team.



