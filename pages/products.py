from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QFormLayout, QMessageBox, QFrame, QComboBox,
    QDoubleSpinBox, QSpinBox, QTextEdit, QLineEdit, QPushButton, QFileDialog,
    QScrollArea
)
from PyQt6.QtCore import Qt, QByteArray
from PyQt6.QtGui import QColor, QFont, QPixmap, QPainter, QPainterPath
from styles import (btn, page_title, card_frame, search_box,
                    PRIMARY, SUCCESS, DANGER, FIELD_STYLE, TABLE_STYLE,
                    TEXT_LIGHT, TEXT_DARK, TEXT_MID, BG_CARD, BORDER)

_IMG_SIZE   = 46   # thumbnail size in table rows
_PREV_SIZE  = 110  # preview size in dialog


def _pick_image_bytes(parent=None) -> bytes | None:
    path, _ = QFileDialog.getOpenFileName(
        parent, "Select Product Image", "",
        "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
    )
    if not path:
        return None
    with open(path, "rb") as f:
        return f.read()


def _rounded_pixmap(data: bytes, size: int) -> QPixmap | None:
    """Return a rounded-corner pixmap from raw bytes, or None on failure."""
    pm = QPixmap()
    pm.loadFromData(QByteArray(data))
    if pm.isNull():
        return None
    pm = pm.scaled(size, size,
                   Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                   Qt.TransformationMode.SmoothTransformation)
    out = QPixmap(size, size)
    out.fill(Qt.GlobalColor.transparent)
    painter = QPainter(out)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(0, 0, size, size, 8, 8)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, pm)
    painter.end()
    return out


def _thumb_widget(data: bytes | None, size: int = _IMG_SIZE) -> QWidget:
    """Cell widget: product thumbnail or a neutral placeholder."""
    wrap = QWidget()
    lay  = QHBoxLayout(wrap)
    lay.setContentsMargins(6, 4, 6, 4)
    lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

    lbl = QLabel()
    lbl.setFixedSize(size, size)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

    if data:
        pm = _rounded_pixmap(data, size)
        if pm:
            lbl.setPixmap(pm)
            lay.addWidget(lbl)
            return wrap

    # placeholder
    lbl.setStyleSheet(
        f"background:#E2E8F0;border-radius:6px;color:#94A3B8;font-size:18px;"
    )
    lbl.setText("📦")
    lay.addWidget(lbl)
    return wrap


class ProductDialog(QDialog):
    def __init__(self, parent, db, data=None):
        super().__init__(parent)
        self.db = db
        self._image_bytes: bytes | None = None
        self._keep_existing_image: bool = True   # used during edit
        self.setWindowTitle("Add Product" if data is None else "Edit Product")
        self.setMinimumWidth(540)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)
        root.addWidget(QLabel(self.windowTitle(),
            styleSheet="font-size:16px;font-weight:700;color:#111827;"))

        # ── Image picker ──────────────────────────────────────────────────────
        img_frame = QFrame()
        img_frame.setStyleSheet(
            f"QFrame{{background:#F8FAFC;border-radius:10px;border:1px solid {BORDER};}}"
        )
        img_lay = QHBoxLayout(img_frame)
        img_lay.setContentsMargins(14, 12, 14, 12)
        img_lay.setSpacing(16)

        # Preview box
        self._preview = QLabel()
        self._preview.setFixedSize(_PREV_SIZE, _PREV_SIZE)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setStyleSheet(
            "background:#E2E8F0;border-radius:8px;color:#94A3B8;font-size:36px;"
        )
        self._preview.setText("📦")
        img_lay.addWidget(self._preview)

        btn_col = QVBoxLayout(); btn_col.setSpacing(8)
        img_title = QLabel("PRODUCT IMAGE")
        img_title.setStyleSheet(f"font-size:10px;font-weight:700;color:{TEXT_LIGHT};letter-spacing:1px;")
        img_hint = QLabel("Optional · PNG / JPG / WEBP")
        img_hint.setStyleSheet("font-size:11px;color:#94A3B8;")

        self._choose_btn = QPushButton("Choose Image")
        self._choose_btn.setStyleSheet(f"""
            QPushButton {{
                background:#EEF2FF;color:#4F46E5;border:1.5px solid #C7D2FE;
                border-radius:7px;padding:7px 16px;font-size:12px;font-weight:600;
            }}
            QPushButton:hover {{ background:#E0E7FF; }}
        """)
        self._choose_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._choose_btn.clicked.connect(self._pick_image)

        self._clear_btn = QPushButton("Remove Image")
        self._clear_btn.setStyleSheet(f"""
            QPushButton {{
                background:transparent;color:#EF4444;border:1px solid #FCA5A5;
                border-radius:7px;padding:6px 14px;font-size:11px;font-weight:600;
            }}
            QPushButton:hover {{ background:#FEF2F2; }}
        """)
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.clicked.connect(self._clear_image)
        self._clear_btn.setVisible(False)

        self._img_status = QLabel("No image selected")
        self._img_status.setStyleSheet("font-size:11px;color:#94A3B8;")

        btn_col.addWidget(img_title)
        btn_col.addWidget(img_hint)
        btn_col.addWidget(self._choose_btn)
        btn_col.addWidget(self._clear_btn)
        btn_col.addWidget(self._img_status)
        btn_col.addStretch()
        img_lay.addLayout(btn_col)
        img_lay.addStretch()
        root.addWidget(img_frame)

        # ── Form fields ───────────────────────────────────────────────────────
        form = QFormLayout(); form.setSpacing(10)
        self.name        = QLineEdit(); self.name.setPlaceholderText("Product name")
        self.sku         = QLineEdit(); self.sku.setPlaceholderText("Auto-generated if blank")
        self.category    = QComboBox()
        self.supplier    = QComboBox()
        self.unit        = QLineEdit(); self.unit.setPlaceholderText("pcs, kg, box…")
        self.cost_price  = QDoubleSpinBox()
        self.cost_price.setRange(0, 9999999); self.cost_price.setDecimals(2)
        self.cost_price.setPrefix("$ ")
        self.sale_price  = QDoubleSpinBox()
        self.sale_price.setRange(0, 9999999); self.sale_price.setDecimals(2)
        self.sale_price.setPrefix("$ ")
        self.quantity    = QSpinBox(); self.quantity.setRange(0, 999999)
        self.min_stock   = QSpinBox()
        self.min_stock.setRange(0, 999999); self.min_stock.setValue(10)
        self.description = QTextEdit()
        self.description.setPlaceholderText("Optional")
        self.description.setMaximumHeight(60)

        for w in [self.name, self.sku, self.category, self.supplier, self.unit,
                  self.cost_price, self.sale_price, self.quantity, self.min_stock,
                  self.description]:
            w.setStyleSheet(FIELD_STYLE)

        form.addRow("Name *",      self.name)
        form.addRow("SKU",         self.sku)

        # Category row: combo + "+ New" button + inline create panel
        cat_col = QVBoxLayout(); cat_col.setSpacing(4)

        cat_top = QHBoxLayout(); cat_top.setSpacing(6)
        cat_top.addWidget(self.category)
        self._new_cat_btn = QPushButton("+ New")
        self._new_cat_btn.setFixedSize(60, 32)
        self._new_cat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._new_cat_btn.setStyleSheet("""
            QPushButton {
                background: #EEF2FF; color: #4F46E5;
                border: 1.5px solid #C7D2FE; border-radius: 6px;
                font-size: 12px; font-weight: 700;
            }
            QPushButton:hover { background: #E0E7FF; }
        """)
        self._new_cat_btn.clicked.connect(self._toggle_new_cat)
        cat_top.addWidget(self._new_cat_btn)
        cat_col.addLayout(cat_top)

        # Inline create panel (hidden by default)
        self._cat_create_panel = QFrame()
        self._cat_create_panel.setStyleSheet(
            "QFrame{background:#F0FDF4;border-radius:7px;border:1px solid #86EFAC;}"
        )
        cp_lay = QHBoxLayout(self._cat_create_panel)
        cp_lay.setContentsMargins(8, 6, 8, 6); cp_lay.setSpacing(6)
        self._new_cat_input = QLineEdit()
        self._new_cat_input.setPlaceholderText("New category name…")
        self._new_cat_input.setStyleSheet(FIELD_STYLE)
        self._new_cat_input.setFixedHeight(32)
        self._new_cat_input.returnPressed.connect(self._create_category)
        create_btn = QPushButton("Create")
        create_btn.setFixedSize(60, 32)
        create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        create_btn.setStyleSheet("""
            QPushButton {
                background: #22C55E; color: white;
                border: none; border-radius: 6px;
                font-size: 12px; font-weight: 700;
            }
            QPushButton:hover { background: #16A34A; }
        """)
        create_btn.clicked.connect(self._create_category)
        cancel_cat_btn = QPushButton("✕")
        cancel_cat_btn.setFixedSize(32, 32)
        cancel_cat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_cat_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #94A3B8;
                border: 1px solid #CBD5E1; border-radius: 6px;
                font-size: 13px; font-weight: 700;
            }
            QPushButton:hover { color: #EF4444; border-color: #FCA5A5; }
        """)
        cancel_cat_btn.clicked.connect(self._hide_new_cat)
        cp_lay.addWidget(self._new_cat_input)
        cp_lay.addWidget(create_btn)
        cp_lay.addWidget(cancel_cat_btn)
        self._cat_create_panel.setVisible(False)
        cat_col.addWidget(self._cat_create_panel)

        form.addRow("Category",    cat_col)

        # Supplier row: combo + "+ New" button + inline create panel
        sup_col = QVBoxLayout(); sup_col.setSpacing(4)

        sup_top = QHBoxLayout(); sup_top.setSpacing(6)
        sup_top.addWidget(self.supplier)
        self._new_sup_btn = QPushButton("+ New")
        self._new_sup_btn.setFixedSize(60, 32)
        self._new_sup_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._new_sup_btn.setStyleSheet("""
            QPushButton {
                background: #FFF7ED; color: #EA580C;
                border: 1.5px solid #FED7AA; border-radius: 6px;
                font-size: 12px; font-weight: 700;
            }
            QPushButton:hover { background: #FFEDD5; }
        """)
        self._new_sup_btn.clicked.connect(self._toggle_new_sup)
        sup_top.addWidget(self._new_sup_btn)
        sup_col.addLayout(sup_top)

        # Inline create panel (hidden by default)
        self._sup_create_panel = QFrame()
        self._sup_create_panel.setStyleSheet(
            "QFrame{background:#FFF7ED;border-radius:7px;border:1px solid #FDBA74;}"
        )
        sp_lay = QHBoxLayout(self._sup_create_panel)
        sp_lay.setContentsMargins(8, 6, 8, 6); sp_lay.setSpacing(6)
        self._new_sup_input = QLineEdit()
        self._new_sup_input.setPlaceholderText("New supplier name…")
        self._new_sup_input.setStyleSheet(FIELD_STYLE)
        self._new_sup_input.setFixedHeight(32)
        self._new_sup_input.returnPressed.connect(self._create_supplier)
        create_sup_btn = QPushButton("Create")
        create_sup_btn.setFixedSize(60, 32)
        create_sup_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        create_sup_btn.setStyleSheet("""
            QPushButton {
                background: #F97316; color: white;
                border: none; border-radius: 6px;
                font-size: 12px; font-weight: 700;
            }
            QPushButton:hover { background: #EA580C; }
        """)
        create_sup_btn.clicked.connect(self._create_supplier)
        cancel_sup_btn = QPushButton("✕")
        cancel_sup_btn.setFixedSize(32, 32)
        cancel_sup_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_sup_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #94A3B8;
                border: 1px solid #CBD5E1; border-radius: 6px;
                font-size: 13px; font-weight: 700;
            }
            QPushButton:hover { color: #EF4444; border-color: #FCA5A5; }
        """)
        cancel_sup_btn.clicked.connect(self._hide_new_sup)
        sp_lay.addWidget(self._new_sup_input)
        sp_lay.addWidget(create_sup_btn)
        sp_lay.addWidget(cancel_sup_btn)
        self._sup_create_panel.setVisible(False)
        sup_col.addWidget(self._sup_create_panel)

        form.addRow("Supplier",    sup_col)
        form.addRow("Unit",        self.unit)
        pr = QHBoxLayout()
        pr.addWidget(self.cost_price)
        pr.addWidget(QLabel("Sale:"))
        pr.addWidget(self.sale_price)
        form.addRow("Cost Price",  pr)
        qr = QHBoxLayout()
        qr.addWidget(self.quantity)
        qr.addWidget(QLabel("Min:"))
        qr.addWidget(self.min_stock)
        form.addRow("Quantity",    qr)
        form.addRow("Description", self.description)
        root.addLayout(form)

        # Populate combos
        self._cats = [{"id": None, "name": "— None —"}] + [dict(r) for r in db.get_all_categories()]
        self._sups = [{"id": None, "name": "— None —"}] + [dict(r) for r in db.get_all_suppliers()]
        for c in self._cats: self.category.addItem(c["name"], c["id"])
        for s in self._sups: self.supplier.addItem(s["name"], s["id"])

        # Pre-fill when editing
        if data:
            self.name.setText(data.get("name", ""))
            self.sku.setText(data.get("sku", "") or "")
            self.unit.setText(data.get("unit", "pcs"))
            self.cost_price.setValue(data.get("cost_price", 0) or 0)
            self.sale_price.setValue(data.get("sale_price", 0) or 0)
            self.quantity.setValue(data.get("quantity", 0) or 0)
            self.min_stock.setValue(data.get("min_stock", 10) or 10)
            self.description.setText(data.get("description", "") or "")
            for i, c in enumerate(self._cats):
                if c["id"] == data.get("category_id"):
                    self.category.setCurrentIndex(i)
            for i, s in enumerate(self._sups):
                if s["id"] == data.get("supplier_id"):
                    self.supplier.setCurrentIndex(i)
            # Load existing image
            existing = data.get("image")
            if existing:
                self._image_bytes = existing
                self._refresh_preview(existing)
                self._img_status.setText("Current image loaded")
                self._img_status.setStyleSheet("font-size:11px;color:#059669;")
                self._clear_btn.setVisible(True)

        # Buttons
        btns = QHBoxLayout(); btns.setSpacing(8)
        c = btn("Cancel", "#E5E7EB", "#374151"); c.clicked.connect(self.reject)
        s = btn("Save");   s.clicked.connect(self._validate)
        btns.addStretch()
        btns.addWidget(c); btns.addWidget(s)
        root.addLayout(btns)

    # ── category helpers ──────────────────────────────────────────────────────

    def _toggle_new_cat(self):
        visible = self._cat_create_panel.isVisible()
        self._cat_create_panel.setVisible(not visible)
        if not visible:
            self._new_cat_input.setFocus()
            self._new_cat_btn.setText("✕ Cancel")
        else:
            self._new_cat_input.clear()
            self._new_cat_btn.setText("+ New")

    def _hide_new_cat(self):
        self._cat_create_panel.setVisible(False)
        self._new_cat_input.clear()
        self._new_cat_btn.setText("+ New")

    def _create_category(self):
        name = self._new_cat_input.text().strip()
        if not name:
            self._new_cat_input.setFocus()
            return
        try:
            self.db.add_category(name)
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
            return
        # Repopulate combo and select the newly created category
        self._cats = [{"id": None, "name": "— None —"}] + \
                     [dict(r) for r in self.db.get_all_categories()]
        self.category.blockSignals(True)
        self.category.clear()
        new_index = 0
        for i, c in enumerate(self._cats):
            self.category.addItem(c["name"], c["id"])
            if c["name"] == name:
                new_index = i
        self.category.blockSignals(False)
        self.category.setCurrentIndex(new_index)
        self._hide_new_cat()

    # ── supplier helpers ──────────────────────────────────────────────────────

    def _toggle_new_sup(self):
        visible = self._sup_create_panel.isVisible()
        self._sup_create_panel.setVisible(not visible)
        if not visible:
            self._new_sup_input.setFocus()
            self._new_sup_btn.setText("✕ Cancel")
        else:
            self._new_sup_input.clear()
            self._new_sup_btn.setText("+ New")

    def _hide_new_sup(self):
        self._sup_create_panel.setVisible(False)
        self._new_sup_input.clear()
        self._new_sup_btn.setText("+ New")

    def _create_supplier(self):
        name = self._new_sup_input.text().strip()
        if not name:
            self._new_sup_input.setFocus()
            return
        try:
            self.db.add_supplier(name)
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
            return
        # Repopulate combo and select the newly created supplier
        self._sups = [{"id": None, "name": "— None —"}] + \
                     [dict(r) for r in self.db.get_all_suppliers()]
        self.supplier.blockSignals(True)
        self.supplier.clear()
        new_index = 0
        for i, s in enumerate(self._sups):
            self.supplier.addItem(s["name"], s["id"])
            if s["name"] == name:
                new_index = i
        self.supplier.blockSignals(False)
        self.supplier.setCurrentIndex(new_index)
        self._hide_new_sup()

    # ── image helpers ─────────────────────────────────────────────────────────

    def _refresh_preview(self, data: bytes):
        pm = _rounded_pixmap(data, _PREV_SIZE)
        if pm:
            self._preview.setPixmap(pm)
            self._preview.setStyleSheet("border-radius:8px;")

    def _pick_image(self):
        data = _pick_image_bytes(self)
        if data is None:
            return
        self._image_bytes = data
        self._keep_existing_image = True
        self._refresh_preview(data)
        self._img_status.setText("Image selected")
        self._img_status.setStyleSheet("font-size:11px;color:#059669;")
        self._clear_btn.setVisible(True)

    def _clear_image(self):
        self._image_bytes = None
        self._keep_existing_image = False
        self._preview.setPixmap(QPixmap())
        self._preview.setStyleSheet(
            "background:#E2E8F0;border-radius:8px;color:#94A3B8;font-size:36px;"
        )
        self._preview.setText("📦")
        self._img_status.setText("Image removed")
        self._img_status.setStyleSheet("font-size:11px;color:#EF4444;")
        self._clear_btn.setVisible(False)

    def _validate(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, "Validation", "Product name is required.")
            return
        self.accept()

    def get_data(self):
        return dict(
            name=self.name.text().strip(),
            sku=self.sku.text().strip() or None,
            category_id=self.category.currentData(),
            supplier_id=self.supplier.currentData(),
            unit=self.unit.text().strip() or "pcs",
            cost_price=self.cost_price.value(),
            sale_price=self.sale_price.value(),
            quantity=self.quantity.value(),
            min_stock=self.min_stock.value(),
            description=self.description.toPlainText().strip(),
            image_bytes=self._image_bytes,
        )


class ProductsPage(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db; self._rows = []
        self._build(); self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24); root.setSpacing(16)

        hr = QHBoxLayout()
        hr.addWidget(page_title("Products")); hr.addStretch()
        self.search = search_box("  Search name, SKU…")
        self.search.textChanged.connect(self.refresh)
        hr.addWidget(self.search)
        self.cat_filter = QComboBox(); self.cat_filter.setFixedWidth(160)
        self.cat_filter.setStyleSheet(FIELD_STYLE)
        self.cat_filter.currentIndexChanged.connect(self.refresh)
        hr.addWidget(self.cat_filter)
        a = btn("+ Add Product"); a.clicked.connect(self.add_product)
        hr.addWidget(a); root.addLayout(hr)

        f = card_frame(); fl = QVBoxLayout(f); fl.setContentsMargins(0, 0, 0, 0)
        HEADERS = ["Image", "#", "Name", "SKU", "Category", "Supplier",
                   "Unit", "Stock", "Min", "Cost", "Sale Price", "Updated"]
        self.table = QTableWidget()
        self.table.setColumnCount(len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, _IMG_SIZE + 16)
        self.table.setColumnWidth(1, 50)
        self.table.setStyleSheet(TABLE_STYLE)
        fl.addWidget(self.table); root.addWidget(f)

        ar = QHBoxLayout(); ar.setSpacing(8); ar.addStretch()
        inc = btn("＋  Add Stock",    SUCCESS); inc.clicked.connect(self.increment_stock)
        dec = btn("－  Remove Stock", DANGER);  dec.clicked.connect(self.decrement_stock)
        e   = btn("Edit",             "#6366F1"); e.clicked.connect(self.edit_product)
        d   = btn("Delete",           "#94A3B8", "#374151"); d.clicked.connect(self.delete_product)
        for w in [inc, dec, e, d]: ar.addWidget(w)
        root.addLayout(ar)

        self._reload_cats()

    def _reload_cats(self):
        self.cat_filter.blockSignals(True)
        self.cat_filter.clear()
        self.cat_filter.addItem("All Categories", None)
        for c in self.db.get_all_categories():
            self.cat_filter.addItem(c["name"], c["id"])
        self.cat_filter.blockSignals(False)

    def refresh(self):
        rows = self.db.get_all_products(self.search.text().strip(),
                                        self.cat_filter.currentData())
        self._rows = rows
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setRowHeight(i, _IMG_SIZE + 10)
            low = r["quantity"] <= r["min_stock"]

            # col 0: image thumbnail
            self.table.setCellWidget(i, 0, _thumb_widget(r["image"], _IMG_SIZE))

            # col 1+: text data
            vals = [str(r["id"]), r["name"], r["sku"] or "—",
                    r["category"] or "—", r["supplier"] or "—",
                    r["unit"], str(r["quantity"]), str(r["min_stock"]),
                    f"${r['cost_price']:.2f}", f"${r['sale_price']:.2f}",
                    (r["updated_at"] or "")[:10]]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if c == 6 and low:          # stock column
                    item.setForeground(QColor(DANGER))
                    item.setFont(QFont("", -1, QFont.Weight.Bold))
                self.table.setItem(i, c + 1, item)

    def _selected(self):
        r = self.table.currentRow()
        if r < 0:
            QMessageBox.information(self, "Select", "Select a product first.")
            return None
        return self._rows[r]

    def increment_stock(self):
        self._adjust_stock("IN")

    def decrement_stock(self):
        self._adjust_stock("OUT")

    def _adjust_stock(self, direction):
        row = self._selected()
        if not row:
            return
        from PyQt6.QtWidgets import QInputDialog
        current = row["quantity"]
        label = (f"Add stock to  '{row['name']}'\n"
                 f"Current stock: {current} {row['unit']}\n\nQuantity to add:"
                 ) if direction == "IN" else (
                f"Remove stock from  '{row['name']}'\n"
                f"Current stock: {current} {row['unit']}\n\nQuantity to remove:")
        max_val = 999999 if direction == "IN" else current
        if direction == "OUT" and current == 0:
            QMessageBox.warning(self, "No Stock", f"'{row['name']}' has 0 units in stock.")
            return
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

    def add_product(self):
        dlg = ProductDialog(self, self.db)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            try:
                self.db.add_product(**d)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def edit_product(self):
        row = self._selected()
        if not row:
            return
        full = dict(self.db.get_product_by_id(row["id"]))
        dlg = ProductDialog(self, self.db, full)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            try:
                self.db.update_product(row["id"], **d)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def delete_product(self):
        row = self._selected()
        if not row:
            return
        if QMessageBox.question(
            self, "Delete",
            f"Delete '{row['name']}'? All stock & transactions removed.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            self.db.delete_product(row["id"])
            self.refresh()
