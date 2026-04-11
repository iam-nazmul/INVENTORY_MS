import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QScrollArea,
    QLineEdit, QMessageBox, QDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QByteArray
from PyQt6.QtGui import QFont, QPixmap, QPainter, QPainterPath

from database import Database
from pages.dashboard    import DashboardPage
from pages.products     import ProductsPage
from pages.customers    import CustomersPage
from pages.suppliers    import SuppliersPage
from pages.sales        import SalesPage
from pages.purchases    import PurchasesPage
from pages.cash         import CashPage
from pages.stock        import StockPage
from pages.credit       import CreditPage
from pages.accounting      import AccountingPage
from pages.reports         import ReportsPage
from pages.categories      import CategoriesPage
from pages.sales_return    import SalesReturnPage
from pages.purchase_return import PurchaseReturnPage
from pages.transactions    import TransactionsPage
from pages.users           import UsersPage
from pages.roles           import RolesPage


APP_STYLE = """
    QMainWindow { background: #F1F5F9; }
    QWidget { font-family: 'Segoe UI', system-ui, sans-serif; }
    QScrollBar:vertical {
        background: #F1F5F9; width: 8px; border-radius: 4px; border: none;
    }
    QScrollBar::handle:vertical {
        background: #CBD5E1; border-radius: 4px; min-height: 30px;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    QToolTip {
        background: #1E293B; color: white; border: none;
        padding: 4px 8px; border-radius: 4px; font-size: 12px;
    }
"""

# (icon, label, section_separator_before)
NAV_ITEMS = [
    ("📊", "Dashboard",        None),
    (None, None,               "INVENTORY"),
    ("📦", "Products",         None),
    ("📈", "Stock",            None),
    ("🔄", "Transactions",     None),
    (None, None,               "TRADING"),
    ("🛒", "Sales",            None),
    ("↩", "Sales Return",     None),
    ("📋", "Purchases",        None),
    ("↪", "Purchase Return",  None),
    ("💳", "Credit",           None),
    (None, None,               "PARTIES"),
    ("👥", "Customers",        None),
    ("🚚", "Suppliers",        None),
    (None, None,               "FINANCE"),
    ("💰", "Cash",             None),
    ("📒", "Accounting",       None),
    (None, None,               "ANALYTICS"),
    ("📄", "Reports",          None),
    (None, None,               "SETTINGS"),
    ("🏷", "Categories",       None),
    ("👤", "Users",            None),
    ("🔑", "Roles",            None),
]


class NavButton(QPushButton):
    BASE = """
        QPushButton {{
            background: transparent; color: #94A3B8; border: none;
            border-radius: 8px; text-align: left;
            padding: 9px 14px; font-size: 13px; font-weight: 500;
        }}
        QPushButton:hover {{ background: #334155; color: #F1F5F9; }}
    """
    ACTIVE = """
        QPushButton {{
            background: #4F46E5; color: white; border: none;
            border-radius: 8px; text-align: left;
            padding: 9px 14px; font-size: 13px; font-weight: 600;
        }}
    """

    def __init__(self, icon, label):
        super().__init__(f"  {icon}  {label}")
        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_active(False)

    def set_active(self, active):
        self.setStyleSheet((self.ACTIVE if active else self.BASE).format())


class Sidebar(QFrame):
    def __init__(self, on_nav, on_logout, user=None, allowed_menus=None, on_change_password=None):
        super().__init__()
        self.setObjectName("sidebar")
        self.setStyleSheet("QFrame#sidebar { background: #1E293B; }")
        self.setFixedWidth(200)
        self._buttons = {}
        self._on_nav = on_nav
        self._on_change_password = on_change_password

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Logo
        logo_frame = QFrame()
        logo_frame.setStyleSheet("background: #0F172A;")
        logo_frame.setFixedHeight(60)
        logo_layout = QVBoxLayout(logo_frame)
        logo_layout.setContentsMargins(16, 0, 16, 0)
        logo_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        logo = QLabel("⬛  IMS")
        logo.setStyleSheet("color: white; font-size: 17px; font-weight: 800;")
        sub  = QLabel("Inventory Manager")
        sub.setStyleSheet("color: #64748B; font-size: 10px;")
        logo_layout.addWidget(logo)
        logo_layout.addWidget(sub)
        outer.addWidget(logo_frame)

        # Scrollable nav — build groups then filter by allowed_menus
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        nav_widget = QWidget(); nav_widget.setStyleSheet("background: transparent;")
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(10, 10, 10, 10)
        nav_layout.setSpacing(2)

        # Group NAV_ITEMS by section so we can skip empty sections
        _groups = []          # [(section_str_or_None, [(icon, label), ...])]
        _cur_sec, _cur_items = None, []
        for icon, label, section in NAV_ITEMS:
            if section is not None:
                _groups.append((_cur_sec, _cur_items))
                _cur_sec, _cur_items = section, []
            elif icon and label:
                _cur_items.append((icon, label))
        _groups.append((_cur_sec, _cur_items))

        SEP_STYLE = ("color: #475569; font-size: 9px; font-weight: 700; "
                     "letter-spacing: 1px; padding: 10px 6px 4px 6px; background: transparent;")

        for sec, items in _groups:
            visible = [(i, l) for i, l in items
                       if allowed_menus is None or l in allowed_menus]
            if not visible:
                continue
            if sec:
                sep = QLabel(sec); sep.setStyleSheet(SEP_STYLE)
                nav_layout.addWidget(sep)
            for icon, label in visible:
                nav_btn = NavButton(icon, label)
                nav_btn.clicked.connect(lambda _, l=label: self._on_nav(l))
                nav_layout.addWidget(nav_btn)
                self._buttons[label] = nav_btn

        nav_layout.addStretch()
        scroll.setWidget(nav_widget)
        outer.addWidget(scroll)

        # User card
        user_frame = QFrame()
        user_frame.setStyleSheet("background: #0F172A; border-top: 1px solid #334155;")
        user_layout = QVBoxLayout(user_frame)
        user_layout.setContentsMargins(14, 10, 14, 4)
        user_layout.setSpacing(4)

        uname = (user or {}).get("username", "—")
        urole = ((user or {}).get("role_name") or (user or {}).get("role", "staff")).capitalize()
        photo_data = (user or {}).get("photo")

        # Avatar row: circular photo (if exists) + name/role stacked beside it
        avatar_row = QHBoxLayout(); avatar_row.setSpacing(10); avatar_row.setContentsMargins(0,0,0,0)

        SIZE = 40
        avatar_lbl = QLabel()
        avatar_lbl.setFixedSize(SIZE, SIZE)
        avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if photo_data:
            pm = QPixmap()
            pm.loadFromData(QByteArray(photo_data))
            if not pm.isNull():
                pm = pm.scaled(SIZE, SIZE,
                               Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                               Qt.TransformationMode.SmoothTransformation)
                rounded = QPixmap(SIZE, SIZE)
                rounded.fill(Qt.GlobalColor.transparent)
                painter = QPainter(rounded)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                path = QPainterPath()
                path.addEllipse(0, 0, SIZE, SIZE)
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, pm)
                painter.end()
                avatar_lbl.setPixmap(rounded)
            else:
                photo_data = None  # fall through to emoji
        if not photo_data:
            avatar_lbl.setText("👤")
            avatar_lbl.setStyleSheet(
                f"font-size:22px;background:transparent;border:none;"
            )

        text_col = QVBoxLayout(); text_col.setSpacing(1)
        name_lbl = QLabel(uname)
        name_lbl.setStyleSheet("color:#E2E8F0;font-size:12px;font-weight:600;background:transparent;")
        role_lbl = QLabel(urole)
        role_lbl.setStyleSheet("color:#64748B;font-size:10px;background:transparent;")
        text_col.addWidget(name_lbl)
        text_col.addWidget(role_lbl)

        avatar_row.addWidget(avatar_lbl)
        avatar_row.addLayout(text_col)
        avatar_row.addStretch()
        user_layout.addLayout(avatar_row)

        chpw_btn = QPushButton("🔑  Change Password")
        chpw_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        chpw_btn.setFixedHeight(30)
        chpw_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #818CF8; border: none;
                font-size: 11px; font-weight: 600; text-align: left; padding: 4px 2px;
            }
            QPushButton:hover { color: #A5B4FC; }
        """)
        chpw_btn.clicked.connect(lambda: on_change_password() if on_change_password else None)
        user_layout.addWidget(chpw_btn)

        logout_btn = QPushButton("⎋  Logout")
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.setFixedHeight(30)
        logout_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #F87171; border: none;
                font-size: 11px; font-weight: 600; text-align: left; padding: 4px 2px;
            }
            QPushButton:hover { color: #FCA5A5; }
        """)
        logout_btn.clicked.connect(on_logout)
        user_layout.addWidget(logout_btn)

        # Footer version
        footer = QLabel("  v2.0  ·  SQLite3")
        footer.setStyleSheet("color: #334155; font-size: 9px; padding: 4px 14px 8px 14px; background: #0F172A;")
        user_layout.addWidget(footer)

        outer.addWidget(user_frame)

    def set_active(self, label):
        for lbl, btn in self._buttons.items():
            btn.set_active(lbl == label)


AUTH_STYLE = """
    QDialog { background: #1E293B; }
    QLabel#title   { color: white; font-size: 22px; font-weight: 800; }
    QLabel#subtitle { color: #64748B; font-size: 12px; }
    QLabel#field   { color: #94A3B8; font-size: 11px; font-weight: 600; letter-spacing: 1px; }
    QLabel#error   { color: #F87171; font-size: 12px; }
    QLabel#success { color: #34D399; font-size: 12px; }
    QLineEdit {
        background: #0F172A; color: white; border: 1px solid #334155;
        border-radius: 8px; padding: 0px 14px; font-size: 13px;
    }
    QLineEdit:focus { border: 1px solid #4F46E5; }
    QPushButton#primary_btn {
        background: #4F46E5; color: white; border: none;
        border-radius: 8px; padding: 11px; font-size: 14px; font-weight: 700;
    }
    QPushButton#primary_btn:hover   { background: #4338CA; }
    QPushButton#primary_btn:pressed { background: #3730A3; }
    QPushButton#link_btn {
        background: transparent; color: #818CF8; border: none;
        font-size: 12px; padding: 4px;
    }
    QPushButton#link_btn:hover { color: #A5B4FC; }
"""


class SelfChangePasswordDialog(QDialog):
    """Lets the currently-logged-in user change their own password."""

    def __init__(self, db: "Database", user: dict, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_id = user["id"]
        self.setWindowTitle("Change My Password – IMS")
        self.setFixedSize(380, 460)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.MSWindowsFixedSizeDialogHint)
        self.setStyleSheet(AUTH_STYLE)
        self._build_ui(user.get("username", ""))

    def _build_ui(self, username):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 36, 40, 30)
        layout.setSpacing(0)

        title = QLabel("⬛  Change Password")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel(f"Logged in as: {username}")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(24)

        for attr, label, ph in [
            ("_inp_old",  "CURRENT PASSWORD", "Enter your current password"),
            ("_inp_new",  "NEW PASSWORD",      "At least 4 characters"),
            ("_inp_conf", "CONFIRM PASSWORD",  "Repeat new password"),
        ]:
            lbl = QLabel(label); lbl.setObjectName("field")
            inp = QLineEdit(); inp.setPlaceholderText(ph); inp.setFixedHeight(40)
            inp.setEchoMode(QLineEdit.EchoMode.Password)
            layout.addWidget(lbl)
            layout.addSpacing(4)
            layout.addWidget(inp)
            layout.addSpacing(12)
            setattr(self, attr, inp)

        self._msg = QLabel("")
        self._msg.setObjectName("error")
        self._msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._msg.setWordWrap(True)
        layout.addWidget(self._msg)
        layout.addSpacing(10)

        save_btn = QPushButton("Save Password")
        save_btn.setObjectName("primary_btn")
        save_btn.setFixedHeight(44)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._submit)
        layout.addWidget(save_btn)
        layout.addSpacing(8)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("link_btn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self._inp_conf.returnPressed.connect(self._submit)
        self._inp_new.returnPressed.connect(self._inp_conf.setFocus)
        self._inp_old.returnPressed.connect(self._inp_new.setFocus)

    def _submit(self):
        old_pw  = self._inp_old.text()
        new_pw  = self._inp_new.text()
        confirm = self._inp_conf.text()

        if not old_pw:
            self._show_error("Please enter your current password.")
            return
        if not self.db.verify_user_password(self.user_id, old_pw):
            self._show_error("Current password is incorrect.")
            self._inp_old.clear(); self._inp_old.setFocus()
            return
        if not new_pw:
            self._show_error("New password cannot be empty.")
            return
        if new_pw != confirm:
            self._show_error("New passwords do not match.")
            self._inp_conf.clear(); self._inp_conf.setFocus()
            return
        try:
            self.db.set_user_password(self.user_id, new_pw)
            self._msg.setStyleSheet("color: #34D399; font-size: 12px;")
            self._msg.setText("Password changed successfully!")
            QTimer.singleShot(1200, self.accept)
        except ValueError as e:
            self._show_error(str(e))

    def _show_error(self, text):
        self._msg.setStyleSheet("color: #F87171; font-size: 12px;")
        self._msg.setText(text)


class RegisterDialog(QDialog):
    def __init__(self, db: "Database"):
        super().__init__()
        self.db = db
        self.setWindowTitle("Register – IMS")
        self.setFixedSize(380, 460)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.MSWindowsFixedSizeDialogHint)
        self.setStyleSheet(AUTH_STYLE)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 36, 40, 30)
        layout.setSpacing(0)

        title = QLabel("⬛  IMS")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("Create a new account")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(24)

        for attr, label, ph, echo in [
            ("_inp_user", "USERNAME",         "Choose a username",      False),
            ("_inp_pass", "PASSWORD",         "At least 4 characters",  True),
            ("_inp_conf", "CONFIRM PASSWORD", "Repeat your password",   True),
        ]:
            lbl = QLabel(label); lbl.setObjectName("field")
            inp = QLineEdit(); inp.setPlaceholderText(ph); inp.setFixedHeight(40)
            if echo:
                inp.setEchoMode(QLineEdit.EchoMode.Password)
            layout.addWidget(lbl)
            layout.addSpacing(4)
            layout.addWidget(inp)
            layout.addSpacing(12)
            setattr(self, attr, inp)

        self._msg = QLabel("")
        self._msg.setObjectName("error")
        self._msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._msg.setWordWrap(True)
        layout.addWidget(self._msg)
        layout.addSpacing(10)

        reg_btn = QPushButton("Create Account")
        reg_btn.setObjectName("primary_btn")
        reg_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reg_btn.clicked.connect(self._attempt_register)
        layout.addWidget(reg_btn)
        layout.addSpacing(8)

        back_btn = QPushButton("← Back to Login")
        back_btn.setObjectName("link_btn")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self.reject)
        layout.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self._inp_conf.returnPressed.connect(self._attempt_register)
        self._inp_pass.returnPressed.connect(self._inp_conf.setFocus)
        self._inp_user.returnPressed.connect(self._inp_pass.setFocus)

    def _attempt_register(self):
        username = self._inp_user.text().strip()
        password = self._inp_pass.text()
        confirm  = self._inp_conf.text()

        if not username or not password:
            self._show_error("Username and password are required.")
            return
        if password != confirm:
            self._show_error("Passwords do not match.")
            self._inp_conf.clear(); self._inp_conf.setFocus()
            return
        try:
            self.db.register_user(username, password)
            self._msg.setObjectName("success")
            self._msg.setStyleSheet("color: #34D399; font-size: 12px;")
            self._msg.setText(f"Account '{username}' created! You can now log in.")
        except ValueError as e:
            self._show_error(str(e))

    def _show_error(self, text):
        self._msg.setStyleSheet("color: #F87171; font-size: 12px;")
        self._msg.setText(text)


class LoginDialog(QDialog):
    def __init__(self, db: "Database"):
        super().__init__()
        self.db = db
        self.current_user = None
        self.setWindowTitle("Login – IMS")
        self.setFixedSize(380, 360)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.MSWindowsFixedSizeDialogHint)
        self.setStyleSheet(AUTH_STYLE)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 36, 40, 30)
        layout.setSpacing(0)

        title = QLabel("⬛  IMS")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Inventory Management System")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(28)

        lbl_user = QLabel("USERNAME"); lbl_user.setObjectName("field")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        self.username_input.setFixedHeight(40)

        lbl_pass = QLabel("PASSWORD"); lbl_pass.setObjectName("field")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setFixedHeight(40)

        layout.addWidget(lbl_user)
        layout.addSpacing(4)
        layout.addWidget(self.username_input)
        layout.addSpacing(14)
        layout.addWidget(lbl_pass)
        layout.addSpacing(4)
        layout.addWidget(self.password_input)
        layout.addSpacing(8)

        self.error_label = QLabel("")
        self.error_label.setObjectName("error")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.error_label)
        layout.addSpacing(12)

        login_btn = QPushButton("Sign In")
        login_btn.setObjectName("primary_btn")
        login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        login_btn.clicked.connect(self._attempt_login)
        layout.addWidget(login_btn)

        self.password_input.returnPressed.connect(self._attempt_login)
        self.username_input.returnPressed.connect(self.password_input.setFocus)

    def _attempt_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            self.error_label.setText("Please enter username and password.")
            return
        user = self.db.check_credentials(username, password)
        if user:
            self.current_user = user
            self.accept()
        else:
            self.error_label.setText("Invalid username or password.")
            self.password_input.clear()
            self.password_input.setFocus()


class MainWindow(QMainWindow):
    logout_requested = pyqtSignal()

    def __init__(self, db: "Database", user: dict, allowed_menus=None):
        super().__init__()
        self.setWindowTitle("Inventory Management System")
        self.resize(1280, 780)
        self.setMinimumSize(960, 620)
        self.setStyleSheet(APP_STYLE)

        self.db = db
        self._user = user
        self._allowed_menus = allowed_menus   # None = all allowed (admin)
        role_name = (user.get("role_name") or user.get("role", "staff"))

        root = QWidget(); self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = Sidebar(self._navigate, self._logout, user, allowed_menus,
                               on_change_password=self._change_own_password)
        root_layout.addWidget(self.sidebar)

        # Content area with scroll
        content_scroll = QScrollArea()
        content_scroll.setWidgetResizable(True)
        content_scroll.setStyleSheet("QScrollArea { border: none; background: #F1F5F9; }")

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("QStackedWidget { background: #F1F5F9; }")
        content_scroll.setWidget(self.stack)
        root_layout.addWidget(content_scroll)

        # Instantiate all pages
        self._pages = {
            "Dashboard":       DashboardPage(self.db, role_name),
            "Products":        ProductsPage(self.db),
            "Stock":           StockPage(self.db),
            "Transactions":    TransactionsPage(self.db),
            "Sales":           SalesPage(self.db),
            "Sales Return":    SalesReturnPage(self.db),
            "Purchases":       PurchasesPage(self.db),
            "Purchase Return": PurchaseReturnPage(self.db),
            "Credit":          CreditPage(self.db),
            "Customers":       CustomersPage(self.db),
            "Suppliers":       SuppliersPage(self.db),
            "Cash":            CashPage(self.db),
            "Accounting":      AccountingPage(self.db),
            "Reports":         ReportsPage(self.db),
            "Categories":      CategoriesPage(self.db),
            "Users":           UsersPage(self.db),
            "Roles":           RolesPage(self.db),
        }
        for page in self._pages.values():
            self.stack.addWidget(page)

        # Navigate to first permitted page (Dashboard preferred)
        QTimer.singleShot(0, self._navigate_home)

    def _is_permitted(self, label):
        """Return True if the current user may access this page."""
        return self._allowed_menus is None or label in self._allowed_menus

    def _navigate_home(self):
        """Go to Dashboard if permitted, else the first permitted nav page."""
        if self._is_permitted("Dashboard"):
            self._navigate("Dashboard")
            return
        # Fall back to first permitted item in nav order
        for _, label, section in NAV_ITEMS:
            if label and self._is_permitted(label) and label in self._pages:
                self._navigate(label)
                return

    def _navigate(self, label):
        # Silently block navigation to pages the user cannot access
        if not self._is_permitted(label):
            return
        page = self._pages.get(label)
        if not page:
            return
        self.stack.setCurrentWidget(page)
        self.sidebar.set_active(label)
        # After switching, reload category filter in products if categories changed
        if label == "Products" and hasattr(page, "_reload_cats"):
            page._reload_cats()
        if hasattr(page, "refresh"):
            page.refresh()

    def _change_own_password(self):
        dlg = SelfChangePasswordDialog(self.db, self._user, self)
        dlg.exec()

    def _logout(self):
        self.logout_requested.emit()
        self.close()

    def closeEvent(self, event):
        # Only close db if not logging out (logout reopens login dialog)
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("IMS")
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))

    db = Database()
    window_ref = [None]

    def start_session():
        login = LoginDialog(db)
        if login.exec() != QDialog.DialogCode.Accepted:
            app.quit()
            return
        user = login.current_user
        # admin role bypasses permission filtering (always sees everything)
        if (user.get("role_name") or user.get("role", "")) == "admin":
            allowed_menus = None
        else:
            allowed_menus = db.get_user_permissions(user.get("role_id"))
        w = MainWindow(db, user, allowed_menus)
        w.logout_requested.connect(start_session)
        window_ref[0] = w
        w.show()

    start_session()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
