from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QFormLayout, QMessageBox, QFrame, QComboBox,
    QSpinBox, QTextEdit, QLineEdit, QDateEdit, QGridLayout, QAbstractItemView
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QFont
from styles import (btn, page_title, card_frame, search_box,
                    PRIMARY, SUCCESS, DANGER, WARNING, INFO, ORANGE,
                    FIELD_STYLE, TABLE_STYLE, TEXT_DARK, TEXT_MID, TEXT_LIGHT, BORDER)


# ── Return Items Table (inside dialog) ────────────────────────────────────────

class ReturnItemsTable(QTableWidget):
    """Editable table showing sale items with a 'Return Qty' spinbox column."""

    HEADERS = ["Product", "Unit", "Sold", "Already Returned", "Max Returnable", "Return Qty", "Unit Price", "Return Total"]

    def __init__(self, items):
        super().__init__()
        self._items = items
        self._spinboxes = []
        self.setColumnCount(len(self.HEADERS))
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        hh = self.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(5, 110)
        self.setStyleSheet(TABLE_STYLE)
        self.setMinimumHeight(200)
        self._populate(items)

    def _populate(self, items):
        self.setRowCount(len(items))
        self._spinboxes = []
        for r, item in enumerate(items):
            max_ret = item["sold_qty"] - item["returned_qty"]

            for c, v in enumerate([
                item["product_name"],
                item["unit"],
                str(item["sold_qty"]),
                str(item["returned_qty"]),
                str(max_ret),
            ]):
                cell = QTableWidgetItem(v)
                if c == 4:
                    cell.setForeground(QColor(DANGER if max_ret == 0 else SUCCESS))
                    cell.setFont(QFont("", -1, QFont.Weight.Bold))
                self.setItem(r, c, cell)

            # Qty spinbox
            sp = QSpinBox()
            sp.setRange(0, max(0, max_ret))
            sp.setValue(0)
            sp.setEnabled(max_ret > 0)
            sp.setStyleSheet(f"""
                QSpinBox {{
                    border: 1.5px solid {BORDER}; border-radius: 4px;
                    padding: 3px 6px; font-size: 13px;
                    background: {'#FAFAFA' if max_ret > 0 else '#F3F4F6'};
                }}
                QSpinBox:focus {{ border-color: {PRIMARY}; }}
            """)
            sp.valueChanged.connect(lambda _, row=r: self._update_total(row))
            self.setCellWidget(r, 5, sp)
            self._spinboxes.append(sp)

            # Unit price
            self.setItem(r, 6, QTableWidgetItem(f"${item['unit_price']:.2f}"))

            # Return total
            self.setItem(r, 7, QTableWidgetItem("$0.00"))

    def _update_total(self, row):
        item = self._items[row]
        qty = self._spinboxes[row].value()
        total = qty * item["unit_price"]
        t_item = QTableWidgetItem(f"${total:.2f}")
        t_item.setForeground(QColor(DANGER if total > 0 else TEXT_MID))
        t_item.setFont(QFont("", -1, QFont.Weight.Bold) if total > 0 else QFont())
        self.setItem(row, 7, t_item)

    def get_return_items(self):
        result = []
        for r, item in enumerate(self._items):
            qty = self._spinboxes[r].value()
            if qty > 0:
                result.append(dict(
                    product_id=item["product_id"],
                    qty=qty,
                    unit_price=item["unit_price"],
                    total=qty * item["unit_price"],
                ))
        return result

    def get_return_total(self):
        return sum(
            self._spinboxes[r].value() * self._items[r]["unit_price"]
            for r in range(len(self._items))
        )


# ── Sales Return Dialog ────────────────────────────────────────────────────────

class SalesReturnDialog(QDialog):
    def __init__(self, parent, db, sale=None):
        super().__init__(parent)
        self.db = db
        self._sale = sale
        self._items_table = None
        self.setWindowTitle("New Sales Return")
        self.setMinimumSize(820, 580)
        self.setModal(True)
        self._build()
        if sale:
            self._load_invoice(sale)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # Title
        root.addWidget(QLabel("Sales Return",
            styleSheet=f"font-size:17px;font-weight:700;color:{DANGER};"))

        # Invoice selector
        inv_row = QHBoxLayout(); inv_row.setSpacing(10)
        inv_row.addWidget(QLabel("Invoice:", styleSheet=f"font-size:13px;font-weight:600;color:{TEXT_MID};"))
        self.invoice_combo = QComboBox()
        self.invoice_combo.setMinimumWidth(260)
        self.invoice_combo.setStyleSheet(FIELD_STYLE)
        sales = self.db.get_all_sales()
        for s in sales:
            self.invoice_combo.addItem(
                f"{s['invoice_no']}  –  {s['customer']}  (${s['total']:.2f})", s["id"]
            )
        self.invoice_combo.currentIndexChanged.connect(self._on_invoice_changed)
        inv_row.addWidget(self.invoice_combo)

        # Invoice summary labels
        self.lbl_inv_info = QLabel()
        self.lbl_inv_info.setStyleSheet(f"font-size:12px;color:{TEXT_LIGHT};")
        inv_row.addWidget(self.lbl_inv_info)
        inv_row.addStretch()
        root.addLayout(inv_row)

        # Items header
        root.addWidget(QLabel("Select Items to Return",
            styleSheet=f"font-size:13px;font-weight:600;color:{TEXT_MID};"))

        # Items container (replaced when invoice changes)
        self._items_frame = QFrame()
        self._items_frame.setStyleSheet("QFrame{background:transparent;}")
        self._items_frame_layout = QVBoxLayout(self._items_frame)
        self._items_frame_layout.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._items_frame)

        # Return details row
        det = QGridLayout(); det.setSpacing(10)
        self.return_date = QDateEdit(QDate.currentDate())
        self.return_date.setStyleSheet(FIELD_STYLE); self.return_date.setCalendarPopup(True)
        self.refund_type = QComboBox()
        self.refund_type.setStyleSheet(FIELD_STYLE)
        self.refund_type.addItem("Cash Refund (pay back to customer)", "cash")
        self.refund_type.addItem("Adjust Balance (reduce customer due)", "adjust")
        self.reason = QLineEdit(); self.reason.setPlaceholderText("Return reason")
        self.reason.setStyleSheet(FIELD_STYLE)
        self.note = QTextEdit(); self.note.setPlaceholderText("Additional notes (optional)")
        self.note.setMaximumHeight(55); self.note.setStyleSheet(FIELD_STYLE)

        det.addWidget(QLabel("Return Date:"),  0, 0); det.addWidget(self.return_date,  0, 1)
        det.addWidget(QLabel("Refund Type:"),  0, 2); det.addWidget(self.refund_type,  0, 3)
        det.addWidget(QLabel("Reason:"),       1, 0); det.addWidget(self.reason,       1, 1, 1, 3)
        det.addWidget(QLabel("Note:"),         2, 0); det.addWidget(self.note,         2, 1, 1, 3)
        root.addLayout(det)

        # Total row
        total_row = QHBoxLayout()
        total_row.addStretch()
        self.lbl_total = QLabel("Return Total: $0.00")
        self.lbl_total.setStyleSheet(f"font-size:16px;font-weight:700;color:{DANGER};")
        total_row.addWidget(self.lbl_total)
        root.addLayout(total_row)

        # Buttons
        btns = QHBoxLayout(); btns.setSpacing(8)
        c = btn("Cancel", "#E5E7EB", "#374151"); c.clicked.connect(self.reject)
        s = btn("Process Return", DANGER); s.clicked.connect(self._validate)
        btns.addStretch(); btns.addWidget(c); btns.addWidget(s)
        root.addLayout(btns)

        # Load first invoice
        if self.invoice_combo.count() > 0:
            self._on_invoice_changed(0)

    def _on_invoice_changed(self, _):
        sale_id = self.invoice_combo.currentData()
        if not sale_id:
            return
        sale_rows = self.db.get_all_sales()
        self._sale = next((s for s in sale_rows if s["id"] == sale_id), None)
        if self._sale:
            self.lbl_inv_info.setText(
                f"Date: {self._sale['sale_date']}  |  "
                f"Total: ${self._sale['total']:.2f}  |  "
                f"Status: {self._sale['status'].upper()}"
            )
        self._load_invoice_items(sale_id)

    def _load_invoice(self, sale):
        for i in range(self.invoice_combo.count()):
            if self.invoice_combo.itemData(i) == sale["id"]:
                self.invoice_combo.setCurrentIndex(i)
                break

    def _load_invoice_items(self, sale_id):
        # Clear previous table
        while self._items_frame_layout.count():
            child = self._items_frame_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        items = self.db.get_sale_items_for_return(sale_id)
        self._items_table = ReturnItemsTable(items)
        # Connect spinbox changes to update total label
        for sp in self._items_table._spinboxes:
            sp.valueChanged.connect(self._update_total_label)
        self._items_frame_layout.addWidget(self._items_table)

    def _update_total_label(self):
        if self._items_table:
            total = self._items_table.get_return_total()
            self.lbl_total.setText(f"Return Total: ${total:.2f}")

    def _validate(self):
        if not self._items_table:
            QMessageBox.warning(self, "Error", "No invoice loaded."); return
        items = self._items_table.get_return_items()
        if not items:
            QMessageBox.warning(self, "Items", "Select at least one item to return."); return
        if not self.reason.text().strip():
            QMessageBox.warning(self, "Reason", "Please enter a return reason."); return
        self.accept()

    def get_data(self):
        return dict(
            sale_id     = self.invoice_combo.currentData(),
            items       = self._items_table.get_return_items(),
            refund_type = self.refund_type.currentData(),
            reason      = self.reason.text().strip(),
            note        = self.note.toPlainText().strip(),
            return_date = self.return_date.date().toString("yyyy-MM-dd"),
        )


# ── Return Detail Dialog ───────────────────────────────────────────────────────

class SaleReturnDetailDialog(QDialog):
    def __init__(self, parent, db, ret):
        super().__init__(parent)
        self.db = db; self.ret = ret
        self.setWindowTitle(f"Sales Return: {ret['return_no']}")
        self.setMinimumSize(580, 400); self.setModal(True)
        layout = QVBoxLayout(self); layout.setContentsMargins(20, 16, 20, 16); layout.setSpacing(10)

        # Header
        hr = QHBoxLayout()
        hr.addWidget(QLabel(ret["return_no"],
            styleSheet=f"font-size:16px;font-weight:700;color:{DANGER};"))
        hr.addSpacing(20)
        hr.addWidget(QLabel(f"Original Invoice: {ret['invoice_no']}",
            styleSheet=f"font-size:13px;color:{PRIMARY};font-weight:600;"))
        hr.addStretch(); layout.addLayout(hr)

        info = QHBoxLayout()
        for lbl, val in [("Customer:", ret["customer"]), ("Date:", ret["return_date"]),
                          ("Refund:", ret["refund_type"].title())]:
            info.addWidget(QLabel(f"<b>{lbl}</b> {val}")); info.addSpacing(20)
        info.addStretch(); layout.addLayout(info)

        if ret["reason"]:
            layout.addWidget(QLabel(f"Reason: {ret['reason']}",
                styleSheet=f"color:{TEXT_LIGHT};font-size:12px;"))

        # Items
        items = db.get_sale_return_items(ret["id"])
        t = QTableWidget(len(items), 4)
        t.setHorizontalHeaderLabels(["Product", "Unit", "Qty Returned", "Total"])
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.setAlternatingRowColors(True); t.verticalHeader().setVisible(False)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        t.setStyleSheet(TABLE_STYLE)
        for r, item in enumerate(items):
            for c, v in enumerate([item["product_name"], item["unit"],
                                    str(item["quantity"]), f"${item['total']:.2f}"]):
                ti = QTableWidgetItem(v)
                if c == 3: ti.setForeground(QColor(DANGER))
                t.setItem(r, c, ti)
        layout.addWidget(t)

        # Total
        tf = QFrame(); tf.setStyleSheet("background:#FEF2F2;border-radius:8px;")
        tl = QHBoxLayout(tf); tl.setContentsMargins(16, 10, 16, 10)
        tl.addWidget(QLabel("Total Returned:",
            styleSheet="font-weight:600;font-size:13px;"))
        tl.addStretch()
        tl.addWidget(QLabel(f"${ret['total']:.2f}",
            styleSheet=f"font-size:18px;font-weight:700;color:{DANGER};"))
        layout.addWidget(tf)

        btns = QHBoxLayout(); btns.addStretch()
        p = btn("Print Receipt", DANGER); p.clicked.connect(self._print_receipt)
        btns.addWidget(p)
        c = btn("Close", "#E5E7EB", "#374151"); c.clicked.connect(self.accept)
        btns.addWidget(c); layout.addLayout(btns)

    def _print_receipt(self):
        from invoices.templates import build_pos_sales_return_receipt
        from invoices.printer import PrintInvoiceDialog
        items = [dict(i) for i in self.db.get_sale_return_items(self.ret["id"])]
        company = self.db.get_company_info()
        pos = build_pos_sales_return_receipt(dict(self.ret), items, company)
        PrintInvoiceDialog(self, pos, pos, self.ret["return_no"], "Print Return Receipt").exec()


# ── Sales Return Page ──────────────────────────────────────────────────────────

class SalesReturnPage(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db; self._rows = []
        self._build(); self.refresh()

    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(24, 24, 24, 24); root.setSpacing(16)

        # Header
        hr = QHBoxLayout()
        hr.addWidget(page_title("Sales Returns"))
        hr.addStretch()
        self.search = search_box("  Search return no, invoice…")
        self.search.textChanged.connect(self.refresh)
        hr.addWidget(self.search)

        self.df = QDateEdit(QDate.currentDate().addMonths(-1))
        self.dt = QDateEdit(QDate.currentDate())
        for d in [self.df, self.dt]:
            d.setStyleSheet(FIELD_STYLE); d.setCalendarPopup(True); d.setFixedWidth(115)
            d.dateChanged.connect(self.refresh)
        hr.addWidget(QLabel("From:")); hr.addWidget(self.df)
        hr.addWidget(QLabel("To:")); hr.addWidget(self.dt)

        new_btn = btn("+ New Return", DANGER); new_btn.clicked.connect(self.new_return)
        hr.addWidget(new_btn)
        root.addLayout(hr)

        # Summary strip
        sf = QFrame(); sf.setStyleSheet("QFrame{background:#FEE2E2;border-radius:8px;}")
        sl = QHBoxLayout(sf); sl.setContentsMargins(16, 8, 16, 8)
        self.lbl_sum = QLabel()
        self.lbl_sum.setStyleSheet(f"font-size:13px;font-weight:600;color:{DANGER};")
        sl.addWidget(self.lbl_sum); sl.addStretch()
        root.addWidget(sf)

        # Table
        f = card_frame(); fl = QVBoxLayout(f); fl.setContentsMargins(0, 0, 0, 0)
        HEADERS = ["#", "Return No", "Invoice No", "Customer", "Date",
                   "Amount", "Refund Type", "Reason"]
        self.table = QTableWidget(); self.table.setColumnCount(len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True); self.table.verticalHeader().setVisible(False)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(0, 50)
        self.table.setStyleSheet(TABLE_STYLE)
        self.table.doubleClicked.connect(self.view_return)
        fl.addWidget(self.table)
        root.addWidget(f)

        ar = QHBoxLayout(); ar.addStretch()
        view_btn = btn("View Detail", PRIMARY); view_btn.clicked.connect(self.view_return)
        ar.addWidget(view_btn)
        root.addLayout(ar)

    def refresh(self):
        df = self.df.date().toString("yyyy-MM-dd")
        dt = self.dt.date().toString("yyyy-MM-dd")
        rows = self.db.get_all_sales_returns(
            self.search.text().strip(), df, dt
        )
        self._rows = rows
        self.table.setRowCount(len(rows))

        total_returned = sum(r["total"] for r in rows)
        self.lbl_sum.setText(
            f"Returns: {len(rows)}  |  Total Returned: ${total_returned:,.2f}"
        )

        for i, r in enumerate(rows):
            vals = [str(r["id"]), r["return_no"], r["invoice_no"], r["customer"],
                    r["return_date"], f"${r['total']:.2f}",
                    r["refund_type"].title(), r["reason"] or "—"]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if c == 5:
                    item.setForeground(QColor(DANGER))
                    item.setFont(QFont("", -1, QFont.Weight.Bold))
                if c == 6:
                    color = SUCCESS if r["refund_type"] == "cash" else WARNING
                    item.setForeground(QColor(color))
                self.table.setItem(i, c, item)

    def _selected(self):
        r = self.table.currentRow()
        if r < 0:
            QMessageBox.information(self, "Select", "Select a return record first.")
            return None
        return self._rows[r]

    def new_return(self):
        dlg = SalesReturnDialog(self, self.db)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            try:
                rn = self.db.create_sale_return(**d)
                QMessageBox.information(self, "Success",
                    f"Sales return {rn} processed successfully.")
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def view_return(self):
        row = self._selected()
        if row:
            SaleReturnDetailDialog(self, self.db, row).exec()
