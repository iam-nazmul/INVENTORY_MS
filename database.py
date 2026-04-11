import sqlite3
import hashlib
import os
import sys
from pathlib import Path

def get_data_dir():
    """Get the user data directory for the application."""
    if getattr(sys, 'frozen', False):
        # Running as bundled executable
        app_name = "inventory_ms"
    else:
        # Running from source
        app_name = "inventory_ms"

    # Get platform-specific data directory
    if os.name == 'nt':  # Windows
        data_dir = Path(os.environ.get('APPDATA', '')) / app_name
    elif os.name == 'posix':  # Linux/macOS
        if sys.platform == 'darwin':  # macOS
            data_dir = Path.home() / 'Library' / 'Application Support' / app_name
        else:  # Linux
            data_dir = Path.home() / '.local' / 'share' / app_name
    else:
        # Fallback
        data_dir = Path.home() / app_name

    # Create directory if it doesn't exist
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

DB_PATH = get_data_dir() / "inventory.db"


class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()
        self._seed_defaults()

    # ─── Schema ───────────────────────────────────────────────────────────────

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE TABLE IF NOT EXISTS categories (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at  TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS customers (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                phone       TEXT,
                email       TEXT,
                address     TEXT,
                credit_limit REAL DEFAULT 0,
                balance     REAL DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS suppliers (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                contact     TEXT,
                phone       TEXT,
                email       TEXT,
                address     TEXT,
                balance     REAL DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS products (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                sku         TEXT UNIQUE,
                category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
                supplier_id INTEGER REFERENCES suppliers(id)  ON DELETE SET NULL,
                unit        TEXT DEFAULT 'pcs',
                cost_price  REAL DEFAULT 0,
                sale_price  REAL DEFAULT 0,
                quantity    INTEGER DEFAULT 0,
                min_stock   INTEGER DEFAULT 10,
                description TEXT,
                created_at  TEXT DEFAULT (datetime('now','localtime')),
                updated_at  TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS sales (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_no     TEXT UNIQUE,
                customer_id    INTEGER REFERENCES customers(id) ON DELETE SET NULL,
                sale_date      TEXT DEFAULT (date('now','localtime')),
                subtotal       REAL DEFAULT 0,
                discount       REAL DEFAULT 0,
                tax_rate       REAL DEFAULT 0,
                tax_amount     REAL DEFAULT 0,
                total          REAL DEFAULT 0,
                paid_amount    REAL DEFAULT 0,
                due_amount     REAL DEFAULT 0,
                payment_type   TEXT DEFAULT 'cash',
                status         TEXT DEFAULT 'paid',
                note           TEXT,
                created_at     TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS sale_items (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id     INTEGER NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
                product_id  INTEGER NOT NULL REFERENCES products(id),
                quantity    INTEGER NOT NULL,
                unit_price  REAL NOT NULL,
                discount    REAL DEFAULT 0,
                total       REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS purchases (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                po_number     TEXT UNIQUE,
                supplier_id   INTEGER REFERENCES suppliers(id) ON DELETE SET NULL,
                purchase_date TEXT DEFAULT (date('now','localtime')),
                subtotal      REAL DEFAULT 0,
                discount      REAL DEFAULT 0,
                tax_rate      REAL DEFAULT 0,
                tax_amount    REAL DEFAULT 0,
                total         REAL DEFAULT 0,
                paid_amount   REAL DEFAULT 0,
                due_amount    REAL DEFAULT 0,
                payment_type  TEXT DEFAULT 'cash',
                status        TEXT DEFAULT 'paid',
                note          TEXT,
                created_at    TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS purchase_items (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                purchase_id  INTEGER NOT NULL REFERENCES purchases(id) ON DELETE CASCADE,
                product_id   INTEGER NOT NULL REFERENCES products(id),
                quantity     INTEGER NOT NULL,
                unit_price   REAL NOT NULL,
                total        REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cash_transactions (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                type           TEXT NOT NULL,
                reference_type TEXT,
                reference_id   INTEGER,
                party_type     TEXT,
                party_id       INTEGER,
                amount         REAL NOT NULL,
                description    TEXT,
                created_at     TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS accounts (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                code           TEXT UNIQUE,
                name           TEXT NOT NULL,
                account_type   TEXT NOT NULL,
                normal_balance TEXT NOT NULL DEFAULT 'DR',
                description    TEXT,
                created_at     TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS journal_entries (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_no       TEXT,
                entry_date     TEXT DEFAULT (date('now','localtime')),
                description    TEXT,
                reference_type TEXT,
                reference_id   INTEGER,
                created_at     TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS journal_lines (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                journal_id  INTEGER NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
                account_id  INTEGER NOT NULL REFERENCES accounts(id),
                debit       REAL DEFAULT 0,
                credit      REAL DEFAULT 0,
                description TEXT
            );

            CREATE TABLE IF NOT EXISTS stock_movements (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id  INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                type        TEXT NOT NULL,
                quantity    INTEGER NOT NULL,
                balance     INTEGER NOT NULL,
                reference_type TEXT,
                reference_id   INTEGER,
                note        TEXT,
                created_at  TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS sales_returns (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                return_no   TEXT UNIQUE,
                sale_id     INTEGER NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
                return_date TEXT DEFAULT (date('now','localtime')),
                reason      TEXT,
                total       REAL DEFAULT 0,
                refund_type TEXT DEFAULT 'cash',
                note        TEXT,
                created_at  TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS sales_return_items (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                return_id   INTEGER NOT NULL REFERENCES sales_returns(id) ON DELETE CASCADE,
                product_id  INTEGER NOT NULL REFERENCES products(id),
                quantity    INTEGER NOT NULL,
                unit_price  REAL NOT NULL,
                total       REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS purchase_returns (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                return_no   TEXT UNIQUE,
                purchase_id INTEGER NOT NULL REFERENCES purchases(id) ON DELETE CASCADE,
                return_date TEXT DEFAULT (date('now','localtime')),
                reason      TEXT,
                total       REAL DEFAULT 0,
                refund_type TEXT DEFAULT 'adjust',
                note        TEXT,
                created_at  TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS purchase_return_items (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                return_id   INTEGER NOT NULL REFERENCES purchase_returns(id) ON DELETE CASCADE,
                product_id  INTEGER NOT NULL REFERENCES products(id),
                quantity    INTEGER NOT NULL,
                unit_price  REAL NOT NULL,
                total       REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id  INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                type        TEXT NOT NULL,
                quantity    INTEGER NOT NULL,
                price       REAL DEFAULT 0,
                note        TEXT,
                created_at  TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS users (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                username   TEXT NOT NULL UNIQUE,
                password   TEXT NOT NULL,
                role       TEXT NOT NULL DEFAULT 'staff',
                role_id    INTEGER REFERENCES roles(id) ON DELETE SET NULL,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS roles (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at  TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS menus (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL UNIQUE,
                icon       TEXT,
                section    TEXT,
                sort_order INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS role_permissions (
                role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
                menu_id INTEGER NOT NULL REFERENCES menus(id) ON DELETE CASCADE,
                PRIMARY KEY (role_id, menu_id)
            );
        """)
        # Migrations for existing databases
        for stmt in [
            "ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'staff'",
            "ALTER TABLE users ADD COLUMN role_id INTEGER REFERENCES roles(id) ON DELETE SET NULL",
            "ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1",
            "ALTER TABLE users ADD COLUMN photo BLOB DEFAULT NULL",
            "ALTER TABLE products ADD COLUMN image BLOB DEFAULT NULL",
        ]:
            try:
                self.conn.execute(stmt)
            except Exception:
                pass
        self.conn.commit()

    def _seed_defaults(self):
        # Settings
        defaults = {
            "cash_balance":         "0",
            "sale_counter":         "0",
            "purchase_counter":     "0",
            "journal_counter":      "0",
            "sale_return_counter":  "0",
            "pur_return_counter":   "0",
            "tax_rate":             "0",
            "company_name":         "My Company",
        }
        for k, v in defaults.items():
            self.conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?,?)", (k, v)
            )

        # Categories
        cur = self.conn.execute("SELECT COUNT(*) FROM categories")
        if cur.fetchone()[0] == 0:
            self.conn.executemany(
                "INSERT INTO categories (name, description) VALUES (?,?)",
                [("Electronics","Electronic devices"), ("Clothing","Apparel"),
                 ("Food","Consumables"), ("Furniture","Home/office furniture"),
                 ("Stationery","Office supplies")],
            )

        # Chart of accounts
        cur = self.conn.execute("SELECT COUNT(*) FROM accounts")
        if cur.fetchone()[0] == 0:
            self.conn.executemany(
                "INSERT INTO accounts (code,name,account_type,normal_balance,description) VALUES (?,?,?,?,?)",
                [
                    ("1001","Cash",                 "ASSET",     "DR","Cash on hand"),
                    ("1002","Accounts Receivable",  "ASSET",     "DR","Customer receivables"),
                    ("1003","Inventory",            "ASSET",     "DR","Stock inventory"),
                    ("2001","Accounts Payable",     "LIABILITY", "CR","Supplier payables"),
                    ("3001","Owner Equity",         "EQUITY",    "CR","Owner capital"),
                    ("4001","Sales Revenue",        "REVENUE",   "CR","Revenue from sales"),
                    ("5001","Cost of Goods Sold",   "EXPENSE",   "DR","Cost of sold items"),
                    ("5002","Purchase Expense",     "EXPENSE",   "DR","Direct purchase costs"),
                    ("5003","Other Expense",        "EXPENSE",   "DR","Miscellaneous expenses"),
                    ("4002","Other Income",         "REVENUE",   "CR","Miscellaneous income"),
                ],
            )
        # ── Menus (seed all nav pages) ──────────────────────────────────────────
        _MENU_DEFS = [
            ("Dashboard",       "📊", None,          1),
            ("Products",        "📦", "INVENTORY",    2),
            ("Stock",           "📈", "INVENTORY",    3),
            ("Transactions",    "🔄", "INVENTORY",    4),
            ("Sales",           "🛒", "TRADING",      5),
            ("Sales Return",    "↩",  "TRADING",      6),
            ("Purchases",       "📋", "TRADING",      7),
            ("Purchase Return", "↪",  "TRADING",      8),
            ("Credit",          "💳", "TRADING",      9),
            ("Customers",       "👥", "PARTIES",     10),
            ("Suppliers",       "🚚", "PARTIES",     11),
            ("Cash",            "💰", "FINANCE",     12),
            ("Accounting",      "📒", "FINANCE",     13),
            ("Reports",         "📄", "ANALYTICS",   14),
            ("Categories",      "🏷", "SETTINGS",    15),
            ("Users",           "👤", "SETTINGS",    16),
            ("Roles",           "🔑", "SETTINGS",    17),
        ]
        self.conn.executemany(
            "INSERT OR IGNORE INTO menus (name, icon, section, sort_order) VALUES (?,?,?,?)",
            _MENU_DEFS
        )

        # ── Roles ────────────────────────────────────────────────────────────────
        self.conn.executemany(
            "INSERT OR IGNORE INTO roles (name, description) VALUES (?,?)",
            [("admin", "Full system access — all menus"),
             ("staff", "Standard access — daily operations only")]
        )
        # ── Default permissions ──────────────────────────────────────────────────
        admin_id = self.conn.execute("SELECT id FROM roles WHERE name='admin'").fetchone()["id"]
        staff_id = self.conn.execute("SELECT id FROM roles WHERE name='staff'").fetchone()["id"]

        # Admin gets every menu
        for row in self.conn.execute("SELECT id FROM menus").fetchall():
            self.conn.execute(
                "INSERT OR IGNORE INTO role_permissions (role_id, menu_id) VALUES (?,?)",
                (admin_id, row["id"])
            )
        # Staff gets daily-operations menus
        _STAFF_MENUS = [
            "Dashboard", "Products", "Stock", "Sales", "Sales Return",
            "Purchases", "Purchase Return", "Credit", "Customers", "Suppliers", "Cash",
        ]
        for name in _STAFF_MENUS:
            row = self.conn.execute("SELECT id FROM menus WHERE name=?", (name,)).fetchone()
            if row:
                self.conn.execute(
                    "INSERT OR IGNORE INTO role_permissions (role_id, menu_id) VALUES (?,?)",
                    (staff_id, row["id"])
                )

        # ── Default admin user (password: admin123) ──────────────────────────────
        cur = self.conn.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()[0] == 0:
            hashed = hashlib.sha256("admin123".encode()).hexdigest()
            self.conn.execute(
                "INSERT INTO users (username, password, role, role_id) VALUES (?,?,?,?)",
                ("admin", hashed, "admin", admin_id)
            )
        else:
            self.conn.execute(
                "UPDATE users SET role='admin' WHERE username='admin' AND role='staff'"
            )

        # ── Migrate existing users: populate role_id from role TEXT ──────────────
        for rname in ("admin", "staff"):
            rid = self.conn.execute(
                "SELECT id FROM roles WHERE name=?", (rname,)
            ).fetchone()
            if rid:
                self.conn.execute(
                    "UPDATE users SET role_id=? WHERE role=? AND role_id IS NULL",
                    (rid["id"], rname)
                )

        self.conn.commit()

    def check_credentials(self, username, password):
        hashed = hashlib.sha256(password.encode()).hexdigest()
        row = self.conn.execute("""
            SELECT u.id, u.username, u.role, u.role_id,
                   COALESCE(r.name, u.role) AS role_name, u.is_active, u.photo
            FROM users u
            LEFT JOIN roles r ON r.id = u.role_id
            WHERE u.username=? AND u.password=? AND u.is_active=1
        """, (username, hashed)).fetchone()
        return dict(row) if row else None

    def register_user(self, username, password, role_name="staff", photo_bytes=None):
        """Register a new user. Raises ValueError on validation failure."""
        username = username.strip()
        if not username:
            raise ValueError("Username cannot be empty.")
        if len(password) < 4:
            raise ValueError("Password must be at least 4 characters.")
        hashed = hashlib.sha256(password.encode()).hexdigest()
        role_row = self.conn.execute(
            "SELECT id FROM roles WHERE name=?", (role_name,)
        ).fetchone()
        role_id = role_row["id"] if role_row else None
        try:
            self.conn.execute(
                "INSERT INTO users (username, password, role, role_id, photo) VALUES (?,?,?,?,?)",
                (username, hashed, role_name, role_id, photo_bytes)
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(f"Username '{username}' is already taken.")

    def get_all_users(self):
        return self.conn.execute("""
            SELECT u.id, u.username, u.role, u.role_id,
                   COALESCE(r.name, u.role) AS role_name, u.created_at, u.is_active, u.photo
            FROM users u LEFT JOIN roles r ON r.id = u.role_id
            ORDER BY u.id
        """).fetchall()

    def set_user_photo(self, user_id, photo_bytes):
        self.conn.execute("UPDATE users SET photo=? WHERE id=?", (photo_bytes, user_id))
        self.conn.commit()

    def verify_user_password(self, user_id, password):
        """Return True if the given password matches the stored hash for user_id."""
        hashed = hashlib.sha256(password.encode()).hexdigest()
        row = self.conn.execute(
            "SELECT id FROM users WHERE id=? AND password=?", (user_id, hashed)
        ).fetchone()
        return row is not None

    def set_user_password(self, user_id, new_password):
        if len(new_password) < 4:
            raise ValueError("Password must be at least 4 characters.")
        hashed = hashlib.sha256(new_password.encode()).hexdigest()
        self.conn.execute("UPDATE users SET password=? WHERE id=?", (hashed, user_id))
        self.conn.commit()

    def set_user_active(self, user_id, is_active: bool):
        self.conn.execute("UPDATE users SET is_active=? WHERE id=?", (1 if is_active else 0, user_id))
        self.conn.commit()

    # ─── Roles ────────────────────────────────────────────────────────────────

    def get_all_roles(self):
        return self.conn.execute(
            "SELECT id, name, description, created_at FROM roles ORDER BY id"
        ).fetchall()

    def create_role(self, name, description=""):
        name = name.strip()
        if not name:
            raise ValueError("Role name cannot be empty.")
        try:
            self.conn.execute(
                "INSERT INTO roles (name, description) VALUES (?,?)", (name, description)
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(f"Role '{name}' already exists.")

    def update_role(self, role_id, name, description=""):
        name = name.strip()
        if not name:
            raise ValueError("Role name cannot be empty.")
        try:
            self.conn.execute(
                "UPDATE roles SET name=?, description=? WHERE id=?",
                (name, description, role_id)
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(f"Role '{name}' already exists.")

    def delete_role(self, role_id):
        row = self.conn.execute("SELECT name FROM roles WHERE id=?", (role_id,)).fetchone()
        if row and row["name"] in ("admin", "staff"):
            raise ValueError("Cannot delete built-in roles (admin / staff).")
        self.conn.execute("DELETE FROM roles WHERE id=?", (role_id,))
        self.conn.commit()

    # ─── Menus & Permissions ──────────────────────────────────────────────────

    def get_menus(self):
        return self.conn.execute(
            "SELECT id, name, icon, section, sort_order FROM menus ORDER BY sort_order"
        ).fetchall()

    def get_role_permissions(self, role_id):
        """Returns set of menu_ids assigned to this role."""
        rows = self.conn.execute(
            "SELECT menu_id FROM role_permissions WHERE role_id=?", (role_id,)
        ).fetchall()
        return {r["menu_id"] for r in rows}

    def set_role_permissions(self, role_id, menu_ids):
        """Replace all permissions for a role with the given menu_id set."""
        self.conn.execute("DELETE FROM role_permissions WHERE role_id=?", (role_id,))
        for mid in menu_ids:
            self.conn.execute(
                "INSERT OR IGNORE INTO role_permissions (role_id, menu_id) VALUES (?,?)",
                (role_id, mid)
            )
        self.conn.commit()

    def get_user_permissions(self, role_id):
        """Returns set of allowed menu *names* for a role_id."""
        if role_id is None:
            return set()
        rows = self.conn.execute("""
            SELECT m.name FROM role_permissions rp
            JOIN menus m ON m.id = rp.menu_id
            WHERE rp.role_id = ?
        """, (role_id,)).fetchall()
        return {r["name"] for r in rows}

    # ─── Settings ─────────────────────────────────────────────────────────────

    def get_setting(self, key, default="0"):
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key, value):
        self.conn.execute("INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)", (key, str(value)))
        self.conn.commit()

    def get_cash_balance(self):
        return float(self.get_setting("cash_balance", "0"))

    def _adjust_cash(self, delta):
        bal = self.get_cash_balance() + delta
        self.set_setting("cash_balance", bal)
        return bal

    def _next_invoice(self):
        n = int(self.get_setting("sale_counter", "0")) + 1
        self.set_setting("sale_counter", n)
        return f"INV-{n:05d}"

    def _next_po(self):
        n = int(self.get_setting("purchase_counter", "0")) + 1
        self.set_setting("purchase_counter", n)
        return f"PO-{n:05d}"

    def _next_journal(self):
        n = int(self.get_setting("journal_counter", "0")) + 1
        self.set_setting("journal_counter", n)
        return f"JE-{n:05d}"

    # ─── Dashboard ────────────────────────────────────────────────────────────

    def get_dashboard_stats(self):
        c = self.conn
        total_products   = c.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        total_stock      = c.execute("SELECT COALESCE(SUM(quantity),0) FROM products").fetchone()[0]
        low_stock        = c.execute("SELECT COUNT(*) FROM products WHERE quantity <= min_stock").fetchone()[0]
        stock_value      = c.execute("SELECT COALESCE(SUM(quantity*cost_price),0) FROM products").fetchone()[0]
        total_customers  = c.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        total_suppliers  = c.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0]
        total_sales      = c.execute("SELECT COALESCE(SUM(total),0) FROM sales").fetchone()[0]
        today_sales      = c.execute("SELECT COALESCE(SUM(total),0) FROM sales WHERE date(sale_date)=date('now','localtime')").fetchone()[0]
        total_purchases  = c.execute("SELECT COALESCE(SUM(total),0) FROM purchases").fetchone()[0]
        receivable       = c.execute("SELECT COALESCE(SUM(due_amount),0) FROM sales WHERE status IN ('partial','unpaid')").fetchone()[0]
        payable          = c.execute("SELECT COALESCE(SUM(due_amount),0) FROM purchases WHERE status IN ('partial','unpaid')").fetchone()[0]
        unpaid_invoices  = c.execute("SELECT COUNT(*) FROM sales WHERE status IN ('partial','unpaid')").fetchone()[0]
        cash_balance     = self.get_cash_balance()
        pl_row = c.execute("""
            SELECT COALESCE(SUM(si.total), 0)                   AS revenue,
                   COALESCE(SUM(si.quantity * p.cost_price), 0) AS cogs
            FROM sale_items si
            JOIN products p ON p.id = si.product_id
        """).fetchone()
        gross_profit = pl_row["revenue"] - pl_row["cogs"]
        return dict(
            total_products=total_products, total_stock=total_stock, low_stock=low_stock,
            stock_value=stock_value, total_customers=total_customers, total_suppliers=total_suppliers,
            total_sales=total_sales, today_sales=today_sales, total_purchases=total_purchases,
            receivable=receivable, payable=payable, unpaid_invoices=unpaid_invoices,
            cash_balance=cash_balance, gross_profit=gross_profit,
        )

    def get_recent_sales(self, limit=8):
        return self.conn.execute("""
            SELECT s.invoice_no, COALESCE(c.name,'Walk-in') AS customer,
                   s.total, s.paid_amount, s.due_amount, s.status, s.sale_date
            FROM sales s LEFT JOIN customers c ON c.id=s.customer_id
            ORDER BY s.id DESC LIMIT ?
        """, (limit,)).fetchall()

    def get_low_stock_products(self, limit=8):
        return self.conn.execute("""
            SELECT p.name, p.sku, p.quantity, p.min_stock, p.unit,
                   c.name AS category
            FROM products p LEFT JOIN categories c ON c.id=p.category_id
            WHERE p.quantity <= p.min_stock ORDER BY p.quantity ASC LIMIT ?
        """, (limit,)).fetchall()

    # ─── Categories ───────────────────────────────────────────────────────────

    def get_all_categories(self):
        return self.conn.execute(
            "SELECT id,name,description,created_at FROM categories ORDER BY name"
        ).fetchall()

    def add_category(self, name, description=""):
        self.conn.execute("INSERT INTO categories (name,description) VALUES (?,?)", (name, description))
        self.conn.commit()

    def update_category(self, cid, name, description=""):
        self.conn.execute("UPDATE categories SET name=?,description=? WHERE id=?", (name, description, cid))
        self.conn.commit()

    def delete_category(self, cid):
        self.conn.execute("DELETE FROM categories WHERE id=?", (cid,))
        self.conn.commit()

    # ─── Customers ────────────────────────────────────────────────────────────

    def get_all_customers(self, search=""):
        q = "SELECT id,name,phone,email,address,credit_limit,balance,created_at FROM customers WHERE 1=1"
        p = []
        if search:
            q += " AND (name LIKE ? OR phone LIKE ? OR email LIKE ?)"
            p += [f"%{search}%"]*3
        return self.conn.execute(q + " ORDER BY name", p).fetchall()

    def get_customer_by_id(self, cid):
        return self.conn.execute("SELECT * FROM customers WHERE id=?", (cid,)).fetchone()

    def add_customer(self, name, phone="", email="", address="", credit_limit=0):
        self.conn.execute(
            "INSERT INTO customers (name,phone,email,address,credit_limit) VALUES (?,?,?,?,?)",
            (name, phone, email, address, credit_limit)
        )
        self.conn.commit()

    def update_customer(self, cid, name, phone="", email="", address="", credit_limit=0):
        self.conn.execute(
            "UPDATE customers SET name=?,phone=?,email=?,address=?,credit_limit=? WHERE id=?",
            (name, phone, email, address, credit_limit, cid)
        )
        self.conn.commit()

    def delete_customer(self, cid):
        self.conn.execute("DELETE FROM customers WHERE id=?", (cid,))
        self.conn.commit()

    def get_customer_transactions(self, cid):
        sales = self.conn.execute("""
            SELECT invoice_no, sale_date AS date, total, paid_amount, due_amount, status, 'Sale' AS type
            FROM sales WHERE customer_id=? ORDER BY sale_date DESC
        """, (cid,)).fetchall()
        cash = self.conn.execute("""
            SELECT 'Cash' AS invoice_no, created_at AS date, amount AS total,
                   amount AS paid_amount, 0 AS due_amount, 'paid' AS status, 'Collection' AS type
            FROM cash_transactions WHERE party_type='customer' AND party_id=? ORDER BY created_at DESC
        """, (cid,)).fetchall()
        return list(sales) + list(cash)

    # ─── Suppliers ────────────────────────────────────────────────────────────

    def get_all_suppliers(self, search=""):
        q = "SELECT id,name,contact,phone,email,address,balance,created_at FROM suppliers WHERE 1=1"
        p = []
        if search:
            q += " AND (name LIKE ? OR phone LIKE ? OR email LIKE ?)"
            p += [f"%{search}%"]*3
        return self.conn.execute(q + " ORDER BY name", p).fetchall()

    def get_supplier_by_id(self, sid):
        return self.conn.execute("SELECT * FROM suppliers WHERE id=?", (sid,)).fetchone()

    def add_supplier(self, name, contact="", phone="", email="", address=""):
        self.conn.execute(
            "INSERT INTO suppliers (name,contact,phone,email,address) VALUES (?,?,?,?,?)",
            (name, contact, phone, email, address)
        )
        self.conn.commit()

    def update_supplier(self, sid, name, contact="", phone="", email="", address=""):
        self.conn.execute(
            "UPDATE suppliers SET name=?,contact=?,phone=?,email=?,address=? WHERE id=?",
            (name, contact, phone, email, address, sid)
        )
        self.conn.commit()

    def delete_supplier(self, sid):
        self.conn.execute("DELETE FROM suppliers WHERE id=?", (sid,))
        self.conn.commit()

    def get_supplier_transactions(self, sid):
        purchases = self.conn.execute("""
            SELECT po_number, purchase_date AS date, total, paid_amount, due_amount, status, 'Purchase' AS type
            FROM purchases WHERE supplier_id=? ORDER BY purchase_date DESC
        """, (sid,)).fetchall()
        cash = self.conn.execute("""
            SELECT 'Cash' AS po_number, created_at AS date, amount AS total,
                   amount AS paid_amount, 0 AS due_amount, 'paid' AS status, 'Payment' AS type
            FROM cash_transactions WHERE party_type='supplier' AND party_id=? ORDER BY created_at DESC
        """, (sid,)).fetchall()
        return list(purchases) + list(cash)

    # ─── Products ─────────────────────────────────────────────────────────────

    def get_all_products(self, search="", category_id=None):
        q = """
            SELECT p.id, p.name, p.sku, c.name AS category, s.name AS supplier,
                   p.unit, p.cost_price, p.sale_price, p.quantity, p.min_stock,
                   p.description, p.updated_at, p.image
            FROM products p
            LEFT JOIN categories c ON c.id=p.category_id
            LEFT JOIN suppliers  s ON s.id=p.supplier_id
            WHERE 1=1
        """
        params = []
        if search:
            q += " AND (p.name LIKE ? OR p.sku LIKE ?)"
            params += [f"%{search}%"]*2
        if category_id:
            q += " AND p.category_id=?"
            params.append(category_id)
        return self.conn.execute(q + " ORDER BY p.name", params).fetchall()

    def get_product_by_id(self, pid):
        return self.conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()

    def add_product(self, name, sku, category_id, supplier_id, unit,
                    cost_price, sale_price, quantity, min_stock, description,
                    image_bytes=None):
        cur = self.conn.execute("""
            INSERT INTO products (name,sku,category_id,supplier_id,unit,cost_price,
                                  sale_price,quantity,min_stock,description,image)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (name, sku, category_id or None, supplier_id or None,
              unit, cost_price, sale_price, quantity, min_stock, description, image_bytes))
        pid = cur.lastrowid
        if quantity > 0:
            self._record_stock_movement(pid, "OPENING", quantity, quantity, "opening", None, "Opening stock")
        self.conn.commit()

    def update_product(self, pid, name, sku, category_id, supplier_id, unit,
                       cost_price, sale_price, quantity, min_stock, description,
                       image_bytes=None):
        old = self.get_product_by_id(pid)
        self.conn.execute("""
            UPDATE products SET name=?,sku=?,category_id=?,supplier_id=?,unit=?,
                cost_price=?,sale_price=?,quantity=?,min_stock=?,description=?,
                image=?,updated_at=datetime('now','localtime')
            WHERE id=?
        """, (name, sku, category_id or None, supplier_id or None,
              unit, cost_price, sale_price, quantity, min_stock, description, image_bytes, pid))
        if old and old["quantity"] != quantity:
            diff = quantity - old["quantity"]
            self._record_stock_movement(
                pid, "ADJUSTMENT", abs(diff), quantity, "manual", None,
                f"Manual adjustment {'+'if diff>0 else ''}{diff}"
            )
        self.conn.commit()

    def delete_product(self, pid):
        self.conn.execute("DELETE FROM products WHERE id=?", (pid,))
        self.conn.commit()

    def _record_stock_movement(self, product_id, move_type, quantity, balance,
                                ref_type, ref_id, note):
        self.conn.execute("""
            INSERT INTO stock_movements
                (product_id,type,quantity,balance,reference_type,reference_id,note)
            VALUES (?,?,?,?,?,?,?)
        """, (product_id, move_type, quantity, balance, ref_type, ref_id, note))

    # ─── Sales ────────────────────────────────────────────────────────────────

    def get_all_sales(self, search="", status=None, date_from=None, date_to=None):
        q = """
            SELECT s.id, s.invoice_no, COALESCE(c.name,'Walk-in') AS customer,
                   s.sale_date, s.subtotal, s.discount, s.tax_amount,
                   s.total, s.paid_amount, s.due_amount, s.payment_type, s.status, s.note
            FROM sales s LEFT JOIN customers c ON c.id=s.customer_id WHERE 1=1
        """
        p = []
        if search:
            q += " AND (s.invoice_no LIKE ? OR c.name LIKE ?)"
            p += [f"%{search}%"]*2
        if status:
            q += " AND s.status=?"
            p.append(status)
        if date_from:
            q += " AND s.sale_date >= ?"
            p.append(date_from)
        if date_to:
            q += " AND s.sale_date <= ?"
            p.append(date_to)
        return self.conn.execute(q + " ORDER BY s.id DESC", p).fetchall()

    def get_sale_items(self, sale_id):
        return self.conn.execute("""
            SELECT si.*, p.name AS product_name, p.unit
            FROM sale_items si JOIN products p ON p.id=si.product_id
            WHERE si.sale_id=?
        """, (sale_id,)).fetchall()

    def create_sale(self, customer_id, sale_date, items, discount, tax_rate,
                    paid_amount, payment_type, note):
        subtotal = sum(i["total"] for i in items)
        tax_amount = (subtotal - discount) * tax_rate / 100
        total = subtotal - discount + tax_amount
        due = total - paid_amount
        status = "paid" if due <= 0 else ("partial" if paid_amount > 0 else "unpaid")
        invoice_no = self._next_invoice()

        cur = self.conn.execute("""
            INSERT INTO sales (invoice_no,customer_id,sale_date,subtotal,discount,
                tax_rate,tax_amount,total,paid_amount,due_amount,payment_type,status,note)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (invoice_no, customer_id or None, sale_date, subtotal, discount,
              tax_rate, tax_amount, total, paid_amount, due, payment_type, status, note))
        sale_id = cur.lastrowid

        for item in items:
            self.conn.execute("""
                INSERT INTO sale_items (sale_id,product_id,quantity,unit_price,discount,total)
                VALUES (?,?,?,?,?,?)
            """, (sale_id, item["product_id"], item["qty"],
                  item["unit_price"], item.get("discount", 0), item["total"]))
            # Reduce stock
            prod = self.get_product_by_id(item["product_id"])
            new_qty = prod["quantity"] - item["qty"]
            self.conn.execute(
                "UPDATE products SET quantity=?,updated_at=datetime('now','localtime') WHERE id=?",
                (new_qty, item["product_id"])
            )
            self._record_stock_movement(
                item["product_id"], "SALE_OUT", item["qty"], new_qty,
                "sale", sale_id, f"Sale: {invoice_no}"
            )

        # Cash transaction for paid portion
        if paid_amount > 0:
            self.conn.execute("""
                INSERT INTO cash_transactions (type,reference_type,reference_id,
                    party_type,party_id,amount,description)
                VALUES ('COLLECTION','sale',?,?,?,?,?)
            """, (sale_id, "customer" if customer_id else None,
                  customer_id, paid_amount, f"Payment for {invoice_no}"))
            self._adjust_cash(paid_amount)

        # Update customer balance (due amount)
        if customer_id and due > 0:
            self.conn.execute(
                "UPDATE customers SET balance=balance+? WHERE id=?", (due, customer_id)
            )

        self._post_sale_journal(sale_id, invoice_no, customer_id, total,
                                paid_amount, due, items)
        self.conn.commit()
        return invoice_no

    def _post_sale_journal(self, sale_id, invoice_no, customer_id, total,
                           paid, due, items):
        je_no = self._next_journal()
        cur = self.conn.execute("""
            INSERT INTO journal_entries (entry_no,entry_date,description,reference_type,reference_id)
            VALUES (?,date('now','localtime'),?,?,?)
        """, (je_no, f"Sale Invoice {invoice_no}", "sale", sale_id))
        jid = cur.lastrowid
        cash_acc = self._acct("1001")
        ar_acc   = self._acct("1002")
        rev_acc  = self._acct("4001")
        cogs_acc = self._acct("5001")
        inv_acc  = self._acct("1003")
        lines = []
        if paid > 0:
            lines.append((jid, cash_acc, paid, 0, "Cash received"))
        if due > 0:
            lines.append((jid, ar_acc, due, 0, "Credit sale"))
        lines.append((jid, rev_acc, 0, total, "Sales revenue"))
        cogs = sum(self._get_cogs(i["product_id"], i["qty"]) for i in items)
        if cogs > 0:
            lines.append((jid, cogs_acc, cogs, 0, "Cost of goods sold"))
            lines.append((jid, inv_acc, 0, cogs, "Inventory reduced"))
        self.conn.executemany(
            "INSERT INTO journal_lines (journal_id,account_id,debit,credit,description) VALUES (?,?,?,?,?)",
            lines
        )

    def _get_cogs(self, product_id, qty):
        p = self.get_product_by_id(product_id)
        return (p["cost_price"] * qty) if p else 0

    def _acct(self, code):
        row = self.conn.execute("SELECT id FROM accounts WHERE code=?", (code,)).fetchone()
        return row["id"] if row else None

    def collect_sale_payment(self, sale_id, amount, note=""):
        sale = self.conn.execute("SELECT * FROM sales WHERE id=?", (sale_id,)).fetchone()
        if not sale:
            raise ValueError("Sale not found")
        if amount > sale["due_amount"]:
            raise ValueError(f"Amount exceeds due: ${sale['due_amount']:.2f}")
        new_paid = sale["paid_amount"] + amount
        new_due  = sale["due_amount"] - amount
        status = "paid" if new_due <= 0 else "partial"
        self.conn.execute(
            "UPDATE sales SET paid_amount=?,due_amount=?,status=? WHERE id=?",
            (new_paid, new_due, status, sale_id)
        )
        self.conn.execute("""
            INSERT INTO cash_transactions (type,reference_type,reference_id,
                party_type,party_id,amount,description)
            VALUES ('COLLECTION','sale',?,?,?,?,?)
        """, (sale_id, "customer", sale["customer_id"], amount,
              note or f"Collection for {sale['invoice_no']}"))
        self._adjust_cash(amount)
        if sale["customer_id"]:
            self.conn.execute(
                "UPDATE customers SET balance=balance-? WHERE id=?",
                (amount, sale["customer_id"])
            )
        # Journal
        je_no = self._next_journal()
        cur = self.conn.execute("""
            INSERT INTO journal_entries (entry_no,entry_date,description,reference_type,reference_id)
            VALUES (?,date('now','localtime'),?,?,?)
        """, (je_no, f"Cash collection for {sale['invoice_no']}", "collection", sale_id))
        jid = cur.lastrowid
        self.conn.executemany(
            "INSERT INTO journal_lines (journal_id,account_id,debit,credit,description) VALUES (?,?,?,?,?)",
            [(jid, self._acct("1001"), amount, 0, "Cash collected"),
             (jid, self._acct("1002"), 0, amount, "AR reduced")]
        )
        self.conn.commit()

    # ─── Purchases ────────────────────────────────────────────────────────────

    def get_all_purchases(self, search="", status=None, date_from=None, date_to=None):
        q = """
            SELECT p.id, p.po_number, COALESCE(s.name,'Unknown') AS supplier,
                   p.purchase_date, p.subtotal, p.discount, p.tax_amount,
                   p.total, p.paid_amount, p.due_amount, p.payment_type, p.status, p.note
            FROM purchases p LEFT JOIN suppliers s ON s.id=p.supplier_id WHERE 1=1
        """
        params = []
        if search:
            q += " AND (p.po_number LIKE ? OR s.name LIKE ?)"
            params += [f"%{search}%"]*2
        if status:
            q += " AND p.status=?"
            params.append(status)
        if date_from:
            q += " AND p.purchase_date >= ?"
            params.append(date_from)
        if date_to:
            q += " AND p.purchase_date <= ?"
            params.append(date_to)
        return self.conn.execute(q + " ORDER BY p.id DESC", params).fetchall()

    def get_purchase_items(self, purchase_id):
        return self.conn.execute("""
            SELECT pi.*, p.name AS product_name, p.unit
            FROM purchase_items pi JOIN products p ON p.id=pi.product_id
            WHERE pi.purchase_id=?
        """, (purchase_id,)).fetchall()

    def create_purchase(self, supplier_id, purchase_date, items, discount,
                        tax_rate, paid_amount, payment_type, note):
        subtotal = sum(i["total"] for i in items)
        tax_amount = (subtotal - discount) * tax_rate / 100
        total = subtotal - discount + tax_amount
        due = total - paid_amount
        status = "paid" if due <= 0 else ("partial" if paid_amount > 0 else "unpaid")
        po_number = self._next_po()

        cur = self.conn.execute("""
            INSERT INTO purchases (po_number,supplier_id,purchase_date,subtotal,discount,
                tax_rate,tax_amount,total,paid_amount,due_amount,payment_type,status,note)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (po_number, supplier_id or None, purchase_date, subtotal, discount,
              tax_rate, tax_amount, total, paid_amount, due, payment_type, status, note))
        pid = cur.lastrowid

        for item in items:
            self.conn.execute("""
                INSERT INTO purchase_items (purchase_id,product_id,quantity,unit_price,total)
                VALUES (?,?,?,?,?)
            """, (pid, item["product_id"], item["qty"], item["unit_price"], item["total"]))
            prod = self.get_product_by_id(item["product_id"])
            new_qty = prod["quantity"] + item["qty"]
            self.conn.execute(
                "UPDATE products SET quantity=?,cost_price=?,updated_at=datetime('now','localtime') WHERE id=?",
                (new_qty, item["unit_price"], item["product_id"])
            )
            self._record_stock_movement(
                item["product_id"], "PURCHASE_IN", item["qty"], new_qty,
                "purchase", pid, f"Purchase: {po_number}"
            )

        if paid_amount > 0:
            self.conn.execute("""
                INSERT INTO cash_transactions (type,reference_type,reference_id,
                    party_type,party_id,amount,description)
                VALUES ('DELIVERY','purchase',?,?,?,?,?)
            """, (pid, "supplier" if supplier_id else None,
                  supplier_id, paid_amount, f"Payment for {po_number}"))
            self._adjust_cash(-paid_amount)

        if supplier_id and due > 0:
            self.conn.execute(
                "UPDATE suppliers SET balance=balance+? WHERE id=?", (due, supplier_id)
            )

        self._post_purchase_journal(pid, po_number, supplier_id, total, paid_amount, due)
        self.conn.commit()
        return po_number

    def _post_purchase_journal(self, purchase_id, po_number, supplier_id,
                               total, paid, due):
        je_no = self._next_journal()
        cur = self.conn.execute("""
            INSERT INTO journal_entries (entry_no,entry_date,description,reference_type,reference_id)
            VALUES (?,date('now','localtime'),?,?,?)
        """, (je_no, f"Purchase Order {po_number}", "purchase", purchase_id))
        jid = cur.lastrowid
        lines = [
            (jid, self._acct("1003"), total, 0, "Inventory added"),
        ]
        if paid > 0:
            lines.append((jid, self._acct("1001"), 0, paid, "Cash paid"))
        if due > 0:
            lines.append((jid, self._acct("2001"), 0, due, "Supplier payable"))
        self.conn.executemany(
            "INSERT INTO journal_lines (journal_id,account_id,debit,credit,description) VALUES (?,?,?,?,?)",
            lines
        )

    def pay_supplier(self, purchase_id, amount, note=""):
        purchase = self.conn.execute("SELECT * FROM purchases WHERE id=?", (purchase_id,)).fetchone()
        if not purchase:
            raise ValueError("Purchase not found")
        if amount > purchase["due_amount"]:
            raise ValueError(f"Amount exceeds due: ${purchase['due_amount']:.2f}")
        new_paid = purchase["paid_amount"] + amount
        new_due  = purchase["due_amount"] - amount
        status = "paid" if new_due <= 0 else "partial"
        self.conn.execute(
            "UPDATE purchases SET paid_amount=?,due_amount=?,status=? WHERE id=?",
            (new_paid, new_due, status, purchase_id)
        )
        self.conn.execute("""
            INSERT INTO cash_transactions (type,reference_type,reference_id,
                party_type,party_id,amount,description)
            VALUES ('DELIVERY','purchase',?,?,?,?,?)
        """, (purchase_id, "supplier", purchase["supplier_id"], amount,
              note or f"Payment for {purchase['po_number']}"))
        self._adjust_cash(-amount)
        if purchase["supplier_id"]:
            self.conn.execute(
                "UPDATE suppliers SET balance=balance-? WHERE id=?",
                (amount, purchase["supplier_id"])
            )
        je_no = self._next_journal()
        cur = self.conn.execute("""
            INSERT INTO journal_entries (entry_no,entry_date,description,reference_type,reference_id)
            VALUES (?,date('now','localtime'),?,?,?)
        """, (je_no, f"Supplier payment for {purchase['po_number']}", "payment", purchase_id))
        jid = cur.lastrowid
        self.conn.executemany(
            "INSERT INTO journal_lines (journal_id,account_id,debit,credit,description) VALUES (?,?,?,?,?)",
            [(jid, self._acct("2001"), amount, 0, "AP reduced"),
             (jid, self._acct("1001"), 0, amount, "Cash paid")]
        )
        self.conn.commit()

    # ─── Cash Transactions ────────────────────────────────────────────────────

    def get_cash_transactions(self, search="", tx_type=None, date_from=None, date_to=None):
        q = """
            SELECT ct.id, ct.type, ct.description, ct.amount,
                   CASE ct.party_type
                     WHEN 'customer' THEN c.name
                     WHEN 'supplier' THEN s.name
                     ELSE '—'
                   END AS party_name,
                   ct.party_type, ct.reference_type, ct.reference_id, ct.created_at
            FROM cash_transactions ct
            LEFT JOIN customers c ON ct.party_type='customer' AND c.id=ct.party_id
            LEFT JOIN suppliers s ON ct.party_type='supplier' AND s.id=ct.party_id
            WHERE 1=1
        """
        p = []
        if search:
            q += " AND (ct.description LIKE ? OR c.name LIKE ? OR s.name LIKE ?)"
            p += [f"%{search}%"]*3
        if tx_type:
            q += " AND ct.type=?"
            p.append(tx_type)
        if date_from:
            q += " AND date(ct.created_at) >= ?"
            p.append(date_from)
        if date_to:
            q += " AND date(ct.created_at) <= ?"
            p.append(date_to)
        return self.conn.execute(q + " ORDER BY ct.id DESC", p).fetchall()

    def add_manual_cash_transaction(self, tx_type, amount, description):
        self.conn.execute("""
            INSERT INTO cash_transactions (type,amount,description) VALUES (?,?,?)
        """, (tx_type, amount, description))
        delta = amount if tx_type == "INCOME" else -amount
        self._adjust_cash(delta)
        je_no = self._next_journal()
        cur = self.conn.execute("""
            INSERT INTO journal_entries (entry_no,entry_date,description,reference_type)
            VALUES (?,date('now','localtime'),?,?)
        """, (je_no, description, tx_type.lower()))
        jid = cur.lastrowid
        if tx_type == "INCOME":
            lines = [(jid, self._acct("1001"), amount, 0, description),
                     (jid, self._acct("4002"), 0, amount, description)]
        else:
            lines = [(jid, self._acct("5003"), amount, 0, description),
                     (jid, self._acct("1001"), 0, amount, description)]
        self.conn.executemany(
            "INSERT INTO journal_lines (journal_id,account_id,debit,credit,description) VALUES (?,?,?,?,?)",
            lines
        )
        self.conn.commit()

    # ─── Stock ────────────────────────────────────────────────────────────────

    def get_stock_movements(self, product_id=None, search=""):
        q = """
            SELECT sm.id, p.name AS product, p.sku, sm.type,
                   sm.quantity, sm.balance, sm.reference_type, sm.note, sm.created_at
            FROM stock_movements sm
            JOIN products p ON p.id=sm.product_id
            WHERE 1=1
        """
        params = []
        if product_id:
            q += " AND sm.product_id=?"
            params.append(product_id)
        if search:
            q += " AND (p.name LIKE ? OR p.sku LIKE ? OR sm.note LIKE ?)"
            params += [f"%{search}%"]*3
        return self.conn.execute(q + " ORDER BY sm.id DESC", params).fetchall()

    def get_stock_summary(self):
        return self.conn.execute("""
            SELECT p.id, p.name, p.sku, c.name AS category, p.unit,
                   p.quantity, p.min_stock, p.cost_price, p.sale_price,
                   (p.quantity * p.cost_price) AS stock_value,
                   CASE WHEN p.quantity <= 0 THEN 'Out of Stock'
                        WHEN p.quantity <= p.min_stock THEN 'Low Stock'
                        ELSE 'In Stock' END AS stock_status
            FROM products p LEFT JOIN categories c ON c.id=p.category_id
            ORDER BY p.quantity ASC
        """).fetchall()

    # ─── Credit Management ────────────────────────────────────────────────────

    def get_credit_sales(self, search=""):
        q = """
            SELECT s.id, s.invoice_no, COALESCE(c.name,'Walk-in') AS customer,
                   c.phone, s.sale_date, s.total, s.paid_amount, s.due_amount, s.status
            FROM sales s LEFT JOIN customers c ON c.id=s.customer_id
            WHERE s.status IN ('partial','unpaid')
        """
        p = []
        if search:
            q += " AND (s.invoice_no LIKE ? OR c.name LIKE ? OR c.phone LIKE ?)"
            p += [f"%{search}%"]*3
        return self.conn.execute(q + " ORDER BY s.due_amount DESC", p).fetchall()

    def get_credit_purchases(self, search=""):
        q = """
            SELECT p.id, p.po_number, COALESCE(s.name,'Unknown') AS supplier,
                   s.phone, p.purchase_date, p.total, p.paid_amount, p.due_amount, p.status
            FROM purchases p LEFT JOIN suppliers s ON s.id=p.supplier_id
            WHERE p.status IN ('partial','unpaid')
        """
        params = []
        if search:
            q += " AND (p.po_number LIKE ? OR s.name LIKE ?)"
            params += [f"%{search}%"]*2
        return self.conn.execute(q + " ORDER BY p.due_amount DESC", params).fetchall()

    # ─── Accounting ───────────────────────────────────────────────────────────

    def get_all_accounts(self):
        return self.conn.execute(
            "SELECT id,code,name,account_type,normal_balance,description FROM accounts ORDER BY code"
        ).fetchall()

    def get_account_balance(self, account_id):
        row = self.conn.execute("""
            SELECT COALESCE(SUM(debit),0) AS total_dr, COALESCE(SUM(credit),0) AS total_cr
            FROM journal_lines WHERE account_id=?
        """, (account_id,)).fetchone()
        return row["total_dr"], row["total_cr"]

    def get_trial_balance(self):
        return self.conn.execute("""
            SELECT a.code, a.name, a.account_type, a.normal_balance,
                   COALESCE(SUM(jl.debit),0)  AS total_dr,
                   COALESCE(SUM(jl.credit),0) AS total_cr
            FROM accounts a
            LEFT JOIN journal_lines jl ON jl.account_id=a.id
            GROUP BY a.id ORDER BY a.code
        """).fetchall()

    def get_journal_entries(self, search="", date_from=None, date_to=None):
        q = """
            SELECT je.id, je.entry_no, je.entry_date, je.description,
                   je.reference_type,
                   COALESCE(SUM(jl.debit),0)  AS total_dr,
                   COALESCE(SUM(jl.credit),0) AS total_cr
            FROM journal_entries je
            LEFT JOIN journal_lines jl ON jl.journal_id=je.id
            WHERE 1=1
        """
        p = []
        if search:
            q += " AND (je.entry_no LIKE ? OR je.description LIKE ?)"
            p += [f"%{search}%"]*2
        if date_from:
            q += " AND je.entry_date >= ?"
            p.append(date_from)
        if date_to:
            q += " AND je.entry_date <= ?"
            p.append(date_to)
        return self.conn.execute(q + " GROUP BY je.id ORDER BY je.id DESC", p).fetchall()

    def get_journal_lines(self, journal_id):
        return self.conn.execute("""
            SELECT jl.*, a.code, a.name AS account_name
            FROM journal_lines jl JOIN accounts a ON a.id=jl.account_id
            WHERE jl.journal_id=?
        """, (journal_id,)).fetchall()

    # ─── Reports ──────────────────────────────────────────────────────────────

    def get_sales_report(self, date_from=None, date_to=None):
        q = """
            SELECT s.invoice_no, COALESCE(c.name,'Walk-in') AS customer,
                   s.sale_date, s.subtotal, s.discount, s.tax_amount,
                   s.total, s.paid_amount, s.due_amount, s.status
            FROM sales s LEFT JOIN customers c ON c.id=s.customer_id WHERE 1=1
        """
        p = []
        if date_from: q += " AND s.sale_date >= ?"; p.append(date_from)
        if date_to:   q += " AND s.sale_date <= ?"; p.append(date_to)
        return self.conn.execute(q + " ORDER BY s.sale_date", p).fetchall()

    def get_purchase_report(self, date_from=None, date_to=None):
        q = """
            SELECT p.po_number, COALESCE(s.name,'Unknown') AS supplier,
                   p.purchase_date, p.subtotal, p.discount, p.tax_amount,
                   p.total, p.paid_amount, p.due_amount, p.status
            FROM purchases p LEFT JOIN suppliers s ON s.id=p.supplier_id WHERE 1=1
        """
        p = []
        if date_from: q += " AND p.purchase_date >= ?"; p.append(date_from)
        if date_to:   q += " AND p.purchase_date <= ?"; p.append(date_to)
        return self.conn.execute(q + " ORDER BY p.purchase_date", p).fetchall()

    def get_profit_loss(self, date_from=None, date_to=None):
        p = []
        date_filter = ""
        if date_from:
            date_filter += " AND sale_date >= ?"
            p.append(date_from)
        if date_to:
            date_filter += " AND sale_date <= ?"
            p.append(date_to)
        revenue = self.conn.execute(
            f"SELECT COALESCE(SUM(total),0) FROM sales WHERE 1=1{date_filter}", p
        ).fetchone()[0]
        p2 = []
        df2 = ""
        if date_from: df2 += " AND purchase_date >= ?"; p2.append(date_from)
        if date_to:   df2 += " AND purchase_date <= ?"; p2.append(date_to)
        purchases = self.conn.execute(
            f"SELECT COALESCE(SUM(total),0) FROM purchases WHERE 1=1{df2}", p2
        ).fetchone()[0]
        profit = revenue - purchases
        # Gross Profit = Sale Revenue − Cost of Goods Sold (cost_price × qty per item)
        gp_row = self.conn.execute(f"""
            SELECT COALESCE(SUM(si.total), 0)                   AS rev,
                   COALESCE(SUM(si.quantity * p.cost_price), 0) AS cogs
            FROM sale_items si
            JOIN products p  ON p.id  = si.product_id
            JOIN sales    s  ON s.id  = si.sale_id
            WHERE 1=1{date_filter}
        """, p).fetchone()
        gross_profit = gp_row["rev"] - gp_row["cogs"]
        cogs = gp_row["cogs"]
        return dict(revenue=revenue, purchases=purchases, profit=profit,
                    cogs=cogs, gross_profit=gross_profit)

    def get_period_summary(self, period, date_from=None, date_to=None):
        """Returns sales/purchase totals grouped by day/week/month/year."""
        fmt_map = {
            "daily":   "%Y-%m-%d",
            "weekly":  "%Y-W%W",
            "monthly": "%Y-%m",
            "yearly":  "%Y",
        }
        fmt = fmt_map.get(period, "%Y-%m-%d")
        p_s, p_p = [], []
        df_s, df_p = "", ""
        if date_from:
            df_s += " AND sale_date >= ?";     p_s.append(date_from)
            df_p += " AND purchase_date >= ?"; p_p.append(date_from)
        if date_to:
            df_s += " AND sale_date <= ?";     p_s.append(date_to)
            df_p += " AND purchase_date <= ?"; p_p.append(date_to)
        sales = self.conn.execute(
            f"SELECT strftime('{fmt}', sale_date) AS period, "
            f"COALESCE(SUM(total),0) AS total FROM sales WHERE 1=1{df_s} "
            "GROUP BY period ORDER BY period", p_s
        ).fetchall()
        purchases = self.conn.execute(
            f"SELECT strftime('{fmt}', purchase_date) AS period, "
            f"COALESCE(SUM(total),0) AS total FROM purchases WHERE 1=1{df_p} "
            "GROUP BY period ORDER BY period", p_p
        ).fetchall()
        result = {}
        for row in sales:
            result.setdefault(row["period"], {"sales": 0.0, "purchases": 0.0})
            result[row["period"]]["sales"] = row["total"]
        for row in purchases:
            result.setdefault(row["period"], {"sales": 0.0, "purchases": 0.0})
            result[row["period"]]["purchases"] = row["total"]
        return sorted(result.items())

    # ─── Sales Returns ────────────────────────────────────────────────────────

    def _next_sale_return(self):
        n = int(self.get_setting("sale_return_counter", "0")) + 1
        self.set_setting("sale_return_counter", n)
        return f"SR-{n:05d}"

    def _next_pur_return(self):
        n = int(self.get_setting("pur_return_counter", "0")) + 1
        self.set_setting("pur_return_counter", n)
        return f"PR-{n:05d}"

    def get_all_sales_returns(self, search="", date_from=None, date_to=None):
        q = """
            SELECT sr.id, sr.return_no, s.invoice_no,
                   COALESCE(c.name,'Walk-in') AS customer,
                   sr.return_date, sr.total, sr.refund_type, sr.reason, sr.created_at
            FROM sales_returns sr
            JOIN sales s ON s.id = sr.sale_id
            LEFT JOIN customers c ON c.id = s.customer_id
            WHERE 1=1
        """
        p = []
        if search:
            q += " AND (sr.return_no LIKE ? OR s.invoice_no LIKE ? OR c.name LIKE ?)"
            p += [f"%{search}%"] * 3
        if date_from:
            q += " AND sr.return_date >= ?"; p.append(date_from)
        if date_to:
            q += " AND sr.return_date <= ?"; p.append(date_to)
        return self.conn.execute(q + " ORDER BY sr.id DESC", p).fetchall()

    def get_sale_return_items(self, return_id):
        return self.conn.execute("""
            SELECT sri.*, p.name AS product_name, p.unit
            FROM sales_return_items sri
            JOIN products p ON p.id = sri.product_id
            WHERE sri.return_id = ?
        """, (return_id,)).fetchall()

    def get_sale_items_for_return(self, sale_id):
        """Return sale items with already-returned quantities deducted."""
        return self.conn.execute("""
            SELECT si.id, si.product_id, p.name AS product_name, p.unit,
                   si.quantity AS sold_qty, si.unit_price,
                   COALESCE((
                       SELECT SUM(sri.quantity)
                       FROM sales_return_items sri
                       JOIN sales_returns sr ON sr.id = sri.return_id
                       WHERE sri.product_id = si.product_id AND sr.sale_id = si.sale_id
                   ), 0) AS returned_qty
            FROM sale_items si
            JOIN products p ON p.id = si.product_id
            WHERE si.sale_id = ?
        """, (sale_id,)).fetchall()

    def create_sale_return(self, sale_id, items, refund_type, reason, note, return_date):
        """
        items: list of {product_id, qty, unit_price, total}
        refund_type: 'cash' | 'adjust'  (adjust = reduce customer balance)
        """
        sale = self.conn.execute("SELECT * FROM sales WHERE id=?", (sale_id,)).fetchone()
        if not sale:
            raise ValueError("Sale not found")

        total = sum(i["total"] for i in items)
        if total <= 0:
            raise ValueError("No items selected for return")

        return_no = self._next_sale_return()
        cur = self.conn.execute("""
            INSERT INTO sales_returns
                (return_no, sale_id, return_date, reason, total, refund_type, note)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (return_no, sale_id, return_date, reason, total, refund_type, note))
        rid = cur.lastrowid

        for item in items:
            if item["qty"] <= 0:
                continue
            self.conn.execute("""
                INSERT INTO sales_return_items
                    (return_id, product_id, quantity, unit_price, total)
                VALUES (?, ?, ?, ?, ?)
            """, (rid, item["product_id"], item["qty"], item["unit_price"], item["total"]))

            # Restock inventory
            prod = self.get_product_by_id(item["product_id"])
            new_qty = prod["quantity"] + item["qty"]
            self.conn.execute(
                "UPDATE products SET quantity=?, updated_at=datetime('now','localtime') WHERE id=?",
                (new_qty, item["product_id"])
            )
            self._record_stock_movement(
                item["product_id"], "SALE_RETURN", item["qty"], new_qty,
                "sale_return", rid, f"Sale Return: {return_no}"
            )

        # Refund
        if refund_type == "cash":
            # Pay cash back to customer → reduces cash balance
            self.conn.execute("""
                INSERT INTO cash_transactions
                    (type, reference_type, reference_id, party_type, party_id, amount, description)
                VALUES ('EXPENSE', 'sale_return', ?, ?, ?, ?, ?)
            """, (rid, "customer" if sale["customer_id"] else None,
                  sale["customer_id"], total, f"Cash refund for {return_no}"))
            self._adjust_cash(-total)
        else:
            # Adjust: reduce customer's outstanding balance
            if sale["customer_id"]:
                self.conn.execute(
                    "UPDATE customers SET balance = MAX(0, balance - ?) WHERE id=?",
                    (total, sale["customer_id"])
                )
            # Also reduce the sale's due_amount
            new_due = max(0, (sale["due_amount"] or 0) - total)
            new_paid = (sale["paid_amount"] or 0)
            new_status = "paid" if new_due <= 0 else (
                "partial" if new_paid > 0 else "unpaid")
            self.conn.execute(
                "UPDATE sales SET due_amount=?, status=? WHERE id=?",
                (new_due, new_status, sale_id)
            )

        # Journal entry
        je_no = self._next_journal()
        cur2 = self.conn.execute("""
            INSERT INTO journal_entries
                (entry_no, entry_date, description, reference_type, reference_id)
            VALUES (?, date('now','localtime'), ?, 'sale_return', ?)
        """, (je_no, f"Sales Return {return_no}", rid))
        jid = cur2.lastrowid

        lines = []
        lines.append((jid, self._acct("4001"), total, 0, "Sales revenue reversed"))  # Dr Revenue
        if refund_type == "cash":
            lines.append((jid, self._acct("1001"), 0, total, "Cash refunded"))       # Cr Cash
        else:
            lines.append((jid, self._acct("1002"), 0, total, "AR adjusted"))         # Cr AR
        # Restock journal: Dr Inventory, Cr COGS
        cogs = sum(self._get_cogs(i["product_id"], i["qty"]) for i in items)
        if cogs > 0:
            lines.append((jid, self._acct("1003"), cogs, 0, "Inventory restocked"))
            lines.append((jid, self._acct("5001"), 0, cogs, "COGS reversed"))

        self.conn.executemany(
            "INSERT INTO journal_lines (journal_id,account_id,debit,credit,description) VALUES (?,?,?,?,?)",
            lines
        )
        self.conn.commit()
        return return_no

    # ─── Purchase Returns ─────────────────────────────────────────────────────

    def get_all_purchase_returns(self, search="", date_from=None, date_to=None):
        q = """
            SELECT pr.id, pr.return_no, p.po_number,
                   COALESCE(s.name,'Unknown') AS supplier,
                   pr.return_date, pr.total, pr.refund_type, pr.reason, pr.created_at
            FROM purchase_returns pr
            JOIN purchases p ON p.id = pr.purchase_id
            LEFT JOIN suppliers s ON s.id = p.supplier_id
            WHERE 1=1
        """
        params = []
        if search:
            q += " AND (pr.return_no LIKE ? OR p.po_number LIKE ? OR s.name LIKE ?)"
            params += [f"%{search}%"] * 3
        if date_from:
            q += " AND pr.return_date >= ?"; params.append(date_from)
        if date_to:
            q += " AND pr.return_date <= ?"; params.append(date_to)
        return self.conn.execute(q + " ORDER BY pr.id DESC", params).fetchall()

    def get_purchase_return_items(self, return_id):
        return self.conn.execute("""
            SELECT pri.*, p.name AS product_name, p.unit
            FROM purchase_return_items pri
            JOIN products p ON p.id = pri.product_id
            WHERE pri.return_id = ?
        """, (return_id,)).fetchall()

    def get_purchase_items_for_return(self, purchase_id):
        """Return purchase items with already-returned quantities deducted."""
        return self.conn.execute("""
            SELECT pi.id, pi.product_id, p.name AS product_name, p.unit,
                   pi.quantity AS purchased_qty, pi.unit_price,
                   COALESCE((
                       SELECT SUM(pri.quantity)
                       FROM purchase_return_items pri
                       JOIN purchase_returns pr ON pr.id = pri.return_id
                       WHERE pri.product_id = pi.product_id AND pr.purchase_id = pi.purchase_id
                   ), 0) AS returned_qty
            FROM purchase_items pi
            JOIN products p ON p.id = pi.product_id
            WHERE pi.purchase_id = ?
        """, (purchase_id,)).fetchall()

    def create_purchase_return(self, purchase_id, items, refund_type, reason, note, return_date):
        """
        refund_type: 'cash' | 'adjust'
          cash   → supplier pays us cash back  → increases our cash
          adjust → reduce what we owe supplier → decreases payable
        """
        purchase = self.conn.execute(
            "SELECT * FROM purchases WHERE id=?", (purchase_id,)
        ).fetchone()
        if not purchase:
            raise ValueError("Purchase not found")

        total = sum(i["total"] for i in items)
        if total <= 0:
            raise ValueError("No items selected for return")

        return_no = self._next_pur_return()
        cur = self.conn.execute("""
            INSERT INTO purchase_returns
                (return_no, purchase_id, return_date, reason, total, refund_type, note)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (return_no, purchase_id, return_date, reason, total, refund_type, note))
        rid = cur.lastrowid

        for item in items:
            if item["qty"] <= 0:
                continue
            self.conn.execute("""
                INSERT INTO purchase_return_items
                    (return_id, product_id, quantity, unit_price, total)
                VALUES (?, ?, ?, ?, ?)
            """, (rid, item["product_id"], item["qty"], item["unit_price"], item["total"]))

            # Deduct stock
            prod = self.get_product_by_id(item["product_id"])
            new_qty = max(0, prod["quantity"] - item["qty"])
            self.conn.execute(
                "UPDATE products SET quantity=?, updated_at=datetime('now','localtime') WHERE id=?",
                (new_qty, item["product_id"])
            )
            self._record_stock_movement(
                item["product_id"], "PURCHASE_RETURN", item["qty"], new_qty,
                "purchase_return", rid, f"Purchase Return: {return_no}"
            )

        if refund_type == "cash":
            # Supplier refunds us cash → increases our cash
            self.conn.execute("""
                INSERT INTO cash_transactions
                    (type, reference_type, reference_id, party_type, party_id, amount, description)
                VALUES ('INCOME', 'purchase_return', ?, ?, ?, ?, ?)
            """, (rid, "supplier" if purchase["supplier_id"] else None,
                  purchase["supplier_id"], total, f"Refund from supplier: {return_no}"))
            self._adjust_cash(total)
        else:
            # Adjust: reduce what we owe supplier (payable)
            if purchase["supplier_id"]:
                self.conn.execute(
                    "UPDATE suppliers SET balance = MAX(0, balance - ?) WHERE id=?",
                    (total, purchase["supplier_id"])
                )
            # Reduce purchase due amount
            new_due = max(0, (purchase["due_amount"] or 0) - total)
            new_paid = purchase["paid_amount"] or 0
            new_status = "paid" if new_due <= 0 else (
                "partial" if new_paid > 0 else "unpaid")
            self.conn.execute(
                "UPDATE purchases SET due_amount=?, status=? WHERE id=?",
                (new_due, new_status, purchase_id)
            )

        # Journal entry
        je_no = self._next_journal()
        cur2 = self.conn.execute("""
            INSERT INTO journal_entries
                (entry_no, entry_date, description, reference_type, reference_id)
            VALUES (?, date('now','localtime'), ?, 'purchase_return', ?)
        """, (je_no, f"Purchase Return {return_no}", rid))
        jid = cur2.lastrowid

        lines = []
        if refund_type == "cash":
            lines.append((jid, self._acct("1001"), total, 0, "Cash received from supplier"))
        else:
            lines.append((jid, self._acct("2001"), total, 0, "AP reduced"))
        lines.append((jid, self._acct("1003"), 0, total, "Inventory returned"))

        self.conn.executemany(
            "INSERT INTO journal_lines (journal_id,account_id,debit,credit,description) VALUES (?,?,?,?,?)",
            lines
        )
        self.conn.commit()
        return return_no

    # ─── Manual Transactions ──────────────────────────────────────────────────

    def get_all_transactions(self, search="", tx_type=None):
        q = """
            SELECT t.id, p.name AS product, p.sku, t.type,
                   t.quantity, t.price, t.note, t.created_at
            FROM transactions t
            JOIN products p ON p.id = t.product_id
            WHERE 1=1
        """
        params = []
        if search:
            q += " AND (p.name LIKE ? OR p.sku LIKE ? OR t.note LIKE ?)"
            params += [f"%{search}%"] * 3
        if tx_type:
            q += " AND t.type=?"
            params.append(tx_type)
        return self.conn.execute(q + " ORDER BY t.id DESC", params).fetchall()

    def add_transaction(self, product_id, tx_type, quantity, price, note):
        prod = self.get_product_by_id(product_id)
        if not prod:
            raise ValueError("Product not found")
        if tx_type == "OUT" and prod["quantity"] < quantity:
            raise ValueError(f"Insufficient stock. Available: {prod['quantity']}")
        self.conn.execute(
            "INSERT INTO transactions (product_id,type,quantity,price,note) VALUES (?,?,?,?,?)",
            (product_id, tx_type, quantity, price, note)
        )
        delta = quantity if tx_type == "IN" else -quantity
        new_qty = prod["quantity"] + delta
        self.conn.execute(
            "UPDATE products SET quantity=?,updated_at=datetime('now','localtime') WHERE id=?",
            (new_qty, product_id)
        )
        self._record_stock_movement(
            product_id, "MANUAL", quantity, new_qty,
            "manual", None, note or f"Manual stock {tx_type.lower()}"
        )
        self.conn.commit()

    # ─── Company Info ─────────────────────────────────────────────────────────

    def get_company_info(self):
        return {"name": self.get_setting("company_name", "My Company")}

    def close(self):
        self.conn.close()
