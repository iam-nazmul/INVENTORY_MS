from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from styles import (PRIMARY, SUCCESS, DANGER, WARNING, INFO, PURPLE,
                    ORANGE, TEXT_DARK, TEXT_MID, TEXT_LIGHT, TABLE_STYLE, BG_CARD)


class StatCard(QFrame):
    def __init__(self, title, value="—", subtitle="", color=PRIMARY):
        super().__init__()
        self.setObjectName("StatCard")
        self.setStyleSheet(f"""
            QFrame#StatCard {{
                background: {BG_CARD};
                border-radius: 12px;
                border-left: 5px solid {color};
            }}
        """)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(100)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(3)

        self._title = QLabel(title)
        self._title.setStyleSheet(f"color:{TEXT_LIGHT};font-size:11px;font-weight:600;background:transparent;border:none;")
        layout.addWidget(self._title)

        self._value = QLabel(str(value))
        self._value.setStyleSheet(f"color:{color};font-size:26px;font-weight:700;background:transparent;border:none;")
        layout.addWidget(self._value)

        if subtitle:
            self._sub = QLabel(subtitle)
            self._sub.setStyleSheet(f"color:{TEXT_LIGHT};font-size:10px;background:transparent;border:none;")
            layout.addWidget(self._sub)

    def set_value(self, v):
        self._value.setText(str(v))


class DashboardPage(QWidget):
    def __init__(self, db, role_name="staff"):
        super().__init__()
        self.db = db
        self._is_admin = (role_name == "admin")
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(18)

        root.addWidget(QLabel("Dashboard", styleSheet=f"font-size:22px;font-weight:700;color:{TEXT_DARK};"))

        # Row 1: financial cards (admin only)
        self._r1_frame = QFrame()
        r1_outer = QVBoxLayout(self._r1_frame)
        r1_outer.setContentsMargins(0, 0, 0, 0)
        r1_outer.setSpacing(0)
        r1 = QGridLayout(); r1.setSpacing(14)
        self.c_cash      = StatCard("Cash Balance",      color=SUCCESS)
        self.c_sales     = StatCard("Total Sales",       color=PRIMARY)
        self.c_today     = StatCard("Today's Sales",     color=INFO)
        self.c_purchases = StatCard("Total Purchases",   color=WARNING)
        self.c_recv      = StatCard("Receivable (Due)",  color=DANGER)
        self.c_pay       = StatCard("Payable (Due)",     color=ORANGE)
        self.c_unpaid    = StatCard("Unpaid Invoices",   color=DANGER)
        self.c_profit    = StatCard("Profit / Loss",     color=SUCCESS)
        for i, c in enumerate([self.c_cash, self.c_sales, self.c_today, self.c_purchases,
                                self.c_recv, self.c_pay, self.c_unpaid, self.c_profit]):
            r1.addWidget(c, i//4, i%4)
        r1_outer.addLayout(r1)
        self._r1_frame.setVisible(self._is_admin)
        root.addWidget(self._r1_frame)

        # Row 2: stock cards
        r2 = QHBoxLayout(); r2.setSpacing(14)
        self.c_prods     = StatCard("Products",     color=PRIMARY)
        self.c_stock     = StatCard("Total Units",  color=SUCCESS)
        self.c_value     = StatCard("Stock Value",  color=WARNING)
        self.c_low       = StatCard("Low Stock",    color=DANGER)
        self.c_customers = StatCard("Customers",    color=INFO)
        self.c_suppliers = StatCard("Suppliers",    color=PURPLE)
        for c in [self.c_prods, self.c_stock, self.c_value, self.c_low,
                  self.c_customers, self.c_suppliers]:
            r2.addWidget(c)
        root.addLayout(r2)

        # Bottom tables
        bot = QHBoxLayout(); bot.setSpacing(16)
        bot.addWidget(self._make_section("Low Stock Alerts",
            ["Product","SKU","Stock","Min","Unit","Category"], "tbl_low"), 1)
        bot.addWidget(self._make_section("Recent Sales",
            ["Invoice","Customer","Total","Paid","Due","Status","Date"], "tbl_sales"), 1)
        root.addLayout(bot)

    def _make_section(self, title, headers, attr):
        f = QFrame()
        f.setStyleSheet(f"QFrame{{background:{BG_CARD};border-radius:12px;}}")
        lay = QVBoxLayout(f); lay.setContentsMargins(16,14,16,14); lay.setSpacing(8)
        lay.addWidget(QLabel(title, styleSheet=f"font-size:14px;font-weight:600;color:{TEXT_MID};background:transparent;border:none;"))
        t = QTableWidget()
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t.setAlternatingRowColors(True)
        t.verticalHeader().setVisible(False)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        t.setStyleSheet(TABLE_STYLE)
        setattr(self, attr, t)
        lay.addWidget(t)
        return f

    def refresh(self):
        s = self.db.get_dashboard_stats()
        self.c_cash.set_value(f"${s['cash_balance']:,.2f}")
        self.c_sales.set_value(f"${s['total_sales']:,.2f}")
        self.c_today.set_value(f"${s['today_sales']:,.2f}")
        self.c_purchases.set_value(f"${s['total_purchases']:,.2f}")
        self.c_recv.set_value(f"${s['receivable']:,.2f}")
        self.c_pay.set_value(f"${s['payable']:,.2f}")
        self.c_unpaid.set_value(str(s['unpaid_invoices']))
        profit = s['gross_profit']
        profit_color = SUCCESS if profit >= 0 else DANGER
        self.c_profit._value.setStyleSheet(
            f"color:{profit_color};font-size:26px;font-weight:700;background:transparent;border:none;"
        )
        self.c_profit.set_value(f"${profit:,.2f}")
        self.c_prods.set_value(s['total_products'])
        self.c_stock.set_value(f"{s['total_stock']:,}")
        self.c_value.set_value(f"${s['stock_value']:,.2f}")
        self.c_low.set_value(s['low_stock'])
        self.c_customers.set_value(s['total_customers'])
        self.c_suppliers.set_value(s['total_suppliers'])

        low = self.db.get_low_stock_products()
        self.tbl_low.setRowCount(len(low))
        for r, row in enumerate(low):
            vals = [row["name"], row["sku"] or "—", str(row["quantity"]),
                    str(row["min_stock"]), row["unit"], row["category"] or "—"]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if c == 2:
                    item.setForeground(QColor("#DC2626"))
                    item.setFont(QFont("", -1, QFont.Weight.Bold))
                self.tbl_low.setItem(r, c, item)

        sales = self.db.get_recent_sales()
        self.tbl_sales.setRowCount(len(sales))
        STATUS_COLOR = {"paid":"#059669","partial":"#D97706","unpaid":"#DC2626"}
        for r, row in enumerate(sales):
            vals = [row["invoice_no"], row["customer"], f"${row['total']:.2f}",
                    f"${row['paid_amount']:.2f}", f"${row['due_amount']:.2f}",
                    row["status"], row["sale_date"]]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if c == 5:
                    item.setForeground(QColor(STATUS_COLOR.get(v, "#374151")))
                    item.setFont(QFont("", -1, QFont.Weight.Bold))
                self.tbl_sales.setItem(r, c, item)
