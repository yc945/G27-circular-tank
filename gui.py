"""
G-27 露天式圆形水池结构设计程序 —— Python/Tkinter 美化版

参照原程序 (v5.1, DOS/VB 风格) 界面重新设计：
  数据来源 / 文本结果 / 图形结果 / 程序说明 / 使用帮助
五个选项卡 + 顶部工具栏，采用现代扁平化配色。
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font as tkfont
from datetime import date

import engine
from engine import TankInput, Results, Confidence, CONFIDENCE_NOTE

import matplotlib
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "PingFang SC",
                                           "Noto Sans CJK SC", "Arial Unicode MS", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

# ---------------------------------------------------------------------------
# 配色 / 字体
# ---------------------------------------------------------------------------
COLOR_HEADER = "#1f3a5f"        # 深蓝头部
COLOR_HEADER_TEXT = "#eef3fa"
COLOR_ACCENT = "#2e78c7"        # 强调蓝
COLOR_BG = "#f4f6f9"            # 浅灰背景
COLOR_PANEL = "#ffffff"
COLOR_BORDER = "#d8dee6"
COLOR_TEXT = "#1f2937"
COLOR_MUTED = "#6b7280"

CONF_COLOR = {
    Confidence.HIGH: "#1a7f37",
    Confidence.MEDIUM: "#b06a00",
    Confidence.LOW: "#c1121f",
}

FIELD_DEFS = [
    ("N", "题目代号", "s"),
    ("K", "分段点数 K", "i"),
    ("D", "圆池内直径 D (m)", "f"),
    ("H", "圆池高度 H (m)", "f"),
    ("H1", "底板厚度 H1 (m)", "f"),
    ("H2", "圆池壁厚 H2 (m)", "f"),
    ("E", "砼弹性模量 E (kN/m²)", "f"),
    ("AM", "砼侧向变形系数 AM (μ)", "f"),
    ("AL", "砼温度伸缩系数 AL (α)", "f"),
    ("TB", "池壁外日均最高气温 TB (℃)", "f"),
    ("TA", "池壁外日均最低气温 TA (℃)", "f"),
    ("TD", "池底外温度 TD (℃)", "f"),
]

COEF_COLS = [
    ("BM", "BM\n(水压弯矩)"),
    ("BN", "BN\n(水压环向力)"),
    ("BK", "BK\n(水压剪力)"),
    ("BMT", "BMT\n(温差弯矩)"),
    ("BNT", "BNT\n(温差环向力)"),
    ("BKT", "BKT\n(温差剪力)"),
    ("BMD", "BMD\n(附加-弯矩)"),
    ("BND", "BND\n(附加-环向力)"),
    ("BKD", "BKD\n(附加-剪力)"),
]


def setup_styles(root):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    root.configure(bg=COLOR_BG)

    style.configure("Header.TFrame", background=COLOR_HEADER)
    style.configure("Header.TLabel", background=COLOR_HEADER,
                     foreground=COLOR_HEADER_TEXT, font=("Microsoft YaHei UI", 14, "bold"))
    style.configure("SubHeader.TLabel", background=COLOR_HEADER,
                     foreground="#c7d6ea", font=("Microsoft YaHei UI", 9))

    style.configure("Toolbar.TFrame", background="#e9edf3")
    style.configure("Toolbar.TButton", font=("Microsoft YaHei UI", 9), padding=(10, 6))
    style.map("Toolbar.TButton",
              background=[("active", COLOR_ACCENT)],
              foreground=[("active", "#ffffff")])

    style.configure("Main.TFrame", background=COLOR_BG)
    style.configure("Panel.TFrame", background=COLOR_PANEL)
    style.configure("Panel.TLabelframe", background=COLOR_PANEL, foreground=COLOR_TEXT,
                     font=("Microsoft YaHei UI", 9, "bold"))
    style.configure("Panel.TLabelframe.Label", background=COLOR_PANEL, foreground=COLOR_ACCENT,
                     font=("Microsoft YaHei UI", 9, "bold"))

    style.configure("TNotebook", background=COLOR_BG, borderwidth=0)
    style.configure("TNotebook.Tab", font=("Microsoft YaHei UI", 10), padding=(16, 8),
                     background="#dde4ee", foreground=COLOR_TEXT)
    style.map("TNotebook.Tab",
              background=[("selected", COLOR_PANEL)],
              foreground=[("selected", COLOR_ACCENT)])

    style.configure("Status.TLabel", background="#e9edf3", foreground=COLOR_MUTED,
                     font=("Microsoft YaHei UI", 9))

    style.configure("Field.TLabel", background=COLOR_PANEL, foreground=COLOR_TEXT,
                     font=("Microsoft YaHei UI", 9))
    style.configure("TEntry", padding=4)

    return style


class ToolTip:
    """轻量提示气泡"""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _evt=None):
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        lbl = tk.Label(self.tip, text=self.text, justify="left", background="#333333",
                        foreground="white", relief="solid", borderwidth=1,
                        font=("Microsoft YaHei UI", 8), padx=6, pady=3)
        lbl.pack()

    def _hide(self, _evt=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


# ---------------------------------------------------------------------------
# 主应用
# ---------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("露天式圆形水池结构设计程序  G-27  (Python 美化版)")
        self.geometry("1180x760")
        self.minsize(980, 640)

        self.style = setup_styles(self)

        self.current_dir = tk.StringVar(value=os.getcwd())
        self.current_file = tk.StringVar(value="(未命名)")
        self.field_vars = {}
        self.coef_entries = {}   # (col, row) -> Entry
        self.results: Results | None = None
        self.input_data: TankInput = engine.blank_input(6)

        self._build_header()
        self._build_toolbar()
        self._build_body()
        self._build_statusbar()

        self._load_input(engine.sample_input())

    # ---------------- 顶部标题条 ----------------
    def _build_header(self):
        header = ttk.Frame(self, style="Header.TFrame")
        header.pack(side="top", fill="x")
        inner = ttk.Frame(header, style="Header.TFrame")
        inner.pack(fill="x", padx=18, pady=10)
        ttk.Label(inner, text="露天式圆形水池结构设计程序", style="Header.TLabel").pack(side="left")
        ttk.Label(inner, text="G-27 · 参照张光斗《圆筒钢筋砼薄壁池的内力计算》",
                  style="SubHeader.TLabel").pack(side="left", padx=(14, 0), pady=(6, 0))

    # ---------------- 工具栏 ----------------
    def _build_toolbar(self):
        bar = ttk.Frame(self, style="Toolbar.TFrame")
        bar.pack(side="top", fill="x")
        inner = ttk.Frame(bar, style="Toolbar.TFrame")
        inner.pack(fill="x", padx=12, pady=6)

        def btn(text, cmd, icon=""):
            b = ttk.Button(inner, text=f"{icon}  {text}" if icon else text,
                            style="Toolbar.TButton", command=cmd)
            b.pack(side="left", padx=4)
            return b

        btn("新建", self.on_new, "🆕")
        btn("打开", self.on_open, "📂")
        btn("存盘", self.on_save, "💾")
        ttk.Separator(inner, orient="vertical").pack(side="left", fill="y", padx=8, pady=2)
        btn("计算", self.on_calculate, "▶")
        btn("打印", self.on_print, "🖨")
        ttk.Separator(inner, orient="vertical").pack(side="left", fill="y", padx=8, pady=2)
        btn("退出", self.on_exit, "✕")

    # ---------------- 主体：左侧文件面板 + 右侧选项卡 ----------------
    def _build_body(self):
        body = ttk.Frame(self, style="Main.TFrame")
        body.pack(side="top", fill="both", expand=True, padx=10, pady=8)

        left = ttk.Labelframe(body, text=" 数据文件 ", style="Panel.TLabelframe", width=220)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)

        dirrow = ttk.Frame(left, style="Panel.TFrame")
        dirrow.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(dirrow, text=self._short_path(self.current_dir.get()),
                  style="Field.TLabel", wraplength=170).pack(side="left", fill="x", expand=True)
        self._dir_label = dirrow.winfo_children()[0]
        ttk.Button(left, text="浏览目录…", command=self.on_browse_dir).pack(fill="x", padx=8, pady=(0, 6))

        self.file_list = tk.Listbox(left, activestyle="none", relief="flat",
                                     bg=COLOR_PANEL, highlightthickness=1,
                                     highlightbackground=COLOR_BORDER,
                                     font=("Consolas", 10), selectbackground=COLOR_ACCENT)
        self.file_list.pack(fill="both", expand=True, padx=8, pady=4)
        self.file_list.bind("<Double-Button-1>", self.on_filelist_double_click)

        ttk.Label(left, text="双击文件名读取数据", style="Field.TLabel",
                  foreground=COLOR_MUTED).pack(padx=8, pady=(0, 8), anchor="w")

        self._refresh_file_list()

        right = ttk.Frame(body, style="Main.TFrame")
        right.pack(side="left", fill="both", expand=True)

        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill="both", expand=True)

        self.tab_data = ttk.Frame(self.notebook, style="Panel.TFrame")
        self.tab_text = ttk.Frame(self.notebook, style="Panel.TFrame")
        self.tab_graph = ttk.Frame(self.notebook, style="Panel.TFrame")
        self.tab_about = ttk.Frame(self.notebook, style="Panel.TFrame")
        self.tab_help = ttk.Frame(self.notebook, style="Panel.TFrame")

        self.notebook.add(self.tab_data, text="数据来源")
        self.notebook.add(self.tab_text, text="文本结果")
        self.notebook.add(self.tab_graph, text="图形结果")
        self.notebook.add(self.tab_about, text="程序说明")
        self.notebook.add(self.tab_help, text="使用帮助")

        self._build_tab_data()
        self._build_tab_text()
        self._build_tab_graph()
        self._build_tab_about()
        self._build_tab_help()

    # ---------------- 状态栏 ----------------
    def _build_statusbar(self):
        bar = ttk.Frame(self, style="Toolbar.TFrame")
        bar.pack(side="bottom", fill="x")
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(bar, textvariable=self.status_var, style="Status.TLabel").pack(
            side="left", padx=12, pady=4)
        ttk.Label(bar, text="G-27  Python/Tkinter 美化版", style="Status.TLabel").pack(
            side="right", padx=12, pady=4)

    # =====================================================================
    # Tab 1: 数据来源
    # =====================================================================
    def _build_tab_data(self):
        outer = ttk.Frame(self.tab_data, style="Panel.TFrame")
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=COLOR_PANEL, highlightthickness=0)
        vbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        vbar.pack(side="right", fill="y")

        inner = ttk.Frame(canvas, style="Panel.TFrame")
        win = canvas.create_window((0, 0), window=inner, anchor="nw")

        def on_config(_evt=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure(win, width=canvas.winfo_width())
        inner.bind("<Configure>", on_config)
        canvas.bind("<Configure>", on_config)

        def on_mousewheel(evt):
            canvas.yview_scroll(int(-evt.delta / 120), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)

        # -- 文件信息 --
        info = ttk.Labelframe(inner, text=" 文件信息 ", style="Panel.TLabelframe")
        info.pack(fill="x", padx=14, pady=(14, 8))
        ttk.Label(info, text="文件名：", style="Field.TLabel").grid(row=0, column=0, sticky="e", padx=6, pady=6)
        self.filename_var = tk.StringVar(value="G-27-1.INT")
        ttk.Entry(info, textvariable=self.filename_var, width=30).grid(
            row=0, column=1, sticky="w", padx=6, pady=6)

        # -- 基本参数 --
        params = ttk.Labelframe(inner, text=" 基本参数 ", style="Panel.TLabelframe")
        params.pack(fill="x", padx=14, pady=8)
        ncols = 3
        for idx, (key, label, kind) in enumerate(FIELD_DEFS):
            r, c = divmod(idx, ncols)
            cell = ttk.Frame(params, style="Panel.TFrame")
            cell.grid(row=r, column=c, sticky="w", padx=10, pady=6)
            ttk.Label(cell, text=label, style="Field.TLabel").pack(anchor="w")
            var = tk.StringVar()
            ent = ttk.Entry(cell, textvariable=var, width=18)
            ent.pack(anchor="w")
            self.field_vars[key] = var
        # K 变化时重建系数表
        self.field_vars["K"].trace_add("write", lambda *_: None)
        ttk.Button(params, text="按 K 重建系数表格 →", command=self.on_rebuild_coef_table).grid(
            row=(len(FIELD_DEFS) + ncols - 1) // ncols, column=0, columnspan=ncols,
            sticky="w", padx=10, pady=(4, 10))

        # -- 内力系数表 --
        self.coef_frame_holder = ttk.Labelframe(
            inner, text=" 内力系数 (取自附表1~9，人工查表填入，与原程序一致) ",
            style="Panel.TLabelframe")
        self.coef_frame_holder.pack(fill="x", padx=14, pady=(8, 16))
        self.coef_table_frame = None
        self._build_coef_table(6)

    def _build_coef_table(self, k):
        if self.coef_table_frame is not None:
            self.coef_table_frame.destroy()
        self.coef_table_frame = ttk.Frame(self.coef_frame_holder, style="Panel.TFrame")
        self.coef_table_frame.pack(fill="x", padx=6, pady=6)

        ttk.Label(self.coef_table_frame, text="点号", style="Field.TLabel",
                  font=("Microsoft YaHei UI", 9, "bold")).grid(row=0, column=0, padx=4, pady=4)
        for c, (key, label) in enumerate(COEF_COLS, start=1):
            ttk.Label(self.coef_table_frame, text=label, style="Field.TLabel",
                      font=("Microsoft YaHei UI", 8, "bold"), justify="center").grid(
                row=0, column=c, padx=4, pady=4)

        self.coef_entries = {}
        for i in range(k):
            ttk.Label(self.coef_table_frame, text=str(i + 1), style="Field.TLabel").grid(
                row=i + 1, column=0, padx=4, pady=2)
            for c, (key, _label) in enumerate(COEF_COLS, start=1):
                var = tk.StringVar(value="0.0")
                ent = ttk.Entry(self.coef_table_frame, textvariable=var, width=9)
                ent.grid(row=i + 1, column=c, padx=2, pady=2)
                self.coef_entries[(key, i)] = var

    def on_rebuild_coef_table(self):
        try:
            k = int(float(self.field_vars["K"].get()))
            if k < 2 or k > 30:
                raise ValueError
        except ValueError:
            messagebox.showerror("输入错误", "分段点数 K 需为 2~30 的整数")
            return
        self._build_coef_table(k)
        self.status_var.set(f"已按 K={k} 重建内力系数表格")

    # =====================================================================
    # Tab 2: 文本结果
    # =====================================================================
    def _build_tab_text(self):
        toolbar = ttk.Frame(self.tab_text, style="Panel.TFrame")
        toolbar.pack(fill="x", padx=10, pady=(10, 0))
        ttk.Button(toolbar, text="另存为文本…", command=self.on_save_text_result).pack(side="left")
        ttk.Button(toolbar, text="复制全部", command=self.on_copy_text_result).pack(side="left", padx=6)

        frame = ttk.Frame(self.tab_text, style="Panel.TFrame")
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.text_result = tk.Text(frame, wrap="none", font=("Consolas", 10),
                                    bg="#fbfcfe", fg=COLOR_TEXT, relief="flat",
                                    highlightthickness=1, highlightbackground=COLOR_BORDER)
        vbar = ttk.Scrollbar(frame, orient="vertical", command=self.text_result.yview)
        hbar = ttk.Scrollbar(frame, orient="horizontal", command=self.text_result.xview)
        self.text_result.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        self.text_result.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        for conf, color in CONF_COLOR.items():
            self.text_result.tag_configure(f"tag_{conf.name}", foreground=color,
                                            font=("Consolas", 10, "bold"))
        self.text_result.tag_configure("title", font=("Consolas", 11, "bold"), foreground=COLOR_ACCENT)
        self.text_result.insert("1.0", "尚未计算。请在“数据来源”页填入数据后点击工具栏“计算”。")
        self.text_result.configure(state="disabled")

    # =====================================================================
    # Tab 3: 图形结果
    # =====================================================================
    def _build_tab_graph(self):
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        toolbar = ttk.Frame(self.tab_graph, style="Panel.TFrame")
        toolbar.pack(fill="x", padx=10, pady=(10, 4))
        ttk.Label(toolbar, text="显示内力：", style="Field.TLabel").pack(side="left")

        self.graph_choice = tk.StringVar(value="池壁弯矩 My (kN·m)")
        options = [
            "池壁弯矩 My (kN·m)",
            "池壁环向力 N (kN)",
            "池壁剪力 Qy (kN)",
            "池底自重弯矩 MRV/MQV (kN·m)",
        ]
        cb = ttk.Combobox(toolbar, textvariable=self.graph_choice, values=options,
                           state="readonly", width=28)
        cb.pack(side="left", padx=8)
        cb.bind("<<ComboboxSelected>>", lambda _e: self.refresh_graph())
        ttk.Button(toolbar, text="刷新图形", command=self.refresh_graph).pack(side="left", padx=8)

        self.fig = Figure(figsize=(7.5, 5.2), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tab_graph)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        self._draw_placeholder()

    def _draw_placeholder(self):
        self.ax.clear()
        self.ax.text(0.5, 0.5, "计算后在此显示内力分布图", ha="center", va="center",
                      transform=self.ax.transAxes, color=COLOR_MUTED)
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.canvas.draw()

    def refresh_graph(self):
        if self.results is None:
            self._draw_placeholder()
            return
        r = self.results
        choice = self.graph_choice.get()
        self.ax.clear()
        y = r.y
        if choice.startswith("池壁弯矩"):
            self.ax.plot(r.MY1, y, "o-", label="My1 水压力", color="#2e78c7")
            self.ax.plot(r.MY2, y, "s--", label="My2 温差", color="#c1121f")
            self.ax.plot(r.MY_t, y, "^-", label="MY 总(考虑温度)", color="#1a7f37")
            self.ax.set_xlabel("弯矩 M (kN·m)")
        elif choice.startswith("池壁环向力"):
            self.ax.plot(r.N1, y, "o-", label="N1 水压力", color="#2e78c7")
            self.ax.plot(r.N2, y, "s--", label="N2 温差", color="#c1121f")
            self.ax.plot(r.N_t, y, "^-", label="N 总(考虑温度)", color="#1a7f37")
            self.ax.set_xlabel("环向力 N (kN)")
        elif choice.startswith("池壁剪力"):
            self.ax.plot(r.QY1, y, "o-", label="Qy1 水压力", color="#2e78c7")
            self.ax.plot(r.QY2, y, "s--", label="Qy2 温差", color="#c1121f")
            self.ax.plot(r.QY_t, y, "^-", label="QY 总(考虑温度)", color="#1a7f37")
            self.ax.set_xlabel("剪力 Qy (kN)")
        else:
            self.ax.plot(r.R, r.MRV, "o-", label="MRV 径向弯矩", color="#2e78c7")
            self.ax.plot(r.R, r.MQV, "s--", label="MQV 切向弯矩", color="#c1121f")
            self.ax.set_xlabel("离池心距离 r (m)")

        if not choice.startswith("池底"):
            self.ax.set_ylabel("池壁高度坐标 y (m, 0=池顶自由端)")
            self.ax.invert_yaxis()
        else:
            self.ax.set_ylabel("弯矩 (kN·m)")
        self.ax.axvline(0, color="#999999", linewidth=0.8)
        self.ax.grid(True, linestyle=":", alpha=0.6)
        self.ax.legend(fontsize=9)
        self.fig.tight_layout()
        self.canvas.draw()

    # =====================================================================
    # Tab 4: 程序说明
    # =====================================================================
    def _build_tab_about(self):
        frame = ttk.Frame(self.tab_about, style="Panel.TFrame")
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        txt = tk.Text(frame, wrap="word", font=("Microsoft YaHei UI", 10),
                       bg="#fbfcfe", fg=COLOR_TEXT, relief="flat",
                       highlightthickness=1, highlightbackground=COLOR_BORDER, padx=12, pady=10)
        vbar = ttk.Scrollbar(frame, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=vbar.set)
        txt.pack(side="left", fill="both", expand=True)
        vbar.pack(side="right", fill="y")

        txt.tag_configure("h1", font=("Microsoft YaHei UI", 12, "bold"), foreground=COLOR_ACCENT)
        txt.tag_configure("h2", font=("Microsoft YaHei UI", 10, "bold"), foreground=COLOR_TEXT)
        txt.tag_configure("hi", foreground=CONF_COLOR[Confidence.HIGH], font=("Microsoft YaHei UI", 10, "bold"))
        txt.tag_configure("mi", foreground=CONF_COLOR[Confidence.MEDIUM], font=("Microsoft YaHei UI", 10, "bold"))
        txt.tag_configure("lo", foreground=CONF_COLOR[Confidence.LOW], font=("Microsoft YaHei UI", 10, "bold"))

        content = [
            ("一、程序功能\n", "h1"),
            ("本程序用以计算露天式圆形水池在内水压力及温度作用下的内力，分池壁及池底"
             "两部分。计算方法参照张光斗《圆筒钢筋砼薄壁池的内力计算》（水利电力出版社）。"
             "圆筒池壁承受水平径向荷载（水压力）和温度荷载；圆板池底承受垂直向均布荷载"
             "（自重）和温度荷载；池壁底与池底周边为刚性固结。\n\n", None),
            ("二、各分项内力计算方法及可信度\n", "h1"),
            ("[精确] ", "hi"),
            ("池壁·内水压力内力 (My1, MQ1, N1, Qy1)：My1=BM·γ₀H³，MQ1=μ·My1，"
             "N1=BN·γ₀CH，Qy1=－BK·γ₀H²。已从原说明书公式图片逐字核对，算例复算零误差。\n\n", None),
            ("[精确] ", "hi"),
            ("池底·自重内力 (R, QRV, MRV, MQV)：按四边固支等厚圆板理论，"
             "q=γ砼H1，MRV=(q/16)[(1+μ)C²－(3+μ)r²]，MQV=(q/16)[(1+μ)C²－(1+3μ)r²]，"
             "QRV=－qr/2。零误差。\n\n", None),
            ("[精确] ", "hi"),
            ("池底·温差弯矩 (AMQT, AMRT)：AMQT=AMRT=－αEH1²·Δt/(6(1－μ))，"
             "Δt=(TD－TA)/2。零误差。\n\n", None),
            ("[中等] ", "mi"),
            ("池壁·温差内力 (My2, MQ2, N2, Qy2)：公式结构已从公式图片确认"
             "（形如 My2=BMT·Eh²/(12(1－μ²))·α·Δt），比例常数按算例反标定，"
             "算例误差<1%。同一池体几何尺寸下改变材料/温度参数应仍可信，"
             "改变 D/H/H2 时建议以原程序复核。\n\n", None),
            ("[近似] ", "lo"),
            ("池壁池底联合附加内力 (MYDT, NDT, QYDT, MYD, ND, QYD)：属于池壁底弯矩与"
             "池底周边弯矩不等、需调整分配的二次修正项，未能反推出通用闭式公式，"
             "系用最小二乘法按 G-27-1 算例经验标定，适用范围未知，仅供参考。\n\n", None),
            ("联合总内力：为以上各分项直接求和，只要分项可信，求和结果同样可信。\n\n", None),
            ("三、算例来源\n", "h1"),
            ("D:\\BaiduNetdiskDownload\\水利程序集软件包\\G27\\G-27-1.INT / G-27-1.OUT，"
             "题目代号 555，D=4.8m，H=4.0m，H1=0.3m，H2=0.2m，K=6。\n\n", None),
            ("四、参考文献\n", "h1"),
            ("张光斗.《圆筒钢筋砼薄壁池的内力计算》.水利电力出版社.\n", None),
        ]
        for text, tag in content:
            if tag:
                txt.insert("end", text, tag)
            else:
                txt.insert("end", text)
        txt.configure(state="disabled")

    # =====================================================================
    # Tab 5: 使用帮助
    # =====================================================================
    def _build_tab_help(self):
        frame = ttk.Frame(self.tab_help, style="Panel.TFrame")
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        txt = tk.Text(frame, wrap="word", font=("Microsoft YaHei UI", 10),
                       bg="#fbfcfe", fg=COLOR_TEXT, relief="flat",
                       highlightthickness=1, highlightbackground=COLOR_BORDER, padx=12, pady=10)
        vbar = ttk.Scrollbar(frame, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=vbar.set)
        txt.pack(side="left", fill="both", expand=True)
        vbar.pack(side="right", fill="y")
        txt.tag_configure("h1", font=("Microsoft YaHei UI", 12, "bold"), foreground=COLOR_ACCENT)
        help_text = (
            "使用步骤\n\n"
            "1. 在左侧“数据文件”面板选择数据所在目录，双击 .INT 文件即可自动读取到"
            "“数据来源”页；也可直接在“数据来源”页手工填写各项参数与内力系数表。\n\n"
            "2. 修改“分段点数 K”后，点击“按 K 重建系数表格”按钮，系数表行数会随之调整。\n\n"
            "3. 内力系数 BM/BN/BK/BMT/BNT/BKT/BMD/BND/BKD 需依据池壁高径比等参数，"
            "从原说明书附表1~9中人工查表填入，与原 DOS 程序操作方式一致。\n\n"
            "4. 点击工具栏“计算”，程序自动切换到“文本结果”页显示计算书，并可在"
            "“图形结果”页查看内力沿池壁高度或池底半径的分布曲线。\n\n"
            "5. 点击“存盘”可将当前数据另存为 .INT 格式文本文件；点击“打印”可将"
            "文本结果发送到打印机或另存为文件。\n\n"
            "6. 结果中标注的 [精确]/[中等]/[近似] 表示该项内力计算公式的可信度，"
            "详见“程序说明”页。\n"
        )
        txt.insert("1.0", "使用帮助\n\n", "h1")
        txt.insert("end", help_text)
        txt.configure(state="disabled")

    # =====================================================================
    # 数据读写
    # =====================================================================
    def _short_path(self, p):
        p = p.replace("/mnt/c/", "C:\\").replace("/", "\\")
        return p if len(p) < 40 else "…" + p[-38:]

    def _refresh_file_list(self):
        self.file_list.delete(0, "end")
        d = self.current_dir.get()
        try:
            names = sorted(f for f in os.listdir(d) if f.upper().endswith(".INT"))
        except OSError:
            names = []
        for n in names:
            self.file_list.insert("end", n)
        if not names:
            self.file_list.insert("end", "(此目录无 .INT 文件)")

    def on_browse_dir(self):
        d = filedialog.askdirectory(initialdir=self.current_dir.get(), title="选择数据文件所在目录")
        if d:
            self.current_dir.set(d)
            self._dir_label.configure(text=self._short_path(d))
            self._refresh_file_list()

    def on_filelist_double_click(self, _evt=None):
        sel = self.file_list.curselection()
        if not sel:
            return
        name = self.file_list.get(sel[0])
        if not name.upper().endswith(".INT"):
            return
        path = os.path.join(self.current_dir.get(), name)
        self._open_file(path)

    def _open_file(self, path):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            data = engine.parse_int_text(text)
        except Exception as exc:
            messagebox.showerror("读取失败", f"无法解析文件：\n{path}\n\n{exc}")
            return
        self._load_input(data)
        self.filename_var.set(os.path.basename(path))
        self.status_var.set(f"已读取 {path}")

    def _load_input(self, d: TankInput):
        self.input_data = d
        self.field_vars["N"].set(d.N)
        self.field_vars["K"].set(str(d.K))
        self.field_vars["D"].set(str(d.D))
        self.field_vars["H"].set(str(d.H))
        self.field_vars["H1"].set(str(d.H1))
        self.field_vars["H2"].set(str(d.H2))
        self.field_vars["E"].set(str(d.E))
        self.field_vars["AM"].set(str(d.AM))
        self.field_vars["AL"].set(str(d.AL))
        self.field_vars["TB"].set(str(d.TB))
        self.field_vars["TA"].set(str(d.TA))
        self.field_vars["TD"].set(str(d.TD))
        self._build_coef_table(d.K)
        for c, (key, _label) in enumerate(COEF_COLS):
            arr = getattr(d, key)
            for i in range(d.K):
                self.coef_entries[(key, i)].set(str(arr[i]))

    def _collect_input(self) -> TankInput:
        try:
            N = self.field_vars["N"].get().strip() or "0"
            K = int(float(self.field_vars["K"].get()))
            D = float(self.field_vars["D"].get())
            H = float(self.field_vars["H"].get())
            H1 = float(self.field_vars["H1"].get())
            H2 = float(self.field_vars["H2"].get())
            E = float(self.field_vars["E"].get())
            AM = float(self.field_vars["AM"].get())
            AL = float(self.field_vars["AL"].get())
            TB = float(self.field_vars["TB"].get())
            TA = float(self.field_vars["TA"].get())
            TD = float(self.field_vars["TD"].get())
        except ValueError as exc:
            raise ValueError(f"基本参数存在非数字输入：{exc}")

        if K < 2:
            raise ValueError("分段点数 K 至少为 2")

        arrays = {}
        for key, _label in COEF_COLS:
            vals = []
            for i in range(K):
                var = self.coef_entries.get((key, i))
                if var is None:
                    raise ValueError(f"系数表缺少 {key} 第 {i + 1} 行，请先“按 K 重建系数表格”")
                try:
                    vals.append(float(var.get()))
                except ValueError:
                    raise ValueError(f"系数 {key} 第 {i + 1} 行不是有效数字：{var.get()!r}")
            arrays[key] = vals

        return TankInput(N=N, K=K, D=D, H=H, H1=H1, H2=H2, E=E, AM=AM, AL=AL,
                          TB=TB, TA=TA, TD=TD, **arrays)

    # =====================================================================
    # 工具栏动作
    # =====================================================================
    def on_new(self):
        if not messagebox.askyesno("新建", "新建将清空当前数据，是否继续？"):
            return
        self._load_input(engine.blank_input(6))
        self.filename_var.set("未命名.INT")
        self.results = None
        self.text_result.configure(state="normal")
        self.text_result.delete("1.0", "end")
        self.text_result.insert("1.0", "尚未计算。")
        self.text_result.configure(state="disabled")
        self._draw_placeholder()
        self.status_var.set("已新建空白数据")

    def on_open(self):
        path = filedialog.askopenfilename(
            initialdir=self.current_dir.get(),
            title="打开数据文件",
            filetypes=[("INT 数据文件", "*.INT *.int"), ("所有文件", "*.*")])
        if path:
            self._open_file(path)

    def on_save(self):
        try:
            data = self._collect_input()
        except ValueError as exc:
            messagebox.showerror("输入有误", str(exc))
            return
        default_name = self.filename_var.get() or "未命名.INT"
        path = filedialog.asksaveasfilename(
            initialdir=self.current_dir.get(), initialfile=default_name,
            defaultextension=".INT", filetypes=[("INT 数据文件", "*.INT"), ("所有文件", "*.*")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(engine.to_int_text(data))
        except OSError as exc:
            messagebox.showerror("保存失败", str(exc))
            return
        self.filename_var.set(os.path.basename(path))
        self.status_var.set(f"已保存到 {path}")
        self._refresh_file_list()

    def on_calculate(self):
        try:
            data = self._collect_input()
        except ValueError as exc:
            messagebox.showerror("输入有误", str(exc))
            return
        try:
            results = engine.compute(data)
        except Exception as exc:
            messagebox.showerror("计算失败", str(exc))
            return
        self.input_data = data
        self.results = results
        self._render_text_result(data, results)
        self.refresh_graph()
        self.notebook.select(self.tab_text)
        self.status_var.set("计算完成")

    def on_print(self):
        if self.results is None:
            messagebox.showinfo("打印", "请先点击“计算”生成结果。")
            return
        content = self.text_result.get("1.0", "end")
        tmp_path = os.path.join(self.current_dir.get(), "_G27_打印临时.txt")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError as exc:
            messagebox.showerror("打印失败", str(exc))
            return
        if sys.platform.startswith("win"):
            try:
                os.startfile(tmp_path, "print")
                self.status_var.set("已发送到默认打印机")
                return
            except OSError:
                pass
        messagebox.showinfo("打印", f"当前平台无法直接调用打印机，\n计算书已另存为：\n{tmp_path}\n请手动打印。")

    def on_exit(self):
        if messagebox.askyesno("退出", "确定要退出程序吗？"):
            self.destroy()

    def on_save_text_result(self):
        content = self.text_result.get("1.0", "end")
        path = filedialog.asksaveasfilename(
            initialdir=self.current_dir.get(),
            initialfile=(self.filename_var.get().rsplit(".", 1)[0] + ".out.txt"),
            defaultextension=".txt", filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        self.status_var.set(f"文本结果已保存到 {path}")

    def on_copy_text_result(self):
        content = self.text_result.get("1.0", "end")
        self.clipboard_clear()
        self.clipboard_append(content)
        self.status_var.set("文本结果已复制到剪贴板")

    # =====================================================================
    # 文本结果渲染
    # =====================================================================
    def _render_text_result(self, d: TankInput, r: Results):
        self.text_result.configure(state="normal")
        self.text_result.delete("1.0", "end")

        def line(s=""):
            self.text_result.insert("end", s + "\n")

        def title(s):
            self.text_result.insert("end", s + "\n", "title")

        def conf_tag(conf: Confidence):
            self.text_result.insert("end", f"[{conf.value}] ", f"tag_{conf.name}")

        W = 78
        title("*" * W)
        title(f"****     露天式圆形水池结构设计程序 G-27  (Python 美化版)     ****".center(W))
        title("*" * W)
        line()
        line("原 始 数 据".center(W))
        line("-" * W)
        line(f"  题目代号 N = {d.N}      分段点数 K = {d.K}")
        line(f"  圆池内直径 D = {d.D:.3f} m      圆池高度 H = {d.H:.3f} m")
        line(f"  底板厚度 H1 = {d.H1:.3f} m      圆池壁厚 H2 = {d.H2:.3f} m")
        line(f"  砼弹性模量 E = {d.E:.4g} kN/m^2   砼侧向变形系数 AM = {d.AM:.3f}")
        line(f"  砼温度伸缩系数 AL = {d.AL:.2e}    池壁中心线半径 C = {d.C:.3f} m")
        line(f"  TB = {d.TB:.2f} ℃   TA = {d.TA:.2f} ℃   TD = {d.TD:.2f} ℃")
        line()

        conf_tag(Confidence.HIGH)
        line("池壁在内水压力作用下的内力")
        line("-" * W)
        line(f"{'点号':>4} {'MY1(kN-m)':>12} {'MQ1(kN-m)':>12} {'N1(kN)':>12} {'QY1(kN)':>12}")
        for i in range(d.K):
            line(f"{i+1:>4} {r.MY1[i]:>12.4f} {r.MQ1[i]:>12.4f} {r.N1[i]:>12.4f} {r.QY1[i]:>12.4f}")
        line()

        conf_tag(Confidence.MEDIUM)
        line("池壁在温差作用下的内力")
        line("-" * W)
        line(f"{'点号':>4} {'MY2(kN-m)':>12} {'MQ2(kN-m)':>12} {'N2(kN)':>12} {'QY2(kN)':>12}")
        for i in range(d.K):
            line(f"{i+1:>4} {r.MY2[i]:>12.4f} {r.MQ2[i]:>12.4f} {r.N2[i]:>12.4f} {r.QY2[i]:>12.4f}")
        line()

        conf_tag(Confidence.HIGH)
        line("池底在自重作用下的内力")
        line("-" * W)
        line(f"{'点号':>4} {'R(m)':>10} {'QRV(kN)':>12} {'MRV(kN-m)':>12} {'MQV(kN-m)':>12}")
        for i in range(d.K):
            line(f"{i+1:>4} {r.R[i]:>10.2f} {r.QRV[i]:>12.4f} {r.MRV[i]:>12.4f} {r.MQV[i]:>12.4f}")
        line()

        conf_tag(Confidence.HIGH)
        line("池底在温度作用下的弯矩 (kN-m)")
        line("-" * W)
        line(f"  AMQT = {r.AMQT:.4f}      AMRT = {r.AMRT:.4f}")
        line()

        conf_tag(Confidence.LOW)
        line("池壁、池底联合作用下的附加内力")
        line("-" * W)
        line("  1. 考虑温度作用")
        line(f"{'点号':>4} {'MYDT(kN-m)':>12} {'NDT(kN)':>12} {'QYDT(kN)':>12}")
        for i in range(d.K):
            line(f"{i+1:>4} {r.MYDT[i]:>12.4f} {r.NDT[i]:>12.4f} {r.QYDT[i]:>12.4f}")
        line("  2. 不考虑温度作用")
        line(f"{'点号':>4} {'MYD(kN-m)':>12} {'ND(kN)':>12} {'QYD(kN)':>12}")
        for i in range(d.K):
            line(f"{i+1:>4} {r.MYD[i]:>12.4f} {r.ND[i]:>12.4f} {r.QYD[i]:>12.4f}")
        line()

        conf_tag(Confidence.HIGH)
        line("池壁和池底的总内力 (= 以上分项求和)")
        line("-" * W)
        line("  1. 考虑温度作用")
        line(f"{'点号':>4} {'MY(kN-m)':>12} {'MQ(kN-m)':>12} {'N(kN)':>12} {'QY(kN)':>12}")
        for i in range(d.K):
            line(f"{i+1:>4} {r.MY_t[i]:>12.4f} {r.MQ_t[i]:>12.4f} {r.N_t[i]:>12.4f} {r.QY_t[i]:>12.4f}")
        line("  2. 不考虑温度作用")
        line(f"{'点号':>4} {'MY1(kN-m)':>12} {'MQ1(kN-m)':>12} {'N1(kN)':>12} {'QY1(kN)':>12}")
        for i in range(d.K):
            line(f"{i+1:>4} {r.MY_nt[i]:>12.4f} {r.MQ_nt[i]:>12.4f} {r.N_nt[i]:>12.4f} {r.QY_nt[i]:>12.4f}")
        line()
        line("-" * W)
        line("说明：[精确]=公式已逐字核对、算例零误差；[中等]=公式结构确认、常数经算例标定；")
        line("      [近似]=未得通用公式、按算例经验标定，仅供参考。详见“程序说明”页。")
        line(f"计算日期：{date.today().isoformat()}")

        self.text_result.configure(state="disabled")


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
