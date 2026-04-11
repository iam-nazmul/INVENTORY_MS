import csv
import os
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QTabWidget, QDateEdit, QFileDialog, QMessageBox,
    QComboBox, QSizePolicy, QScrollArea
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QFont
from styles import (btn, page_title, card_frame, search_box,
                    PRIMARY, SUCCESS, DANGER, WARNING, INFO, PURPLE, ORANGE,
                    FIELD_STYLE, TABLE_STYLE, TEXT_DARK, TEXT_MID, TEXT_LIGHT)

# Chart palette aligned with app colours
_C_SALES     = "#4F46E5"
_C_PURCHASES = "#D97706"
_C_PROFIT    = "#059669"
_C_LOSS      = "#DC2626"
_C_BG        = "#FFFFFF"
_C_GRID      = "#F3F4F6"
_C_TEXT      = "#374151"
_C_SUBTEXT   = "#9CA3AF"


def _date_filter_row(df_attr, dt_attr, on_change):
    """Helper: returns a QHBoxLayout with From/To date pickers."""
    layout = QHBoxLayout(); layout.setSpacing(8)
    df = QDateEdit(QDate.currentDate().addMonths(-1))
    dt = QDateEdit(QDate.currentDate())
    for d in [df, dt]:
        d.setStyleSheet(FIELD_STYLE); d.setCalendarPopup(True); d.setFixedWidth(115)
        d.dateChanged.connect(on_change)
    layout.addWidget(QLabel("From:")); layout.addWidget(df)
    layout.addWidget(QLabel("To:"));   layout.addWidget(dt)
    layout.addStretch()
    return layout, df, dt


class ReportsPage(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self._build(); self.refresh()

    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(24,24,24,24); root.setSpacing(16)
        root.addWidget(page_title("Reports"))

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background: transparent; }
            QTabBar::tab {
                background: #E5E7EB; color: #374151; border-radius: 6px;
                padding: 7px 18px; font-size: 12px; margin-right: 3px;
            }
            QTabBar::tab:selected { background: #4F46E5; color: white; font-weight: 600; }
        """)

        # ── Sales Report ───────────────────────────────────────────────────────
        self._sales_tab = self._make_report_tab(
            tabs, "Sales Report",
            ["Invoice","Customer","Date","Subtotal","Discount","Tax","Total","Paid","Due","Status"],
            "_tbl_sales", "_sr_df", "_sr_dt", self._load_sales,
            summary_attr="_sr_sum"
        )

        # ── Purchase Report ────────────────────────────────────────────────────
        self._pur_tab = self._make_report_tab(
            tabs, "Purchase Report",
            ["PO Number","Supplier","Date","Subtotal","Discount","Tax","Total","Paid","Due","Status"],
            "_tbl_pur", "_pr_df", "_pr_dt", self._load_purchases,
            summary_attr="_pr_sum"
        )

        # ── Profit & Loss ──────────────────────────────────────────────────────
        pl_tab = QWidget()
        pll = QVBoxLayout(pl_tab); pll.setContentsMargins(0,12,0,0); pll.setSpacing(16)
        dr, self._pl_df, self._pl_dt = _date_filter_row("_pl_df","_pl_dt", self._load_pl)
        refresh_btn = btn("Refresh", PRIMARY); refresh_btn.clicked.connect(self._load_pl)
        dr.addWidget(refresh_btn); pll.addLayout(dr)

        # P&L cards
        pl_cards = QHBoxLayout(); pl_cards.setSpacing(16)
        for attr, title, color in [
            ("_pl_rev",  "Total Revenue",        SUCCESS),
            ("_pl_pur",  "Total Purchases",       WARNING),
            ("_pl_prof", "Gross Profit",          PRIMARY),
            ("_pl_gp",   "Gross Profit / Loss",   SUCCESS),
            ("_pl_marg", "Profit Margin",         INFO),
        ]:
            f = QFrame(); f.setStyleSheet(f"QFrame{{background:white;border-radius:12px;border-left:5px solid {color};}}")
            fl = QVBoxLayout(f); fl.setContentsMargins(16,12,16,12); fl.setSpacing(4)
            fl.addWidget(QLabel(title, styleSheet=f"font-size:11px;color:{TEXT_LIGHT};font-weight:600;background:transparent;border:none;"))
            v = QLabel("—"); v.setStyleSheet(f"font-size:24px;font-weight:700;color:{color};background:transparent;border:none;")
            fl.addWidget(v); pl_cards.addWidget(f); setattr(self, attr, v)
        pll.addLayout(pl_cards)

        # Breakdown table
        pl_f = card_frame(); pl_fl = QVBoxLayout(pl_f); pl_fl.setContentsMargins(16,14,16,14)
        self.tbl_pl = QTableWidget(7, 3)
        self.tbl_pl.setHorizontalHeaderLabels(["Description","Amount","% of Revenue"])
        self.tbl_pl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_pl.verticalHeader().setVisible(False)
        self.tbl_pl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_pl.setStyleSheet(TABLE_STYLE); self.tbl_pl.setAlternatingRowColors(True)
        pl_fl.addWidget(self.tbl_pl); pll.addWidget(pl_f)
        tabs.addTab(pl_tab, "Profit & Loss")

        # ── Stock Report ───────────────────────────────────────────────────────
        stk_tab = QWidget()
        stl = QVBoxLayout(stk_tab); stl.setContentsMargins(0,12,0,0); stl.setSpacing(12)
        stk_hr = QHBoxLayout()
        stk_refresh = btn("Refresh", PRIMARY); stk_refresh.clicked.connect(self._load_stock)
        stk_export  = btn("Export CSV", INFO);  stk_export.clicked.connect(lambda: self._export(self.tbl_stock, "stock_report"))
        stk_hr.addStretch(); stk_hr.addWidget(stk_refresh); stk_hr.addWidget(stk_export)
        stl.addLayout(stk_hr)

        sksf = QFrame(); sksf.setStyleSheet("QFrame{background:#EEF2FF;border-radius:8px;}")
        sksl = QHBoxLayout(sksf); sksl.setContentsMargins(16,8,16,8)
        self._stk_sum = QLabel(); self._stk_sum.setStyleSheet(f"font-size:13px;font-weight:600;color:{PRIMARY};")
        sksl.addWidget(self._stk_sum); sksl.addStretch(); stl.addWidget(sksf)

        stk_f = card_frame(); stk_fl = QVBoxLayout(stk_f); stk_fl.setContentsMargins(0,0,0,0)
        STK_HEADERS = ["Product","SKU","Category","Unit","Stock","Min","Cost","Sale","Value","Status"]
        self.tbl_stock = QTableWidget(); self.tbl_stock.setColumnCount(len(STK_HEADERS))
        self.tbl_stock.setHorizontalHeaderLabels(STK_HEADERS)
        self.tbl_stock.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_stock.setAlternatingRowColors(True); self.tbl_stock.verticalHeader().setVisible(False)
        self.tbl_stock.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_stock.setStyleSheet(TABLE_STYLE)
        stk_fl.addWidget(self.tbl_stock); stl.addWidget(stk_f)
        tabs.addTab(stk_tab, "Stock Report")

        # ── Cash Flow ─────────────────────────────────────────────────────────
        cf_tab = QWidget()
        cfl = QVBoxLayout(cf_tab); cfl.setContentsMargins(0,12,0,0); cfl.setSpacing(12)
        cfr, self._cf_df, self._cf_dt = _date_filter_row("_cf_df","_cf_dt", self._load_cashflow)
        cf_export = btn("Export CSV", INFO); cf_export.clicked.connect(lambda: self._export(self.tbl_cf,"cashflow"))
        cfr.addWidget(cf_export); cfl.addLayout(cfr)

        cfsf = QFrame(); cfsf.setStyleSheet("QFrame{background:#F0FDF4;border-radius:8px;}")
        cfsl = QHBoxLayout(cfsf); cfsl.setContentsMargins(16,8,16,8)
        self._cf_sum = QLabel(); self._cf_sum.setStyleSheet(f"font-size:13px;font-weight:600;color:{SUCCESS};")
        cfsl.addWidget(self._cf_sum); cfsl.addStretch(); cfl.addWidget(cfsf)

        cf_f = card_frame(); cf_fl = QVBoxLayout(cf_f); cf_fl.setContentsMargins(0,0,0,0)
        CF_HEADERS = ["#","Type","Party","Amount","Description","Date"]
        self.tbl_cf = QTableWidget(); self.tbl_cf.setColumnCount(len(CF_HEADERS))
        self.tbl_cf.setHorizontalHeaderLabels(CF_HEADERS)
        self.tbl_cf.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_cf.setAlternatingRowColors(True); self.tbl_cf.verticalHeader().setVisible(False)
        self.tbl_cf.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_cf.setStyleSheet(TABLE_STYLE)
        cf_fl.addWidget(self.tbl_cf); cfl.addWidget(cf_f)
        tabs.addTab(cf_tab, "Cash Flow")

        # ── Charts ─────────────────────────────────────────────────────────────
        self._build_charts_tab(tabs)

        # ── Summary Report ─────────────────────────────────────────────────────
        sum_tab = QWidget()
        suml = QVBoxLayout(sum_tab); suml.setContentsMargins(0, 12, 0, 0); suml.setSpacing(12)

        sum_inner = QTabWidget()
        sum_inner.setStyleSheet("""
            QTabWidget::pane { border: none; background: transparent; }
            QTabBar::tab {
                background: #F3F4F6; color: #374151; border-radius: 5px;
                padding: 5px 14px; font-size: 11px; margin-right: 3px;
            }
            QTabBar::tab:selected { background: #10B981; color: white; font-weight: 600; }
        """)

        PERIODS = [
            ("Daily",   "daily",   -30,  0),
            ("Weekly",  "weekly",  -3,   0),   # months offset
            ("Monthly", "monthly", -12,  0),
            ("Yearly",  "yearly",  -5,   0),
        ]
        self._sum_tabs = {}
        for label, key, months_back, _ in PERIODS:
            self._sum_tabs[key] = self._make_summary_sub_tab(sum_inner, label, key, months_back)

        suml.addWidget(sum_inner)
        tabs.addTab(sum_tab, "Summary")

        root.addWidget(tabs)

    def _make_summary_sub_tab(self, parent_tabs, label, period_key, months_back):
        tab = QWidget()
        lay = QVBoxLayout(tab); lay.setContentsMargins(0, 10, 0, 0); lay.setSpacing(10)

        if period_key == "yearly":
            default_from = QDate.currentDate().addYears(-5)
        elif period_key == "weekly":
            default_from = QDate.currentDate().addMonths(-3)
        elif period_key == "daily":
            default_from = QDate.currentDate().addDays(-30)
        else:
            default_from = QDate.currentDate().addMonths(-12)

        df_w = QDateEdit(default_from)
        dt_w = QDateEdit(QDate.currentDate())
        for d in [df_w, dt_w]:
            d.setStyleSheet(FIELD_STYLE); d.setCalendarPopup(True); d.setFixedWidth(115)

        sum_lbl = QLabel()
        sum_lbl.setStyleSheet("font-size:13px;font-weight:600;color:#10B981;")

        # table
        f = card_frame(); fl = QVBoxLayout(f); fl.setContentsMargins(0, 0, 0, 0)
        HEADERS = ["Period", "Sales", "Purchases", "Profit"]
        t = QTableWidget(); t.setColumnCount(len(HEADERS))
        t.setHorizontalHeaderLabels(HEADERS)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.setAlternatingRowColors(True); t.verticalHeader().setVisible(False)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        t.setStyleSheet(TABLE_STYLE)
        fl.addWidget(t)

        def _load(pk=period_key, dfw=df_w, dtw=dt_w, sl=sum_lbl, tbl=t):
            date_from = dfw.date().toString("yyyy-MM-dd")
            date_to   = dtw.date().toString("yyyy-MM-dd")
            rows = self.db.get_period_summary(pk, date_from, date_to)
            tbl.setRowCount(len(rows))
            tot_s = tot_p = 0.0
            for i, (period, data) in enumerate(rows):
                s = data["sales"]; p = data["purchases"]; prof = s - p
                tot_s += s; tot_p += p
                vals = [period, f"${s:,.2f}", f"${p:,.2f}", f"${prof:,.2f}"]
                for c, v in enumerate(vals):
                    item = QTableWidgetItem(v)
                    if c == 3:
                        item.setForeground(QColor(SUCCESS if prof >= 0 else DANGER))
                    tbl.setItem(i, c, item)
            tot_prof = tot_s - tot_p
            sl.setText(
                f"Periods: {len(rows)}  |  Sales: ${tot_s:,.2f}  |  "
                f"Purchases: ${tot_p:,.2f}  |  Profit: ${tot_prof:,.2f}"
            )

        df_w.dateChanged.connect(_load)
        dt_w.dateChanged.connect(_load)

        refresh_btn = btn("Refresh", PRIMARY); refresh_btn.clicked.connect(_load)
        export_btn  = btn("Export CSV", INFO)
        export_btn.clicked.connect(lambda: self._export(t, f"{period_key}_summary"))

        dr = QHBoxLayout(); dr.setSpacing(8)
        dr.addWidget(QLabel("From:")); dr.addWidget(df_w)
        dr.addWidget(QLabel("To:"));   dr.addWidget(dt_w)
        dr.addWidget(refresh_btn); dr.addWidget(export_btn); dr.addStretch()
        lay.addLayout(dr)

        sf = QFrame(); sf.setStyleSheet("QFrame{background:#ECFDF5;border-radius:8px;}")
        sl2 = QHBoxLayout(sf); sl2.setContentsMargins(16, 8, 16, 8)
        sl2.addWidget(sum_lbl); sl2.addStretch(); lay.addWidget(sf)
        lay.addWidget(f)

        tab._load_fn = _load
        parent_tabs.addTab(tab, label)
        return tab

    # ── Charts Tab ─────────────────────────────────────────────────────────────

    def _build_charts_tab(self, tabs):
        tab = QWidget()
        lay = QVBoxLayout(tab); lay.setContentsMargins(0, 12, 0, 0); lay.setSpacing(12)

        # ── controls bar ──
        ctrl = QFrame()
        ctrl.setStyleSheet("QFrame{background:white;border-radius:10px;}")
        cl = QHBoxLayout(ctrl); cl.setContentsMargins(16, 10, 16, 10); cl.setSpacing(10)

        def _lbl(text):
            l = QLabel(text)
            l.setStyleSheet(f"font-size:11px;font-weight:600;color:{_C_SUBTEXT};")
            return l

        # period combo
        self._ch_period = QComboBox()
        self._ch_period.addItems(["Daily", "Weekly", "Monthly", "Yearly"])
        self._ch_period.setCurrentIndex(2)          # Monthly default
        self._ch_period.setFixedWidth(110)
        self._ch_period.setStyleSheet(FIELD_STYLE)

        # chart type combo
        self._ch_type = QComboBox()
        self._ch_type.addItems([
            "Bar Chart", "Grouped Bar", "Line Chart",
            "Area Chart", "Pie Chart", "Donut Chart"
        ])
        self._ch_type.setFixedWidth(130)
        self._ch_type.setStyleSheet(FIELD_STYLE)

        # date pickers
        self._ch_df = QDateEdit(QDate.currentDate().addMonths(-6))
        self._ch_dt = QDateEdit(QDate.currentDate())
        for d in [self._ch_df, self._ch_dt]:
            d.setStyleSheet(FIELD_STYLE); d.setCalendarPopup(True); d.setFixedWidth(115)

        draw_btn = btn("Draw", PRIMARY)
        draw_btn.clicked.connect(self._draw_chart)

        cl.addWidget(_lbl("PERIOD"));     cl.addWidget(self._ch_period)
        cl.addWidget(_lbl("CHART TYPE")); cl.addWidget(self._ch_type)
        cl.addWidget(_lbl("FROM"));       cl.addWidget(self._ch_df)
        cl.addWidget(_lbl("TO"));         cl.addWidget(self._ch_dt)
        cl.addWidget(draw_btn); cl.addStretch()
        lay.addWidget(ctrl)

        # ── canvas ──
        canvas_frame = card_frame()
        cf_lay = QVBoxLayout(canvas_frame); cf_lay.setContentsMargins(16, 16, 16, 16)

        self._fig = Figure(figsize=(10, 5), facecolor=_C_BG, tight_layout=True)
        self._canvas = FigureCanvas(self._fig)
        self._canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._canvas.setMinimumHeight(360)
        cf_lay.addWidget(self._canvas)
        lay.addWidget(canvas_frame)

        tabs.addTab(tab, "Charts")

    def _draw_chart(self):
        period_map  = {0: "daily", 1: "weekly", 2: "monthly", 3: "yearly"}
        period_key  = period_map[self._ch_period.currentIndex()]
        chart_type  = self._ch_type.currentText()
        date_from   = self._ch_df.date().toString("yyyy-MM-dd")
        date_to     = self._ch_dt.date().toString("yyyy-MM-dd")

        rows = self.db.get_period_summary(period_key, date_from, date_to)
        self._fig.clear()

        if not rows:
            ax = self._fig.add_subplot(111)
            ax.text(0.5, 0.5, "No data for selected range",
                    ha="center", va="center", fontsize=14, color=_C_SUBTEXT,
                    transform=ax.transAxes)
            ax.axis("off")
            self._canvas.draw()
            return

        labels   = [r[0] for r in rows]
        sales    = np.array([r[1]["sales"]     for r in rows])
        purchases= np.array([r[1]["purchases"] for r in rows])
        profits  = sales - purchases
        x        = np.arange(len(labels))

        def _style_ax(ax, title=""):
            ax.set_facecolor(_C_BG)
            ax.spines[["top","right"]].set_visible(False)
            ax.spines[["left","bottom"]].set_color(_C_GRID)
            ax.tick_params(colors=_C_SUBTEXT, labelsize=9)
            ax.yaxis.grid(True, color=_C_GRID, linewidth=0.8, zorder=0)
            ax.set_axisbelow(True)
            if title:
                ax.set_title(title, color=_C_TEXT, fontsize=12, fontweight="bold", pad=10)

        def _fmt_labels(ax):
            if len(labels) > 20:
                ax.set_xticks(x[::max(1, len(labels)//10)])
                ax.set_xticklabels(labels[::max(1, len(labels)//10)],
                                   rotation=35, ha="right", fontsize=8)
            else:
                ax.set_xticks(x)
                ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=9)

        def _dollar_fmt(ax):
            import matplotlib.ticker as mtick
            ax.yaxis.set_major_formatter(mtick.FuncFormatter(
                lambda v, _: f"${v:,.0f}"
            ))

        # ── Bar Chart (Sales & Purchases side by side, Profit line) ──
        if chart_type == "Bar Chart":
            ax = self._fig.add_subplot(111)
            _style_ax(ax, f"{period_key.capitalize()} Sales vs Purchases")
            w = 0.35
            bars_s = ax.bar(x - w/2, sales,     w, label="Sales",     color=_C_SALES,     alpha=0.85, zorder=3)
            bars_p = ax.bar(x + w/2, purchases, w, label="Purchases", color=_C_PURCHASES, alpha=0.85, zorder=3)
            ax2 = ax.twinx()
            line_color = [(_C_PROFIT if p >= 0 else _C_LOSS) for p in profits]
            ax2.plot(x, profits, "o-", color=_C_PROFIT, linewidth=2, markersize=5,
                     label="Profit", zorder=4)
            ax2.axhline(0, color=_C_SUBTEXT, linewidth=0.8, linestyle="--")
            ax2.set_ylabel("Profit ($)", color=_C_PROFIT, fontsize=10)
            ax2.tick_params(axis="y", colors=_C_PROFIT, labelsize=9)
            ax2.spines[["top","right"]].set_visible(False)
            import matplotlib.ticker as mtick
            ax2.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v,_: f"${v:,.0f}"))
            _fmt_labels(ax); _dollar_fmt(ax)
            lines, line_lbl = ax2.get_legend_handles_labels()
            ax.legend(handles=ax.patches[:2] + lines,
                      labels=["Sales","Purchases","Profit"],
                      loc="upper left", fontsize=9, framealpha=0.8)

        # ── Grouped Bar (Sales / Purchases / Profit three bars) ──
        elif chart_type == "Grouped Bar":
            ax = self._fig.add_subplot(111)
            _style_ax(ax, f"{period_key.capitalize()} Sales / Purchases / Profit")
            w = 0.26
            ax.bar(x - w,   sales,     w, label="Sales",     color=_C_SALES,     alpha=0.85, zorder=3)
            ax.bar(x,       purchases, w, label="Purchases", color=_C_PURCHASES, alpha=0.85, zorder=3)
            profit_colors = [_C_PROFIT if p >= 0 else _C_LOSS for p in profits]
            for xi, pi, pc in zip(x + w, profits, profit_colors):
                ax.bar(xi, pi, w, color=pc, alpha=0.85, zorder=3)
            ax.axhline(0, color=_C_SUBTEXT, linewidth=0.8, linestyle="--")
            from matplotlib.patches import Patch
            legend_els = [
                Patch(color=_C_SALES, label="Sales"),
                Patch(color=_C_PURCHASES, label="Purchases"),
                Patch(color=_C_PROFIT, label="Profit (+)"),
                Patch(color=_C_LOSS, label="Loss (−)"),
            ]
            ax.legend(handles=legend_els, fontsize=9, framealpha=0.8)
            _fmt_labels(ax); _dollar_fmt(ax)

        # ── Line Chart ──
        elif chart_type == "Line Chart":
            ax = self._fig.add_subplot(111)
            _style_ax(ax, f"{period_key.capitalize()} Trend")
            ax.plot(x, sales,     "o-", color=_C_SALES,     linewidth=2.2, markersize=5, label="Sales",     zorder=3)
            ax.plot(x, purchases, "s-", color=_C_PURCHASES, linewidth=2.2, markersize=5, label="Purchases", zorder=3)
            ax.plot(x, profits,   "^-", color=_C_PROFIT,    linewidth=1.8, markersize=4,
                    linestyle="--", label="Profit", zorder=3)
            ax.axhline(0, color=_C_SUBTEXT, linewidth=0.8, linestyle=":")
            ax.fill_between(x, profits, 0,
                            where=(profits >= 0), alpha=0.08, color=_C_PROFIT)
            ax.fill_between(x, profits, 0,
                            where=(profits < 0),  alpha=0.08, color=_C_LOSS)
            ax.legend(fontsize=9, framealpha=0.8)
            _fmt_labels(ax); _dollar_fmt(ax)

        # ── Area Chart ──
        elif chart_type == "Area Chart":
            ax = self._fig.add_subplot(111)
            _style_ax(ax, f"{period_key.capitalize()} Area — Sales vs Purchases")
            ax.fill_between(x, sales,     alpha=0.30, color=_C_SALES,     zorder=2)
            ax.fill_between(x, purchases, alpha=0.30, color=_C_PURCHASES, zorder=2)
            ax.plot(x, sales,     color=_C_SALES,     linewidth=2, label="Sales",     zorder=3)
            ax.plot(x, purchases, color=_C_PURCHASES, linewidth=2, label="Purchases", zorder=3)
            ax.legend(fontsize=9, framealpha=0.8)
            _fmt_labels(ax); _dollar_fmt(ax)

        # ── Pie Chart ──
        elif chart_type == "Pie Chart":
            tot_s = float(sales.sum()); tot_p = float(purchases.sum())
            if tot_s + tot_p == 0:
                ax = self._fig.add_subplot(111)
                ax.text(0.5, 0.5, "No data", ha="center", va="center"); ax.axis("off")
            else:
                ax = self._fig.add_subplot(111)
                ax.set_facecolor(_C_BG)
                sizes  = [tot_s, tot_p]
                colors = [_C_SALES, _C_PURCHASES]
                explode= (0.04, 0.04)
                wedges, texts, autotexts = ax.pie(
                    sizes, labels=["Sales", "Purchases"],
                    colors=colors, explode=explode,
                    autopct="%1.1f%%", startangle=140,
                    pctdistance=0.75,
                    wedgeprops=dict(linewidth=1.5, edgecolor="white")
                )
                for t in texts:     t.set_color(_C_TEXT); t.set_fontsize(11)
                for at in autotexts: at.set_color("white"); at.set_fontsize(10); at.set_fontweight("bold")
                tot = tot_s + tot_p
                ax.set_title(
                    f"Total Sales: ${tot_s:,.0f}   |   Total Purchases: ${tot_p:,.0f}",
                    color=_C_TEXT, fontsize=11, fontweight="bold"
                )

        # ── Donut Chart ──
        elif chart_type == "Donut Chart":
            tot_s = float(sales.sum()); tot_p = float(purchases.sum())
            tot_prof = tot_s - tot_p
            if tot_s + tot_p == 0:
                ax = self._fig.add_subplot(111)
                ax.text(0.5, 0.5, "No data", ha="center", va="center"); ax.axis("off")
            else:
                # outer ring: sales vs purchases
                # inner ring: profit vs cost
                fig = self._fig
                ax = fig.add_subplot(111)
                ax.set_facecolor(_C_BG)

                outer_sizes  = [tot_s, tot_p]
                outer_colors = [_C_SALES, _C_PURCHASES]
                inner_sizes  = [max(tot_prof, 0), abs(min(tot_prof, 0)), min(tot_s, tot_p)]
                inner_colors = [_C_PROFIT, _C_LOSS, "#E5E7EB"]
                # clean zeros
                outer_pairs = [(s, c) for s, c in zip(outer_sizes, outer_colors) if s > 0]
                inner_pairs = [(s, c) for s, c in zip(inner_sizes, inner_colors) if s > 0]
                if outer_pairs:
                    os_, oc_ = zip(*outer_pairs)
                    ax.pie(os_, colors=oc_, radius=1.0, startangle=140,
                           wedgeprops=dict(width=0.38, edgecolor="white", linewidth=2))
                if inner_pairs:
                    is_, ic_ = zip(*inner_pairs)
                    ax.pie(is_, colors=ic_, radius=0.60, startangle=140,
                           wedgeprops=dict(width=0.38, edgecolor="white", linewidth=2))

                pc = _C_PROFIT if tot_prof >= 0 else _C_LOSS
                ax.text(0, 0, f"Profit\n${tot_prof:,.0f}",
                        ha="center", va="center", fontsize=11, fontweight="bold", color=pc)

                from matplotlib.patches import Patch
                legend_els = [
                    Patch(color=_C_SALES,     label=f"Sales ${tot_s:,.0f}"),
                    Patch(color=_C_PURCHASES, label=f"Purchases ${tot_p:,.0f}"),
                    Patch(color=_C_PROFIT,    label=f"Profit ${max(tot_prof,0):,.0f}"),
                    Patch(color=_C_LOSS,      label=f"Loss ${abs(min(tot_prof,0)):,.0f}"),
                ]
                ax.legend(handles=legend_els, loc="lower right", fontsize=9, framealpha=0.8)
                ax.set_title(f"{period_key.capitalize()} Sales vs Purchases",
                             color=_C_TEXT, fontsize=12, fontweight="bold")

        self._fig.patch.set_facecolor(_C_BG)
        self._canvas.draw()

    def _make_report_tab(self, tabs, tab_title, headers, tbl_attr, df_attr, dt_attr,
                          load_fn, summary_attr=None):
        tab = QWidget()
        layout = QVBoxLayout(tab); layout.setContentsMargins(0,12,0,0); layout.setSpacing(12)
        dr, df, dt = _date_filter_row(df_attr, dt_attr, load_fn)
        setattr(self, df_attr, df); setattr(self, dt_attr, dt)
        refresh = btn("Refresh", PRIMARY); refresh.clicked.connect(load_fn)
        export  = btn("Export CSV", INFO)
        tbl_ref = [None]
        export.clicked.connect(lambda: self._export(tbl_ref[0], tab_title.lower().replace(" ","_")))
        dr.addWidget(refresh); dr.addWidget(export); layout.addLayout(dr)

        if summary_attr:
            sf = QFrame(); sf.setStyleSheet("QFrame{background:#EEF2FF;border-radius:8px;}")
            sl = QHBoxLayout(sf); sl.setContentsMargins(16,8,16,8)
            sum_lbl = QLabel(); sum_lbl.setStyleSheet(f"font-size:13px;font-weight:600;color:{PRIMARY};")
            sl.addWidget(sum_lbl); sl.addStretch(); layout.addWidget(sf)
            setattr(self, summary_attr, sum_lbl)

        f = card_frame(); fl = QVBoxLayout(f); fl.setContentsMargins(0,0,0,0)
        t = QTableWidget(); t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.setAlternatingRowColors(True); t.verticalHeader().setVisible(False)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        t.setStyleSheet(TABLE_STYLE)
        setattr(self, tbl_attr, t); tbl_ref[0] = t
        fl.addWidget(t); layout.addWidget(f)
        tabs.addTab(tab, tab_title)
        return tab

    def refresh(self):
        self._load_sales(); self._load_purchases(); self._load_pl()
        self._load_stock(); self._load_cashflow()
        for tab in self._sum_tabs.values():
            tab._load_fn()
        self._draw_chart()

    def _load_sales(self):
        df = self._sr_df.date().toString("yyyy-MM-dd")
        dt = self._sr_dt.date().toString("yyyy-MM-dd")
        rows = self.db.get_sales_report(df, dt)
        self._tbl_sales.setRowCount(len(rows))
        total = sum(r["total"] for r in rows)
        paid  = sum(r["paid_amount"] for r in rows)
        due   = sum(r["due_amount"] for r in rows)
        self._sr_sum.setText(f"Records: {len(rows)}  |  Revenue: ${total:,.2f}  |  Collected: ${paid:,.2f}  |  Due: ${due:,.2f}")
        SC = {"paid":SUCCESS,"partial":WARNING,"unpaid":DANGER}
        for i, r in enumerate(rows):
            vals = [r["invoice_no"], r["customer"], r["sale_date"],
                    f"${r['subtotal']:.2f}", f"${r['discount']:.2f}", f"${r['tax_amount']:.2f}",
                    f"${r['total']:.2f}", f"${r['paid_amount']:.2f}", f"${r['due_amount']:.2f}", r["status"]]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if c == 9: item.setForeground(QColor(SC.get(v, TEXT_MID)))
                self._tbl_sales.setItem(i, c, item)

    def _load_purchases(self):
        df = self._pr_df.date().toString("yyyy-MM-dd")
        dt = self._pr_dt.date().toString("yyyy-MM-dd")
        rows = self.db.get_purchase_report(df, dt)
        self._tbl_pur.setRowCount(len(rows))
        total = sum(r["total"] for r in rows)
        paid  = sum(r["paid_amount"] for r in rows)
        due   = sum(r["due_amount"] for r in rows)
        self._pr_sum.setText(f"Records: {len(rows)}  |  Total: ${total:,.2f}  |  Paid: ${paid:,.2f}  |  Due: ${due:,.2f}")
        SC = {"paid":SUCCESS,"partial":WARNING,"unpaid":DANGER}
        for i, r in enumerate(rows):
            vals = [r["po_number"], r["supplier"], r["purchase_date"],
                    f"${r['subtotal']:.2f}", f"${r['discount']:.2f}", f"${r['tax_amount']:.2f}",
                    f"${r['total']:.2f}", f"${r['paid_amount']:.2f}", f"${r['due_amount']:.2f}", r["status"]]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if c == 9: item.setForeground(QColor(SC.get(v, TEXT_MID)))
                self._tbl_pur.setItem(i, c, item)

    def _load_pl(self):
        df = self._pl_df.date().toString("yyyy-MM-dd")
        dt = self._pl_dt.date().toString("yyyy-MM-dd")
        pl = self.db.get_profit_loss(df, dt)
        rev = pl["revenue"]; pur = pl["purchases"]; profit = pl["profit"]
        cogs = pl["cogs"]; gross_profit = pl["gross_profit"]
        margin = (profit / rev * 100) if rev > 0 else 0
        gp_margin = (gross_profit / rev * 100) if rev > 0 else 0
        self._pl_rev.setText(f"${rev:,.2f}")
        self._pl_pur.setText(f"${pur:,.2f}")
        self._pl_prof.setText(f"${profit:,.2f}")
        self._pl_prof.setStyleSheet(f"font-size:24px;font-weight:700;color:{SUCCESS if profit>=0 else DANGER};background:transparent;border:none;")
        self._pl_gp.setText(f"${gross_profit:,.2f}")
        self._pl_gp.setStyleSheet(f"font-size:24px;font-weight:700;color:{SUCCESS if gross_profit>=0 else DANGER};background:transparent;border:none;")
        self._pl_marg.setText(f"{margin:.1f}%")
        rows = [
            ("Revenue",               rev,          100.0),
            ("Cost of Purchases",     pur,          (pur/rev*100) if rev > 0 else 0),
            ("Gross Profit",          profit,       margin),
            ("",                      "",           ""),
            ("Cost of Goods Sold",    cogs,         (cogs/rev*100) if rev > 0 else 0),
            ("Profit or Loss",   gross_profit, gp_margin),
            ("Cash Balance",          self.db.get_cash_balance(), ""),
        ]
        for i, (desc, amt, pct) in enumerate(rows):
            d_item = QTableWidgetItem(str(desc))
            a_item = QTableWidgetItem(f"${amt:,.2f}" if isinstance(amt, float) else "")
            p_item = QTableWidgetItem(f"{pct:.1f}%" if isinstance(pct, float) else "")
            if desc == "Gross Profit / Loss" and isinstance(amt, float):
                color = QColor(SUCCESS if amt >= 0 else DANGER)
                for it in (d_item, a_item, p_item):
                    it.setForeground(color)
                    it.setFont(QFont("", -1, QFont.Weight.Bold))
            self.tbl_pl.setItem(i, 0, d_item)
            self.tbl_pl.setItem(i, 1, a_item)
            self.tbl_pl.setItem(i, 2, p_item)

    def _load_stock(self):
        rows = self.db.get_stock_summary()
        self.tbl_stock.setRowCount(len(rows))
        total_val = sum(r["stock_value"] for r in rows)
        low = sum(1 for r in rows if r["stock_status"] == "Low Stock")
        out = sum(1 for r in rows if r["stock_status"] == "Out of Stock")
        self._stk_sum.setText(f"Products: {len(rows)}  |  Low Stock: {low}  |  Out of Stock: {out}  |  Total Value: ${total_val:,.2f}")
        SC = {"In Stock": SUCCESS, "Low Stock": WARNING, "Out of Stock": DANGER}
        for i, r in enumerate(rows):
            vals = [r["name"], r["sku"] or "—", r["category"] or "—", r["unit"],
                    str(r["quantity"]), str(r["min_stock"]),
                    f"${r['cost_price']:.2f}", f"${r['sale_price']:.2f}",
                    f"${r['stock_value']:.2f}", r["stock_status"]]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if c == 9:
                    item.setForeground(QColor(SC.get(v, TEXT_MID)))
                    item.setFont(QFont("", -1, QFont.Weight.Bold))
                self.tbl_stock.setItem(i, c, item)

    def _load_cashflow(self):
        df = self._cf_df.date().toString("yyyy-MM-dd")
        dt = self._cf_dt.date().toString("yyyy-MM-dd")
        rows = self.db.get_cash_transactions(date_from=df, date_to=dt)
        self.tbl_cf.setRowCount(len(rows))
        in_amt  = sum(r["amount"] for r in rows if r["type"] in ("COLLECTION","INCOME"))
        out_amt = sum(r["amount"] for r in rows if r["type"] in ("DELIVERY","EXPENSE"))
        self._cf_sum.setText(
            f"Records: {len(rows)}  |  Cash In: ${in_amt:,.2f}  |  Cash Out: ${out_amt:,.2f}  |  Net Flow: ${in_amt-out_amt:,.2f}"
        )
        TC = {"COLLECTION":SUCCESS,"INCOME":SUCCESS,"DELIVERY":DANGER,"EXPENSE":DANGER}
        for i, r in enumerate(rows):
            vals = [str(r["id"]), r["type"], r["party_name"] or "—",
                    f"${r['amount']:,.2f}", r["description"] or "—", r["created_at"][:16]]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if c == 1: item.setForeground(QColor(TC.get(v, TEXT_MID)))
                if c == 3: item.setForeground(QColor(TC.get(r["type"], TEXT_MID)))
                self.tbl_cf.setItem(i, c, item)

    def _export(self, table, filename):
        if not table: return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", f"{filename}.csv", "CSV Files (*.csv)"
        )
        if not path: return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                headers = [table.horizontalHeaderItem(c).text()
                           for c in range(table.columnCount())]
                writer.writerow(headers)
                for r in range(table.rowCount()):
                    row = []
                    for c in range(table.columnCount()):
                        item = table.item(r, c)
                        row.append(item.text() if item else "")
                    writer.writerow(row)
            QMessageBox.information(self, "Exported", f"Saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))
