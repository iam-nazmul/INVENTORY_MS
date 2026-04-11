from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QTextEdit,
    QCheckBox, QScrollArea, QFrame, QMessageBox, QDialog,
    QGridLayout, QSizePolicy, QSplitter
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from styles import (PRIMARY, DANGER, SUCCESS, WARNING, TEXT_DARK, TEXT_MID,
                    TEXT_LIGHT, BG_CARD, BORDER, FIELD_STYLE)


def _btn(text, color=PRIMARY, w=None):
    b = QPushButton(text)
    b.setStyleSheet(f"""
        QPushButton {{
            background: {color}; color: white; border: none;
            border-radius: 6px; padding: 7px 16px;
            font-size: 12px; font-weight: 600;
        }}
        QPushButton:hover {{ opacity: 0.85; }}
        QPushButton:disabled {{ background: #CBD5E1; color: #94A3B8; }}
    """)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if w:
        b.setFixedWidth(w)
    return b


def _field_style():
    return f"""
        QLineEdit, QTextEdit {{
            border: 1.5px solid {BORDER}; border-radius: 6px;
            padding: 6px 10px; font-size: 13px;
            color: {TEXT_DARK}; background: #FAFAFA;
        }}
        QLineEdit:focus, QTextEdit:focus {{ border-color: {PRIMARY}; }}
    """


class AddRoleDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Add Role")
        self.setFixedSize(360, 260)
        self.setStyleSheet(f"QDialog {{ background: #F8FAFC; }}")
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 20)
        lay.setSpacing(0)

        title = QLabel("New Role")
        title.setStyleSheet(f"font-size:16px;font-weight:700;color:{TEXT_DARK};")
        lay.addWidget(title)
        lay.addSpacing(16)

        for attr, lbl_text, ph, widget_cls, height in [
            ("_name", "Role Name",   "e.g. Manager",         QLineEdit,  None),
            ("_desc", "Description", "Brief description…",   QTextEdit,  60),
        ]:
            lbl = QLabel(lbl_text)
            lbl.setStyleSheet(f"font-size:11px;font-weight:600;color:{TEXT_LIGHT};letter-spacing:1px;")
            w = widget_cls(); w.setPlaceholderText(ph)
            w.setStyleSheet(_field_style())
            if height:
                w.setFixedHeight(height)
            lay.addWidget(lbl); lay.addSpacing(4); lay.addWidget(w); lay.addSpacing(12)
            setattr(self, attr, w)

        self._err = QLabel("")
        self._err.setStyleSheet(f"color:{DANGER};font-size:12px;")
        lay.addWidget(self._err)
        lay.addSpacing(8)

        row = QHBoxLayout(); row.setSpacing(8)
        cancel = _btn("Cancel", "#6B7280"); cancel.clicked.connect(self.reject)
        ok = _btn("Create Role"); ok.clicked.connect(self._submit)
        row.addWidget(cancel); row.addWidget(ok)
        lay.addLayout(row)

    def _submit(self):
        name = self._name.text().strip()
        desc = self._desc.toPlainText().strip()
        try:
            self.db.create_role(name, desc)
            self.accept()
        except ValueError as e:
            self._err.setText(str(e))


class RolesPage(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self._current_role = None   # dict: id, name, description
        self._menu_checks  = {}     # menu_id -> QCheckBox
        self._group_all    = {}     # section -> QCheckBox  (Select All)
        self._build()
        self.refresh()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # Header
        hdr = QHBoxLayout()
        t = QLabel("Roles & Permissions")
        t.setStyleSheet(f"font-size:22px;font-weight:700;color:{TEXT_DARK};")
        hdr.addWidget(t); hdr.addStretch()
        add_btn = _btn("+ Add Role", w=110)
        add_btn.clicked.connect(self._add_role)
        hdr.addWidget(add_btn)
        root.addLayout(hdr)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(6)
        splitter.setStyleSheet("QSplitter::handle { background: #E2E8F0; }")

        # ── Left: roles list ──────────────────────────────────────────────────
        left = QFrame()
        left.setStyleSheet(f"QFrame{{background:{BG_CARD};border-radius:12px;}}")
        left.setFixedWidth(220)
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(14, 14, 14, 14)
        left_lay.setSpacing(8)

        lbl = QLabel("Roles")
        lbl.setStyleSheet(f"font-size:13px;font-weight:700;color:{TEXT_MID};")
        left_lay.addWidget(lbl)

        self._role_list = QListWidget()
        self._role_list.setStyleSheet(f"""
            QListWidget {{
                border: 1.5px solid {BORDER}; border-radius: 8px;
                background: #FAFAFA; font-size: 13px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 10px 12px; border-bottom: 1px solid #F1F5F9;
                color: {TEXT_DARK};
            }}
            QListWidget::item:selected {{
                background: {PRIMARY}; color: white; border-radius: 6px;
            }}
            QListWidget::item:hover:!selected {{ background: #EEF2FF; }}
        """)
        self._role_list.currentItemChanged.connect(self._on_role_selected)
        left_lay.addWidget(self._role_list)

        self._del_btn = _btn("Delete Role", DANGER)
        self._del_btn.setEnabled(False)
        self._del_btn.clicked.connect(self._delete_role)
        left_lay.addWidget(self._del_btn)

        splitter.addWidget(left)

        # ── Right: editor + permissions ───────────────────────────────────────
        right = QFrame()
        right.setStyleSheet(f"QFrame{{background:{BG_CARD};border-radius:12px;}}")
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(20, 18, 20, 18)
        right_lay.setSpacing(12)

        self._right_title = QLabel("Select a role to edit")
        self._right_title.setStyleSheet(
            f"font-size:15px;font-weight:700;color:{TEXT_DARK};"
        )
        right_lay.addWidget(self._right_title)

        # Role details form
        form_frame = QFrame()
        form_frame.setStyleSheet(
            f"QFrame{{background:#F8FAFC;border:1px solid {BORDER};border-radius:8px;}}"
        )
        form_lay = QGridLayout(form_frame)
        form_lay.setContentsMargins(14, 12, 14, 12)
        form_lay.setSpacing(8)

        form_lay.addWidget(self._field_lbl("ROLE NAME"), 0, 0)
        self._inp_name = QLineEdit()
        self._inp_name.setStyleSheet(_field_style())
        self._inp_name.setPlaceholderText("Role name")
        form_lay.addWidget(self._inp_name, 1, 0)

        form_lay.addWidget(self._field_lbl("DESCRIPTION"), 0, 1)
        self._inp_desc = QLineEdit()
        self._inp_desc.setStyleSheet(_field_style())
        self._inp_desc.setPlaceholderText("Brief description")
        form_lay.addWidget(self._inp_desc, 1, 1)

        save_det = _btn("Save Details", SUCCESS, w=110)
        save_det.clicked.connect(self._save_details)
        form_lay.addWidget(save_det, 1, 2, alignment=Qt.AlignmentFlag.AlignBottom)

        right_lay.addWidget(form_frame)

        # Divider
        div = QFrame(); div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"color:{BORDER};")
        right_lay.addWidget(div)

        # Group Permissions header
        perm_hdr = QHBoxLayout()
        ph = QLabel("Group Permissions")
        ph.setStyleSheet(f"font-size:14px;font-weight:700;color:{TEXT_MID};")
        perm_hdr.addWidget(ph); perm_hdr.addStretch()
        save_perm = _btn("Save Permissions", PRIMARY, w=140)
        save_perm.clicked.connect(self._save_permissions)
        perm_hdr.addWidget(save_perm)
        right_lay.addLayout(perm_hdr)

        # Scrollable permission area (groups of checkboxes)
        perm_scroll = QScrollArea()
        perm_scroll.setWidgetResizable(True)
        perm_scroll.setStyleSheet(
            f"QScrollArea{{border:1.5px solid {BORDER};border-radius:8px;background:#FAFAFA;}}"
        )
        self._perm_widget = QWidget()
        self._perm_widget.setStyleSheet("background: transparent;")
        self._perm_layout = QVBoxLayout(self._perm_widget)
        self._perm_layout.setContentsMargins(12, 10, 12, 10)
        self._perm_layout.setSpacing(4)
        perm_scroll.setWidget(self._perm_widget)
        right_lay.addWidget(perm_scroll)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter)

        # Build the checkbox grid (once, reused with setChecked)
        self._build_permission_grid()

        # Disable right panel until role selected
        self._set_editor_enabled(False)

    def _field_lbl(self, text):
        l = QLabel(text)
        l.setStyleSheet(
            f"font-size:10px;font-weight:700;color:{TEXT_LIGHT};letter-spacing:1px;"
        )
        return l

    def _build_permission_grid(self):
        menus = self.db.get_menus()

        # Group menus by section
        groups = {}   # section -> [menu_row, ...]
        order  = []
        for m in menus:
            sec = m["section"] or "GENERAL"
            if sec not in groups:
                groups[sec] = []
                order.append(sec)
            groups[sec].append(m)

        CB_STYLE = f"""
            QCheckBox {{
                font-size: 12px; color: {TEXT_DARK}; spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 15px; height: 15px;
                border: 1.5px solid #CBD5E1; border-radius: 4px;
                background: white;
            }}
            QCheckBox::indicator:checked {{
                background: {PRIMARY}; border-color: {PRIMARY};
            }}
        """
        ALL_CB_STYLE = f"""
            QCheckBox {{
                font-size: 11px; font-weight: 700; color: {PRIMARY}; spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 14px; height: 14px;
                border: 1.5px solid {PRIMARY}; border-radius: 3px; background: white;
            }}
            QCheckBox::indicator:checked {{
                background: {PRIMARY}; border-color: {PRIMARY};
            }}
        """

        for sec in order:
            items = groups[sec]

            # Section header row
            sec_row = QHBoxLayout(); sec_row.setSpacing(10)

            sec_lbl = QLabel(sec)
            sec_lbl.setStyleSheet(
                f"font-size:10px;font-weight:800;color:{TEXT_LIGHT};"
                f"letter-spacing:1.5px;padding:6px 0 2px 0;"
            )
            sec_row.addWidget(sec_lbl)

            sep_line = QFrame(); sep_line.setFrameShape(QFrame.Shape.HLine)
            sep_line.setStyleSheet(f"color:{BORDER};")
            sep_line.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            sec_row.addWidget(sep_line)

            all_cb = QCheckBox("All")
            all_cb.setStyleSheet(ALL_CB_STYLE)
            sec_row.addWidget(all_cb)
            self._group_all[sec] = all_cb

            self._perm_layout.addLayout(sec_row)

            # Menu checkboxes in a grid (3 per row)
            grid = QGridLayout(); grid.setSpacing(6); grid.setContentsMargins(8, 0, 0, 8)
            for idx, m in enumerate(items):
                cb = QCheckBox(m["icon"] + "  " + m["name"] if m["icon"] else m["name"])
                cb.setStyleSheet(CB_STYLE)
                cb.setProperty("menu_id", m["id"])
                cb.setProperty("section", sec)
                self._menu_checks[m["id"]] = cb
                grid.addWidget(cb, idx // 3, idx % 3)
            self._perm_layout.addLayout(grid)

            # Wire "All" checkbox for this section
            def _make_all_handler(section_name, cb_all):
                def _toggle(state):
                    checked = (state == Qt.CheckState.Checked.value
                               or state == 2)
                    for mid, cb in self._menu_checks.items():
                        if cb.property("section") == section_name:
                            cb.setChecked(checked)
                return _toggle
            all_cb.stateChanged.connect(_make_all_handler(sec, all_cb))

        self._perm_layout.addStretch()

    # ── Data helpers ──────────────────────────────────────────────────────────

    def refresh(self):
        roles = self.db.get_all_roles()
        self._role_list.blockSignals(True)
        self._role_list.clear()
        for r in roles:
            item = QListWidgetItem(f"  {r['name']}")
            item.setData(Qt.ItemDataRole.UserRole, dict(r))
            item.setToolTip(r["description"] or "")
            self._role_list.addItem(item)
        self._role_list.blockSignals(False)

        # Re-select current role if still present
        if self._current_role:
            for i in range(self._role_list.count()):
                d = self._role_list.item(i).data(Qt.ItemDataRole.UserRole)
                if d["id"] == self._current_role["id"]:
                    self._role_list.setCurrentRow(i)
                    break

    def _on_role_selected(self, item):
        if item is None:
            self._current_role = None
            self._set_editor_enabled(False)
            return
        role = item.data(Qt.ItemDataRole.UserRole)
        self._current_role = role
        self._load_role(role)

    def _load_role(self, role):
        self._right_title.setText(f"Editing: {role['name']}")
        self._inp_name.setText(role["name"])
        self._inp_desc.setText(role["description"] or "")

        # Builtin roles: name/desc are read-only
        is_builtin = role["name"] in ("admin", "staff")
        self._inp_name.setReadOnly(is_builtin)
        self._inp_desc.setReadOnly(is_builtin)
        self._del_btn.setEnabled(not is_builtin)

        self._set_editor_enabled(True)

        # Load permissions
        allowed = self.db.get_role_permissions(role["id"])
        for mid, cb in self._menu_checks.items():
            cb.setChecked(mid in allowed)

        # Update "All" group checkboxes state
        for sec, all_cb in self._group_all.items():
            sec_checks = [cb for cb in self._menu_checks.values()
                          if cb.property("section") == sec]
            all_cb.blockSignals(True)
            all_cb.setChecked(all(cb.isChecked() for cb in sec_checks))
            all_cb.blockSignals(False)

    def _set_editor_enabled(self, enabled):
        for w in [self._inp_name, self._inp_desc]:
            w.setEnabled(enabled)
        for cb in self._menu_checks.values():
            cb.setEnabled(enabled)
        for cb in self._group_all.values():
            cb.setEnabled(enabled)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _add_role(self):
        dlg = AddRoleDialog(self.db, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _delete_role(self):
        if not self._current_role:
            return
        name = self._current_role["name"]
        if QMessageBox.question(
            self, "Confirm Delete",
            f"Delete role '{name}'? Users assigned this role will lose it.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db.delete_role(self._current_role["id"])
            self._current_role = None
            self._set_editor_enabled(False)
            self._right_title.setText("Select a role to edit")
            self.refresh()
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))

    def _save_details(self):
        if not self._current_role:
            return
        name = self._inp_name.text().strip()
        desc = self._inp_desc.text().strip()
        try:
            self.db.update_role(self._current_role["id"], name, desc)
            self._current_role["name"] = name
            self._current_role["description"] = desc
            self._right_title.setText(f"Editing: {name}")
            self.refresh()
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))

    def _save_permissions(self):
        if not self._current_role:
            return
        checked_ids = {mid for mid, cb in self._menu_checks.items() if cb.isChecked()}
        self.db.set_role_permissions(self._current_role["id"], checked_ids)
        QMessageBox.information(self, "Saved",
            f"Permissions for '{self._current_role['name']}' saved.\n"
            "Users will see the updated menus on next login.")
