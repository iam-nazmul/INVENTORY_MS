from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QComboBox, QTabWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from styles import (btn, page_title, card_frame, search_box,
                    PRIMARY, SUCCESS, DANGER, WARNING, INFO, FIELD_STYLE, TABLE_STYLE,
                    TEXT_DARK, TEXT_MID, TEXT_LIGHT)


TYPE_COLOR = {
    "PURCHASE_IN": SUCCESS,
    "SALE_OUT":    DANGER,
    "OPENING":     INFO,
    "ADJUSTMENT":  WARNING,
    "MANUAL":      TEXT_MID,
}


class StockPage(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(24,24,24,24); root.setSpacing(16)
        root.addWidget(page_title("Stock Tracking"))

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background: transparent; }
            QTabBar::tab {
                background: #E5E7EB; color: #374151; border-radius: 6px;
                padding: 7px 20px; font-size: 13px; margin-right: 4px;
            }
            QTabBar::tab:selected { background: #4F46E5; color: white; font-weight: 600; }
        """)

        # Tab 1: Stock Summary
        summary_tab = QWidget()
        sl = QVBoxLayout(summary_tab); sl.setContentsMargins(0,12,0,0); sl.setSpacing(12)
        sr = QHBoxLayout()
        self.sum_search = search_box("  Search product…")
        self.sum_search.textChanged.connect(self._refresh_summary)
        sr.addWidget(self.sum_search); sr.addStretch()
        inc_btn = btn("＋  Add Stock",    SUCCESS); inc_btn.clicked.connect(self._increment_stock)
        dec_btn = btn("－  Remove Stock", DANGER);  dec_btn.clicked.connect(self._decrement_stock)
        sr.addWidget(inc_btn); sr.addWidget(dec_btn)
        sl.addLayout(sr)

        # Stats strip
        sf = QFrame(); sf.setStyleSheet("QFrame{background:#EEF2FF;border-radius:8px;}")
        sfl = QHBoxLayout(sf); sfl.setContentsMargins(16,8,16,8)
        self.lbl_stock_sum = QLabel()
        self.lbl_stock_sum.setStyleSheet(f"font-size:13px;font-weight:600;color:{PRIMARY};")
        sfl.addWidget(self.lbl_stock_sum); sfl.addStretch(); sl.addWidget(sf)

        sf2 = card_frame(); sfl2 = QVBoxLayout(sf2); sfl2.setContentsMargins(0,0,0,0)
        HEADERS = ["#","Product","SKU","Category","Unit","Stock","Min Stock","Cost","Sale Price","Value","Status"]
        self.tbl_summary = QTableWidget(); self.tbl_summary.setColumnCount(len(HEADERS))
        self.tbl_summary.setHorizontalHeaderLabels(HEADERS)
        self.tbl_summary.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_summary.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_summary.setAlternatingRowColors(True); self.tbl_summary.verticalHeader().setVisible(False)
        hh = self.tbl_summary.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(0,QHeaderView.ResizeMode.Fixed); self.tbl_summary.setColumnWidth(0,50)
        self.tbl_summary.setStyleSheet(TABLE_STYLE)
        sfl2.addWidget(self.tbl_summary); sl.addWidget(sf2)
        tabs.addTab(summary_tab, "Stock Summary")

        # Tab 2: Movements
        move_tab = QWidget()
        ml = QVBoxLayout(move_tab); ml.setContentsMargins(0,12,0,0); ml.setSpacing(12)
        mr = QHBoxLayout()
        self.mov_search = search_box("  Search product, note…")
        self.mov_search.textChanged.connect(self._refresh_movements)
        mr.addWidget(self.mov_search)
        self.mov_product = QComboBox(); self.mov_product.setFixedWidth(200)
        self.mov_product.setStyleSheet(FIELD_STYLE)
        self.mov_product.addItem("All Products", None)
        for p in self.db.get_all_products():
            self.mov_product.addItem(p["name"], p["id"])
        self.mov_product.currentIndexChanged.connect(self._refresh_movements)
        mr.addWidget(self.mov_product); mr.addStretch()
        ml.addLayout(mr)

        mf = card_frame(); mfl = QVBoxLayout(mf); mfl.setContentsMargins(0,0,0,0)
        MHEADERS = ["#","Product","SKU","Type","Quantity","Balance","Reference","Note","Date/Time"]
        self.tbl_movements = QTableWidget(); self.tbl_movements.setColumnCount(len(MHEADERS))
        self.tbl_movements.setHorizontalHeaderLabels(MHEADERS)
        self.tbl_movements.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_movements.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_movements.setAlternatingRowColors(True); self.tbl_movements.verticalHeader().setVisible(False)
        hh2 = self.tbl_movements.horizontalHeader()
        hh2.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hh2.setSectionResizeMode(0,QHeaderView.ResizeMode.Fixed); self.tbl_movements.setColumnWidth(0,50)
        self.tbl_movements.setStyleSheet(TABLE_STYLE)
        mfl.addWidget(self.tbl_movements); ml.addWidget(mf)
        tabs.addTab(move_tab, "Movement History")

        root.addWidget(tabs)

    def _increment_stock(self):
        self._adjust_stock("IN")

    def _decrement_stock(self):
        self._adjust_stock("OUT")

    def _adjust_stock(self, direction):
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        r = self.tbl_summary.currentRow()
        if r < 0:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Select", "Select a product row first.")
            return
        # Re-query to get live data (search filter may be active)
        search = self.sum_search.text().strip().lower()
        rows = self.db.get_stock_summary()
        if search:
            rows = [x for x in rows if search in x["name"].lower()
                    or search in (x["sku"] or "").lower()]
        if r >= len(rows):
            return
        row = rows[r]
        current = row["quantity"]
        if direction == "OUT" and current == 0:
            QMessageBox.warning(self, "No Stock",
                                f"'{row['name']}' has 0 units in stock.")
            return
        max_val = 999999 if direction == "IN" else current
        label = (f"Add stock to  '{row['name']}'\n"
                 f"Current stock: {current} {row['unit']}\n\n"
                 f"Quantity to add:") if direction == "IN" else (
                f"Remove stock from  '{row['name']}'\n"
                f"Current stock: {current} {row['unit']}\n\n"
                f"Quantity to remove:")
        qty, ok = QInputDialog.getInt(self, "Adjust Stock", label, 1, 1, max_val)
        if not ok:
            return
        try:
            self.db.add_transaction(row["id"], direction, qty, 0,
                                    f"Manual {'addition' if direction == 'IN' else 'removal'}")
            new_qty = current + qty if direction == "IN" else current - qty
            QMessageBox.information(
                self, "Stock Updated",
                f"'{row['name']}'\n"
                f"{'Added' if direction == 'IN' else 'Removed'}:  {qty} {row['unit']}\n"
                f"New stock:  {new_qty} {row['unit']}"
            )
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def refresh(self):
        self._refresh_summary()
        self._refresh_movements()

    def _refresh_summary(self):
        search = self.sum_search.text().strip().lower() if hasattr(self,"sum_search") else ""
        rows = self.db.get_stock_summary()
        if search:
            rows = [r for r in rows if search in r["name"].lower() or search in (r["sku"] or "").lower()]

        total_val = sum(r["stock_value"] for r in rows)
        in_stock  = sum(1 for r in rows if r["stock_status"] == "In Stock")
        low       = sum(1 for r in rows if r["stock_status"] == "Low Stock")
        out       = sum(1 for r in rows if r["stock_status"] == "Out of Stock")
        self.lbl_stock_sum.setText(
            f"Products: {len(rows)}  |  In Stock: {in_stock}  |  Low: {low}  |  Out: {out}  |  Total Value: ${total_val:,.2f}"
        )

        STATUS_COLOR = {"In Stock": SUCCESS, "Low Stock": WARNING, "Out of Stock": DANGER}
        self.tbl_summary.setRowCount(len(rows))
        for i, r in enumerate(rows):
            vals = [str(r["id"]), r["name"], r["sku"] or "—", r["category"] or "—",
                    r["unit"], str(r["quantity"]), str(r["min_stock"]),
                    f"${r['cost_price']:.2f}", f"${r['sale_price']:.2f}",
                    f"${r['stock_value']:.2f}", r["stock_status"]]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if c == 10:
                    item.setForeground(QColor(STATUS_COLOR.get(v, TEXT_MID)))
                    item.setFont(QFont("", -1, QFont.Weight.Bold))
                elif c == 5:
                    if r["stock_status"] != "In Stock":
                        item.setForeground(QColor(STATUS_COLOR.get(r["stock_status"], TEXT_MID)))
                self.tbl_summary.setItem(i, c, item)

    def _refresh_movements(self):
        search  = self.mov_search.text().strip() if hasattr(self,"mov_search") else ""
        pid     = self.mov_product.currentData() if hasattr(self,"mov_product") else None
        rows    = self.db.get_stock_movements(pid, search)
        self.tbl_movements.setRowCount(len(rows))
        for i, r in enumerate(rows):
            color = TYPE_COLOR.get(r["type"], TEXT_MID)
            vals = [str(r["id"]), r["product"], r["sku"] or "—",
                    r["type"], str(r["quantity"]), str(r["balance"]),
                    r["reference_type"] or "—", r["note"] or "—", r["created_at"][:16]]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if c == 3:
                    item.setForeground(QColor(color))
                    item.setFont(QFont("", -1, QFont.Weight.Bold))
                self.tbl_movements.setItem(i, c, item)
