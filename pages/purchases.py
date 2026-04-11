from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QFormLayout, QMessageBox, QFrame, QComboBox,
    QDoubleSpinBox, QSpinBox, QTextEdit, QLineEdit, QScrollArea,
    QPushButton, QGridLayout, QDateEdit
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QFont
from styles import (btn, page_title, card_frame, search_box,
                    PRIMARY, SUCCESS, DANGER, WARNING, FIELD_STYLE, TABLE_STYLE,
                    TEXT_DARK, TEXT_MID, TEXT_LIGHT, BORDER)


class PurchaseItemRow(QFrame):
    def __init__(self, products, on_remove, on_change):
        super().__init__()
        self._products = products
        self._on_change = on_change
        self.setStyleSheet(f"QFrame{{background:#F9FAFB;border-radius:6px;border:1px solid {BORDER};}}")
        layout = QHBoxLayout(self); layout.setContentsMargins(8,6,8,6); layout.setSpacing(8)

        self.product = QComboBox(); self.product.setMinimumWidth(200)
        self.product.setStyleSheet(FIELD_STYLE)
        for p in products:
            self.product.addItem(f"{p['name']} [{p['sku'] or '—'}]", p["id"])
        self.product.currentIndexChanged.connect(self._on_product_change)

        self.qty = QSpinBox(); self.qty.setRange(1,999999); self.qty.setFixedWidth(80)
        self.qty.setStyleSheet(FIELD_STYLE); self.qty.valueChanged.connect(self._recalc)

        self.price = QDoubleSpinBox(); self.price.setRange(0,9999999); self.price.setDecimals(2)
        self.price.setPrefix("$"); self.price.setFixedWidth(110)
        self.price.setStyleSheet(FIELD_STYLE); self.price.valueChanged.connect(self._recalc)

        self.total_lbl = QLabel("$0.00"); self.total_lbl.setFixedWidth(90)
        self.total_lbl.setStyleSheet(f"font-size:14px;font-weight:700;color:{PRIMARY};")
        self.total_lbl.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter)

        rm = QPushButton("✕"); rm.setFixedSize(28,28)
        rm.setStyleSheet(f"background:{DANGER};color:white;border:none;border-radius:14px;font-weight:700;")
        rm.setCursor(Qt.CursorShape.PointingHandCursor); rm.clicked.connect(on_remove)

        for w, lbl in [(self.product,"Product"),(self.qty,"Qty"),(self.price,"Cost Price"),(self.total_lbl,"Total")]:
            col = QVBoxLayout(); col.setSpacing(2)
            col.addWidget(QLabel(lbl, styleSheet=f"font-size:10px;color:{TEXT_LIGHT};"))
            col.addWidget(w); layout.addLayout(col)
        layout.addWidget(rm, alignment=Qt.AlignmentFlag.AlignBottom)

        self._on_product_change(0)

    def _on_product_change(self, _):
        pid = self.product.currentData()
        for p in self._products:
            if p["id"] == pid:
                self.price.setValue(p["cost_price"]); break
        self._recalc()

    def _recalc(self):
        self._total = self.qty.value() * self.price.value()
        self.total_lbl.setText(f"${self._total:.2f}"); self._on_change()

    def get_item(self):
        return dict(product_id=self.product.currentData(),
                    qty=self.qty.value(), unit_price=self.price.value(), total=self._total)


class PurchaseDialog(QDialog):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self._products = list(db.get_all_products())
        self._item_rows = []
        self.setWindowTitle("New Purchase Order")
        self.setMinimumSize(760, 580); self.setModal(True)
        self._build()

    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(20,16,20,16); root.setSpacing(12)
        root.addWidget(QLabel("New Purchase Order", styleSheet=f"font-size:17px;font-weight:700;color:{TEXT_DARK};"))

        hf = QGridLayout(); hf.setSpacing(10)
        self.supplier = QComboBox(); self.supplier.setStyleSheet(FIELD_STYLE)
        self.supplier.addItem("— Select Supplier —", None)
        for s in self.db.get_all_suppliers(): self.supplier.addItem(s["name"], s["id"])
        self.purchase_date = QDateEdit(QDate.currentDate())
        self.purchase_date.setStyleSheet(FIELD_STYLE); self.purchase_date.setCalendarPopup(True)
        self.tax_rate = QDoubleSpinBox(); self.tax_rate.setRange(0,50); self.tax_rate.setSuffix("%")
        self.tax_rate.setStyleSheet(FIELD_STYLE); self.tax_rate.valueChanged.connect(self._recalc)
        self.overall_disc = QDoubleSpinBox(); self.overall_disc.setRange(0,9999999)
        self.overall_disc.setDecimals(2); self.overall_disc.setPrefix("$")
        self.overall_disc.setStyleSheet(FIELD_STYLE); self.overall_disc.valueChanged.connect(self._recalc)
        hf.addWidget(QLabel("Supplier:"),    0,0); hf.addWidget(self.supplier,      0,1)
        hf.addWidget(QLabel("Date:"),        0,2); hf.addWidget(self.purchase_date, 0,3)
        hf.addWidget(QLabel("Discount($):"), 1,0); hf.addWidget(self.overall_disc,  1,1)
        hf.addWidget(QLabel("Tax Rate:"),    1,2); hf.addWidget(self.tax_rate,      1,3)
        root.addLayout(hf)

        root.addWidget(QLabel("Items", styleSheet=f"font-size:13px;font-weight:600;color:{TEXT_MID};"))
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(180); scroll.setMaximumHeight(260)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        self._items_container = QWidget()
        self._items_layout = QVBoxLayout(self._items_container)
        self._items_layout.setContentsMargins(0,0,0,0); self._items_layout.setSpacing(6)
        self._items_layout.addStretch()
        scroll.setWidget(self._items_container); root.addWidget(scroll)

        ar = btn("+ Add Item", SUCCESS); ar.clicked.connect(self._add_row)
        root.addWidget(ar, alignment=Qt.AlignmentFlag.AlignLeft)

        tf = QFrame(); tf.setStyleSheet("background:#F9FAFB;border-radius:8px;")
        tl = QGridLayout(tf); tl.setContentsMargins(16,12,16,12); tl.setSpacing(6)
        self.lbl_subtotal = QLabel("$0.00"); self.lbl_disc = QLabel("$0.00")
        self.lbl_tax = QLabel("$0.00"); self.lbl_total = QLabel("$0.00"); self.lbl_due = QLabel("$0.00")
        self.lbl_total.setStyleSheet(f"font-size:18px;font-weight:700;color:{PRIMARY};")
        self.lbl_due.setStyleSheet(f"font-size:14px;font-weight:700;color:{DANGER};")
        tl.addWidget(QLabel("Subtotal:"), 0,0); tl.addWidget(self.lbl_subtotal, 0,1)
        tl.addWidget(QLabel("Discount:"), 1,0); tl.addWidget(self.lbl_disc,     1,1)
        tl.addWidget(QLabel("Tax:"),      2,0); tl.addWidget(self.lbl_tax,      2,1)
        tl.addWidget(QLabel("TOTAL:"),    3,0); tl.addWidget(self.lbl_total,    3,1)
        self.payment_type = QComboBox(); self.payment_type.setStyleSheet(FIELD_STYLE)
        self.payment_type.addItems(["cash","credit","partial"])
        self.payment_type.currentTextChanged.connect(self._recalc)
        self.paid_input = QDoubleSpinBox(); self.paid_input.setRange(0,9999999)
        self.paid_input.setDecimals(2); self.paid_input.setPrefix("$")
        self.paid_input.setStyleSheet(FIELD_STYLE); self.paid_input.valueChanged.connect(self._recalc)
        tl.addWidget(QLabel("Payment:"), 0,2); tl.addWidget(self.payment_type, 0,3)
        tl.addWidget(QLabel("Paid:"),    1,2); tl.addWidget(self.paid_input,   1,3)
        tl.addWidget(QLabel("Due:"),     2,2); tl.addWidget(self.lbl_due,      2,3)
        root.addWidget(tf)

        self.note = QTextEdit(); self.note.setPlaceholderText("Note (optional)")
        self.note.setMaximumHeight(50); self.note.setStyleSheet(FIELD_STYLE); root.addWidget(self.note)

        btns = QHBoxLayout(); btns.setSpacing(8)
        c = btn("Cancel","#E5E7EB","#374151"); c.clicked.connect(self.reject)
        s = btn("Save Order", SUCCESS); s.clicked.connect(self._validate)
        btns.addStretch(); btns.addWidget(c); btns.addWidget(s); root.addLayout(btns)
        self._add_row()

    def _add_row(self):
        if not self._products: QMessageBox.warning(self,"No Products","Add products first."); return
        row = PurchaseItemRow(self._products, lambda: self._remove_row(row), self._recalc)
        self._item_rows.append(row)
        self._items_layout.insertWidget(self._items_layout.count()-1, row); self._recalc()

    def _remove_row(self, row):
        if len(self._item_rows) <= 1: return
        self._item_rows.remove(row); row.setParent(None); row.deleteLater(); self._recalc()

    def _recalc(self):
        subtotal = sum(r.get_item()["total"] for r in self._item_rows)
        disc = self.overall_disc.value()
        taxable = subtotal - disc
        tax = taxable * self.tax_rate.value() / 100
        total = taxable + tax
        ptype = self.payment_type.currentText()
        if ptype == "cash":
            paid = total; self.paid_input.setValue(total); self.paid_input.setEnabled(False)
        elif ptype == "credit":
            paid = 0; self.paid_input.setValue(0); self.paid_input.setEnabled(False)
        else:
            self.paid_input.setEnabled(True); paid = min(self.paid_input.value(), total)
        due = total - paid
        self.lbl_subtotal.setText(f"${subtotal:.2f}"); self.lbl_disc.setText(f"${disc:.2f}")
        self.lbl_tax.setText(f"${tax:.2f}"); self.lbl_total.setText(f"${total:.2f}")
        self.lbl_due.setText(f"${due:.2f}")
        self._total = total; self._paid = paid; self._due = due

    def _validate(self):
        if not self._item_rows: QMessageBox.warning(self,"Items","Add at least one item."); return
        self.accept()

    def get_data(self):
        return dict(
            supplier_id   = self.supplier.currentData(),
            purchase_date = self.purchase_date.date().toString("yyyy-MM-dd"),
            items         = [r.get_item() for r in self._item_rows],
            discount      = self.overall_disc.value(),
            tax_rate      = self.tax_rate.value(),
            paid_amount   = self._paid,
            payment_type  = self.payment_type.currentText(),
            note          = self.note.toPlainText().strip(),
        )


class PurchaseDetailDialog(QDialog):
    def __init__(self, parent, db, purchase):
        super().__init__(parent)
        self.db = db; self.purchase = purchase
        self.setWindowTitle(f"PO: {purchase['po_number']}")
        self.setMinimumSize(620,460); self.setModal(True)
        layout = QVBoxLayout(self); layout.setContentsMargins(20,16,20,16); layout.setSpacing(10)
        hr = QHBoxLayout()
        hr.addWidget(QLabel(purchase["po_number"], styleSheet=f"font-size:16px;font-weight:700;color:{PRIMARY};"))
        SC = {"paid":SUCCESS,"partial":WARNING,"unpaid":DANGER}
        hr.addWidget(QLabel(purchase["status"].upper(),
            styleSheet=f"font-size:12px;font-weight:700;color:{SC.get(purchase['status'],TEXT_MID)};"))
        hr.addStretch(); layout.addLayout(hr)
        ir = QHBoxLayout()
        for lbl, val in [("Supplier:", purchase["supplier"]), ("Date:", purchase["purchase_date"]),
                         ("Payment:", purchase["payment_type"])]:
            ir.addWidget(QLabel(f"<b>{lbl}</b> {val}")); ir.addSpacing(20)
        ir.addStretch(); layout.addLayout(ir)
        items = db.get_purchase_items(purchase["id"])
        t = QTableWidget(len(items), 4)
        t.setHorizontalHeaderLabels(["Product","Unit","Qty","Unit Price","Total"])
        t.setColumnCount(5)
        t.setHorizontalHeaderLabels(["Product","Unit","Qty","Cost Price","Total"])
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.setAlternatingRowColors(True); t.verticalHeader().setVisible(False)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        t.setStyleSheet(TABLE_STYLE)
        for r, item in enumerate(items):
            for c, v in enumerate([item["product_name"],item["unit"],str(item["quantity"]),
                                    f"${item['unit_price']:.2f}",f"${item['total']:.2f}"]):
                t.setItem(r, c, QTableWidgetItem(v))
        layout.addWidget(t)
        tf = QFrame(); tf.setStyleSheet("background:#F9FAFB;border-radius:8px;")
        tl = QGridLayout(tf); tl.setContentsMargins(16,10,16,10); tl.setSpacing(6)
        for r, (lbl, val, bold) in enumerate([
            ("TOTAL:", f"${purchase['total']:.2f}", True),
            ("Paid:",  f"${purchase['paid_amount']:.2f}", False),
            ("Due:",   f"${purchase['due_amount']:.2f}", True),
        ]):
            ll = QLabel(lbl); vl = QLabel(val)
            if bold: vl.setStyleSheet(f"font-weight:700;color:{DANGER if 'Due' in lbl else PRIMARY};")
            tl.addWidget(ll, r,0); tl.addWidget(vl, r,1)
        layout.addWidget(tf)
        btns = QHBoxLayout(); btns.addStretch()
        p = btn("Print PO", WARNING); p.clicked.connect(self._print_po)
        btns.addWidget(p)
        if purchase["due_amount"] > 0:
            pay = btn("Pay Supplier", SUCCESS); pay.clicked.connect(self._pay)
            btns.addWidget(pay)
        c = btn("Close","#E5E7EB","#374151"); c.clicked.connect(self.accept)
        btns.addWidget(c); layout.addLayout(btns)

    def _print_po(self):
        from invoices.templates import build_a4_purchase_invoice, build_pos_purchase_receipt
        from invoices.printer import PrintInvoiceDialog
        items = [dict(i) for i in self.db.get_purchase_items(self.purchase["id"])]
        company = self.db.get_company_info()
        a4  = build_a4_purchase_invoice(dict(self.purchase), items, company)
        pos = build_pos_purchase_receipt(dict(self.purchase), items, company)
        PrintInvoiceDialog(self, a4, pos, self.purchase["po_number"], "Print Purchase Order").exec()

    def _pay(self):
        from PyQt6.QtWidgets import QInputDialog
        amount, ok = QInputDialog.getDouble(
            self,"Pay Supplier",
            f"Amount to pay (Due: ${self.purchase['due_amount']:.2f}):",
            self.purchase["due_amount"], 0.01, self.purchase["due_amount"], 2
        )
        if ok:
            try:
                self.db.pay_supplier(self.purchase["id"], amount)
                QMessageBox.information(self,"Success",f"${amount:.2f} paid.")
                self.accept()
            except Exception as e:
                QMessageBox.critical(self,"Error",str(e))


class PurchasesPage(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db; self._rows = []
        self._build(); self.refresh()

    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(24,24,24,24); root.setSpacing(16)
        hr = QHBoxLayout()
        hr.addWidget(page_title("Purchases")); hr.addStretch()
        self.search = search_box("  Search PO, supplier…")
        self.search.textChanged.connect(self.refresh); hr.addWidget(self.search)
        self.status_filter = QComboBox(); self.status_filter.setFixedWidth(120)
        self.status_filter.setStyleSheet(FIELD_STYLE)
        self.status_filter.addItem("All Status", None)
        for s in ["paid","partial","unpaid"]: self.status_filter.addItem(s.title(), s)
        self.status_filter.currentIndexChanged.connect(self.refresh); hr.addWidget(self.status_filter)
        self.df = QDateEdit(QDate.currentDate().addMonths(-1))
        self.dt = QDateEdit(QDate.currentDate())
        for d in [self.df, self.dt]:
            d.setStyleSheet(FIELD_STYLE); d.setCalendarPopup(True); d.setFixedWidth(115)
            d.dateChanged.connect(self.refresh)
        hr.addWidget(QLabel("From:")); hr.addWidget(self.df)
        hr.addWidget(QLabel("To:")); hr.addWidget(self.dt)
        a = btn("+ New Purchase", WARNING); a.clicked.connect(self.new_purchase); hr.addWidget(a)
        root.addLayout(hr)

        sf = QFrame(); sf.setStyleSheet("QFrame{background:#FEF3C7;border-radius:8px;}")
        sl = QHBoxLayout(sf); sl.setContentsMargins(16,8,16,8)
        self.lbl_sum = QLabel(); self.lbl_sum.setStyleSheet("font-size:13px;font-weight:600;color:#92400E;")
        sl.addWidget(self.lbl_sum); sl.addStretch(); root.addWidget(sf)

        f = card_frame(); fl = QVBoxLayout(f); fl.setContentsMargins(0,0,0,0)
        HEADERS = ["#","PO Number","Supplier","Date","Subtotal","Disc","Tax","Total","Paid","Due","Payment","Status"]
        self.table = QTableWidget(); self.table.setColumnCount(len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True); self.table.verticalHeader().setVisible(False)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(0,QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(0,40)
        self.table.setStyleSheet(TABLE_STYLE)
        self.table.doubleClicked.connect(self.view_purchase)
        fl.addWidget(self.table); root.addWidget(f)

        ar = QHBoxLayout(); ar.addStretch()
        v = btn("View / Pay", PRIMARY); v.clicked.connect(self.view_purchase); ar.addWidget(v)
        root.addLayout(ar)

    def refresh(self):
        df = self.df.date().toString("yyyy-MM-dd")
        dt = self.dt.date().toString("yyyy-MM-dd")
        rows = self.db.get_all_purchases(
            self.search.text().strip(), self.status_filter.currentData(), df, dt
        )
        self._rows = rows
        self.table.setRowCount(len(rows))
        total = sum(r["total"] for r in rows)
        paid  = sum(r["paid_amount"] for r in rows)
        due   = sum(r["due_amount"] for r in rows)
        self.lbl_sum.setText(
            f"Records: {len(rows)}  |  Total: ${total:,.2f}  |  Paid: ${paid:,.2f}  |  Outstanding: ${due:,.2f}"
        )
        SC = {"paid":SUCCESS,"partial":WARNING,"unpaid":DANGER}
        for i, r in enumerate(rows):
            vals = [str(r["id"]), r["po_number"], r["supplier"], r["purchase_date"],
                    f"${r['subtotal']:.2f}", f"${r['discount']:.2f}", f"${r['tax_amount']:.2f}",
                    f"${r['total']:.2f}", f"${r['paid_amount']:.2f}", f"${r['due_amount']:.2f}",
                    r["payment_type"], r["status"]]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if c == 11:
                    item.setForeground(QColor(SC.get(v,TEXT_MID)))
                    item.setFont(QFont("", -1, QFont.Weight.Bold))
                self.table.setItem(i, c, item)

    def _selected(self):
        r = self.table.currentRow()
        if r < 0: QMessageBox.information(self,"Select","Select a purchase first."); return None
        return self._rows[r]

    def new_purchase(self):
        dlg = PurchaseDialog(self, self.db)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            try:
                po = self.db.create_purchase(**d)
                QMessageBox.information(self,"Success",f"Order {po} saved."); self.refresh()
            except Exception as e:
                QMessageBox.critical(self,"Error",str(e))

    def view_purchase(self):
        row = self._selected()
        if row:
            PurchaseDetailDialog(self, self.db, row).exec(); self.refresh()
