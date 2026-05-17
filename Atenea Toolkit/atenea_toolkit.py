import os
import sys
import threading
import subprocess
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import customtkinter as ctk


# ==========================================================
# PALETA
# ==========================================================
BG_BASE      = "#1a1a1a"
BG_PANEL     = "#222222"
BG_ELEVATED  = "#2c2c2c"
BG_ACTIVE    = "#383838"
BORDER       = "#3a3a3a"
TXT_PRIMARY  = "#f0f0f0"
TXT_MUTED    = "#888888"
BTN_HOVER    = "#3a3a3a"
WHITE        = "#ffffff"

TAB_BG       = "#1e1e1e"
TAB_ACTIVE   = "#2c2c2c"
TAB_BORDER   = "#2e2e2e"


# ==========================================================
# DATOS COMPARTIDOS
# ==========================================================
EXT_MAP_IMG = {
    "All formats": [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"],
    "PNG":         [".png"],
    "JPG":         [".jpg", ".jpeg"],
    "WEBP":        [".webp"],
    "BMP":         [".bmp"],
    "TIFF":        [".tiff", ".tif"],
}

PIL_FORMAT = {"PNG": "PNG", "JPG": "JPEG", "WEBP": "WEBP", "BMP": "BMP", "TIFF": "TIFF"}
PIL_EXT    = {"PNG": ".png", "JPG": ".jpg", "WEBP": ".webp", "BMP": ".bmp", "TIFF": ".tiff"}

DDS_OUT_FORMATS = {
    "Auto":     "AUTO",
    "BC3/DXT5": "BC3_UNORM",
    "BC1/DXT1": "BC1_UNORM",
    "BC7":      "BC7_UNORM",
    "BC4":      "BC4_UNORM",
}
IMG_OUT_FORMATS  = ["PNG", "JPG", "WEBP", "BMP", "TIFF"]
FORMATOS_SALIDA  = ["WEBP", "PNG", "JPG", "BMP", "TIFF"]

PRESET_SIZES = [
    ("120 × 120", (120, 120)),
    ("320 × 320", (320, 320)),
    ("100 × 100", (100, 100)),
    ("Custom",     None),
]


# ==========================================================
# LÓGICA — CONVERTER
# ==========================================================
def convertir_imagenes(entradas, carpeta_salida, fmt_salida, calidad,
                       cb_prog, cb_log, cb_fin):
    os.makedirs(carpeta_salida, exist_ok=True)
    total = len(entradas)
    ok = errores = 0
    for i, ruta in enumerate(entradas):
        nombre = os.path.basename(ruta)
        base   = os.path.splitext(nombre)[0]
        ext_o  = PIL_EXT[fmt_salida]
        dest   = os.path.join(carpeta_salida, base + ext_o)
        try:
            img = Image.open(ruta)
            if fmt_salida in ("JPG", "BMP"):
                if img.mode in ("RGBA", "LA", "P"):
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    bg.paste(img, mask=img.split()[-1])
                    img = bg
                else:
                    img = img.convert("RGB")
            elif fmt_salida == "PNG":
                img = img.convert("RGBA")
            elif fmt_salida == "TIFF":
                if img.mode not in ("RGB", "RGBA", "L"):
                    img = img.convert("RGB")
            if fmt_salida in ("WEBP", "JPG"):
                img.save(dest, PIL_FORMAT[fmt_salida], quality=calidad)
            else:
                img.save(dest, PIL_FORMAT[fmt_salida])
            ok += 1
            cb_log(f"  ✓  {nombre}  →  {base + ext_o}\n")
        except Exception as e:
            errores += 1
            cb_log(f"  ✗  {nombre}: {e}\n")
        cb_prog(i + 1, total)
    cb_fin(ok, errores)


# ==========================================================
# LÓGICA — RESIZER
# ==========================================================
def redimensionar_imagenes(entradas, carpeta_salida, ancho, alto,
                            cb_prog, cb_log, cb_fin, ignorar_menores=False):
    os.makedirs(carpeta_salida, exist_ok=True)
    total = len(entradas)
    ok = errores = omitidas = 0
    for i, ruta in enumerate(entradas):
        nombre = os.path.basename(ruta)
        base, ext = os.path.splitext(nombre)
        dest = os.path.join(carpeta_salida, nombre)
        try:
            img = Image.open(ruta)
            if ignorar_menores and img.width <= ancho and img.height <= alto:
                omitidas += 1
                cb_log(f"  ⏭  Skipped ({img.width}×{img.height}px): {nombre}\n")
                cb_prog(i + 1, total)
                continue
            img = img.convert("RGBA")
            ratio = min(ancho / img.width, alto / img.height)
            nw = round(img.width * ratio)
            nh = round(img.height * ratio)
            img = img.resize((nw, nh), Image.LANCZOS)
            lienzo = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
            lienzo.paste(img, ((ancho - nw) // 2, (alto - nh) // 2), img)
            ext_l = ext.lower()
            if ext_l in (".jpg", ".jpeg"):
                bg = Image.new("RGB", (ancho, alto), (255, 255, 255))
                bg.paste(lienzo, mask=lienzo.split()[3])
                bg.save(dest, "JPEG", quality=95)
            elif ext_l == ".bmp":
                bg = Image.new("RGB", (ancho, alto), (255, 255, 255))
                bg.paste(lienzo, mask=lienzo.split()[3])
                bg.save(dest, "BMP")
            elif ext_l == ".webp":
                lienzo.save(dest, "WEBP", quality=95)
            elif ext_l in (".tiff", ".tif"):
                lienzo.save(dest, "TIFF")
            else:
                lienzo.save(dest, "PNG")
            ok += 1
            cb_log(f"  ✓  {nombre}  →  {ancho}×{alto}px\n")
        except Exception as e:
            errores += 1
            cb_log(f"  ✗  {nombre}: {e}\n")
        cb_prog(i + 1, total)
    cb_fin(ok, errores, omitidas)


# ==========================================================
# LÓGICA — DDS
# ==========================================================
def has_alpha(path):
    try:
        img = Image.open(path).convert("RGBA")
        _, _, _, a = img.split()
        return a.getextrema()[0] < 255
    except Exception:
        return False

def convert_to_dds(inputs, out_folder, fmt_dds, mipmaps,
                   cb_prog, cb_log, cb_fin, texconv_path):
    os.makedirs(out_folder, exist_ok=True)
    total = len(inputs)
    ok = errors = 0
    for i, path in enumerate(inputs):
        name = os.path.basename(path)
        base = os.path.splitext(name)[0]
        dest = os.path.join(out_folder, base + ".dds")
        try:
            fmt_use = fmt_dds
            if fmt_use == "AUTO":
                fmt_use = "BC3_UNORM" if has_alpha(path) else "BC1_UNORM"
                cb_log(f"  ·  {name}  →  auto: {fmt_use}\n")
            cmd = [texconv_path, "-nologo", "-y", "-f", fmt_use, "-o", out_folder]
            cmd += ["-m", "0"] if mipmaps else ["-m", "1"]
            cmd.append(path)
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if r.returncode == 0 and os.path.exists(dest):
                ok += 1
                cb_log(f"  ✓  {name}  →  {base}.dds\n")
            else:
                raise RuntimeError(r.stderr.strip() or "texconv failed")
        except Exception as e:
            errors += 1
            cb_log(f"  ✗  {name}: {e}\n")
        cb_prog(i + 1, total)
    cb_fin(ok, errors)

def convert_dds_to_img(inputs, out_folder, out_fmt,
                       cb_prog, cb_log, cb_fin, texconv_path):
    os.makedirs(out_folder, exist_ok=True)
    total = len(inputs)
    ok = errors = 0
    for i, path in enumerate(inputs):
        name = os.path.basename(path)
        base = os.path.splitext(name)[0]
        ext  = PIL_EXT[out_fmt]
        dest = os.path.join(out_folder, base + ext)
        try:
            cmd = [texconv_path, "-nologo", "-y", "-ft", "png", "-o", out_folder, path]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            png_out = os.path.join(out_folder, base + ".png")
            if r.returncode != 0 or not os.path.exists(png_out):
                raise RuntimeError(r.stderr.strip() or "texconv failed")
            if out_fmt != "PNG":
                img = Image.open(png_out)
                if out_fmt == "JPG":
                    img = img.convert("RGB")
                img.save(dest, PIL_FORMAT[out_fmt])
                os.remove(png_out)
            ok += 1
            cb_log(f"  ✓  {name}  →  {base}{ext}\n")
        except Exception as e:
            errors += 1
            cb_log(f"  ✗  {name}: {e}\n")
        cb_prog(i + 1, total)
    cb_fin(ok, errors)


# ==========================================================
# APP PRINCIPAL — TOOLKIT
# ==========================================================
class AteneaToolkit(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.configure(fg_color=BG_BASE)
        self.title("Atenea Toolkit")

        # ── Escalado DPI ─────────────────────────────────────
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self._sc = max(0.85, min(sw / 1920, 1.6))

        win_w = max(500, min(int(sw * 0.38), 820))
        win_h = max(620, min(int(sh * 0.88), 1020))
        self.geometry(f"{win_w}x{win_h}+{(sw-win_w)//2}+{(sh-win_h)//2}")
        self.minsize(500, 620)
        self.resizable(True, True)

        self._set_icon()
        self._build_shell()

    # ── Helpers de escala ────────────────────────────────────
    def fs(self, s):  return max(8,  int(s * self._sc))
    def pd(self, s):  return max(4,  int(s * self._sc))
    def ht(self, s):  return max(24, int(s * self._sc))

    # ── Icono ────────────────────────────────────────────────
    def _set_icon(self):
        for path, method in [(self._res("logo.ico"), "bitmap"),
                              (self._res("logo.png"), "photo")]:
            if not os.path.exists(path):
                continue
            try:
                if method == "bitmap":
                    self.iconbitmap(path)
                else:
                    self.iconphoto(True, ImageTk.PhotoImage(Image.open(path)))
            except Exception:
                pass

    # ── Shell: sidebar izquierda + contenido ─────────────────
    def _build_shell(self):
        p = self.pd

        # LAYOUT PRINCIPAL: sidebar | contenido
        main = ctk.CTkFrame(self, fg_color=BG_BASE, corner_radius=0)
        main.pack(fill="both", expand=True)

        # ── SIDEBAR ─────────────────────────────────────────
        sidebar = ctk.CTkFrame(main, fg_color=TAB_BG, corner_radius=0,
                                width=p(160))
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Separador vertical derecho del sidebar
        ctk.CTkFrame(main, width=1, fg_color=TAB_BORDER,
                     corner_radius=0).pack(side="left", fill="y")

        # Logo + título compactos en una fila
        logo_row = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_row.pack(fill="x", padx=p(14), pady=(p(18), p(4)))

        logo_path = self._res("logo.png")
        if os.path.exists(logo_path):
            try:
                li = ctk.CTkImage(Image.open(logo_path), size=(self.ht(28), self.ht(28)))
                ctk.CTkLabel(logo_row, image=li, text="").pack(side="left", padx=(0, p(8)))
            except Exception:
                pass

        title_col = ctk.CTkFrame(logo_row, fg_color="transparent")
        title_col.pack(side="left")
        ctk.CTkLabel(title_col, text="Atenea Toolkit",
                     font=("Segoe UI Semibold", self.fs(12)),
                     text_color=TXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(title_col, text="V2026",
                     font=("Segoe UI", self.fs(8)),
                     text_color=TXT_MUTED).pack(anchor="w")

        # Separador
        ctk.CTkFrame(sidebar, height=1, fg_color=TAB_BORDER).pack(
            fill="x", padx=p(10), pady=(p(12), p(10)))

        # Botones de navegación con indicador lateral activo
        self._active_tab     = None
        self._tab_buttons    = {}
        self._tab_indicators = {}
        tabs = [
            ("🔄  Converter", "converter"),
            ("📐  Resizer",   "resizer"),
            ("🎮  DDS",       "dds"),
        ]
        for label, key in tabs:
            row = ctk.CTkFrame(sidebar, fg_color="transparent", height=self.ht(36))
            row.pack(fill="x", pady=(0, p(3)))
            row.pack_propagate(False)

            # Barra indicadora lateral izquierda
            ind = ctk.CTkFrame(row, width=3, fg_color="transparent", corner_radius=2)
            ind.pack(side="left", fill="y", padx=(p(6), 0))
            self._tab_indicators[key] = ind

            btn = ctk.CTkButton(
                row, text=label,
                fg_color="transparent", hover_color=BG_ELEVATED,
                text_color=TXT_MUTED, corner_radius=6,
                anchor="w", font=("Segoe UI", self.fs(11)),
                height=self.ht(36), border_width=0,
                command=lambda k=key: self._switch_tab(k),
            )
            btn.pack(side="left", fill="both", expand=True, padx=(p(4), p(8)))
            self._tab_buttons[key] = btn

        # Footer del sidebar
        ctk.CTkLabel(sidebar, text="© 2026  Atenea Store Tools",
                     font=("Segoe UI", self.fs(7)),
                     text_color="#333333", justify="left"
                     ).pack(side="bottom", anchor="w", padx=p(14), pady=(0, p(12)))

        ctk.CTkButton(
            sidebar, text="Discord",
            fg_color="#2a2a2a", hover_color="#313131",
            text_color="#666666", border_width=1, border_color="#333333",
            corner_radius=6, height=self.ht(28),
            font=("Segoe UI", self.fs(10)),
            command=lambda: webbrowser.open("https://discord.gg/mam8Nmg49d"),
        ).pack(side="bottom", fill="x", padx=p(14), pady=(0, p(6)))

        # ── CONTENT AREA ────────────────────────────────────
        self._content = ctk.CTkFrame(main, fg_color=BG_BASE, corner_radius=0)
        self._content.pack(side="left", fill="both", expand=True)

        # Construir los 3 paneles
        self._panels = {}
        self._panels["converter"] = self._build_converter(self._content)
        self._panels["resizer"]   = self._build_resizer(self._content)
        self._panels["dds"]       = self._build_dds(self._content)

        self._switch_tab("converter")

    def _switch_tab(self, key):
        if self._active_tab == key:
            return
        self._active_tab = key
        for k, panel in self._panels.items():
            if k == key:
                panel.pack(fill="both", expand=True)
            else:
                panel.pack_forget()
        for k, btn in self._tab_buttons.items():
            ind = self._tab_indicators[k]
            if k == key:
                btn.configure(text_color=TXT_PRIMARY, fg_color=BG_ELEVATED)
                ind.configure(fg_color="#666666")
            else:
                btn.configure(text_color=TXT_MUTED, fg_color="transparent")
                ind.configure(fg_color="transparent")

    # ── Helpers UI compartidos ───────────────────────────────
    def _divider(self, parent):
        ctk.CTkFrame(parent, height=1, fg_color=BORDER).pack(
            fill="x", padx=self.pd(24), pady=(self.pd(8), self.pd(8)))

    def _label(self, parent, text):
        ctk.CTkLabel(parent, text=text,
                     font=("Segoe UI", self.fs(9), "bold"),
                     text_color=TXT_MUTED).pack(
            anchor="w", padx=self.pd(24), pady=(0, self.pd(4)))

    def _entry(self, parent, **kw):
        return ctk.CTkEntry(
            parent, height=self.ht(34), corner_radius=8,
            fg_color=BG_PANEL, border_color=BORDER, border_width=1,
            placeholder_text_color=TXT_MUTED,
            text_color=TXT_PRIMARY, font=("Segoe UI", self.fs(12)),
            **kw)

    def _btn(self, parent, text, command, width=None, height=None, **kw):
        kwargs = dict(
            fg_color=BG_ELEVATED, hover_color=BTN_HOVER,
            text_color=TXT_PRIMARY, border_width=1, border_color=BORDER,
            height=height if height is not None else self.ht(34),
            corner_radius=8,
            font=("Segoe UI", self.fs(12)),
            command=command,
        )
        if width:
            kwargs["width"] = width
        kwargs.update(kw)
        return ctk.CTkButton(parent, text=text, **kwargs)

    def _log_widget(self, parent):
        lb = ctk.CTkTextbox(
            parent, height=self.ht(90), corner_radius=8,
            fg_color=BG_PANEL, border_color=BORDER, border_width=1,
            text_color=TXT_MUTED, font=("Consolas", self.fs(11)),
            scrollbar_button_color=BG_ELEVATED,
        )
        lb.pack(fill="x", padx=self.pd(24), pady=(0, self.pd(6)))
        lb.configure(state="normal")
        lb.insert("end", "  —  Waiting for input…\n")
        lb.configure(state="disabled")
        return lb

    def _progress_row(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=self.pd(24), pady=(self.pd(2), self.pd(4)))
        status = ctk.CTkLabel(row, text="Ready",
                               font=("Segoe UI", self.fs(10)), text_color=TXT_MUTED)
        status.pack(side="left")
        counter = ctk.CTkLabel(row, text="0 / 0",
                                font=("Segoe UI", self.fs(10)), text_color=TXT_MUTED)
        counter.pack(side="right")
        bar = ctk.CTkProgressBar(parent, height=3, corner_radius=2,
                                  fg_color=BG_ELEVATED, progress_color=TXT_PRIMARY)
        bar.set(0)
        bar.pack(fill="x", padx=self.pd(24), pady=(0, self.pd(8)))
        return status, counter, bar

    def _log_write(self, lb, text):
        def _w():
            lb.configure(state="normal")
            lb.insert("end", text)
            lb.see("end")
            lb.configure(state="disabled")
        self.after(0, _w)

    def _log_clear(self, lb):
        lb.configure(state="normal")
        lb.delete("1.0", "end")
        lb.configure(state="disabled")

    def _folder_row(self, parent, entry, label="Output folder", default="output"):
        self._divider(parent)
        self._label(parent, label.upper())
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=self.pd(24))
        row.columnconfigure(0, weight=1)
        e = self._entry(row, placeholder_text="Select output folder…")
        e.insert(0, default)
        e.grid(row=0, column=0, sticky="ew", padx=(0, self.pd(8)))
        self._btn(row, "…", lambda: self._pick_out(e),
                  width=self.ht(34)).grid(row=0, column=1)
        return e

    def _pick_out(self, entry_widget):
        f = filedialog.askdirectory()
        if f:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, f)

    def _input_block(self, parent, on_folder, on_files):
        self._label(parent, "INPUT")
        e = self._entry(parent, placeholder_text="Select a folder or files…")
        e.pack(fill="x", padx=self.pd(24), pady=(0, self.pd(6)))
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=self.pd(24))
        row.columnconfigure(0, weight=1)
        row.columnconfigure(1, weight=1)
        self._btn(row, "  Folder", on_folder, height=self.ht(30)).grid(row=0, column=0, sticky="ew", padx=(0, self.pd(6)))
        self._btn(row, "  Files",  on_files, height=self.ht(30)).grid(row=0, column=1, sticky="ew")
        return e

    def _res(self, path):
        try:
            base = sys._MEIPASS
        except Exception:
            base = os.path.abspath(".")
        return os.path.join(base, path)

    # ==========================================================
    # TAB 1 — IMAGE CONVERTER
    # ==========================================================
    def _build_converter(self, parent):
        self._conv_files   = []
        self._conv_fmt     = "WEBP"

        frame = ctk.CTkScrollableFrame(parent, fg_color=BG_BASE,
                                        scrollbar_button_color=BG_ELEVATED,
                                        scrollbar_button_hover_color=BTN_HOVER)

        ctk.CTkFrame(frame, fg_color="transparent", height=8).pack()
        self._divider(frame)
        self._conv_entry_in = self._input_block(
            frame,
            on_folder=lambda: self._conv_pick_folder(),
            on_files =lambda: self._conv_pick_files(),
        )

        self._divider(frame)
        self._label(frame, "FILTER BY FORMAT")
        self._conv_fmt_in = ctk.CTkOptionMenu(
            frame, values=list(EXT_MAP_IMG.keys()),
            height=self.ht(34), corner_radius=8,
            fg_color=BG_PANEL, button_color=BG_ELEVATED,
            button_hover_color=BTN_HOVER, text_color=TXT_PRIMARY,
            dropdown_fg_color=BG_PANEL, dropdown_text_color=TXT_PRIMARY,
            dropdown_hover_color=BG_ELEVATED,
            font=("Segoe UI", self.fs(12)),
        )
        self._conv_fmt_in.set("All formats")
        self._conv_fmt_in.pack(fill="x", padx=self.pd(24))

        self._conv_entry_out = self._folder_row(frame, None, "Output Folder", "converted")

        self._divider(frame)
        self._label(frame, "TARGET FORMAT")
        self._conv_fmt_btns = {}
        fmt_row = ctk.CTkFrame(frame, fg_color="transparent")
        fmt_row.pack(fill="x", padx=self.pd(24))
        for i, fmt in enumerate(FORMATOS_SALIDA):
            fmt_row.columnconfigure(i, weight=1)
        for i, fmt in enumerate(FORMATOS_SALIDA):
            active = (fmt == "WEBP")
            b = ctk.CTkButton(
                fmt_row, text=fmt, height=self.ht(34), corner_radius=8,
                fg_color=BG_ACTIVE if active else BG_ELEVATED,
                hover_color=BTN_HOVER,
                text_color=WHITE if active else TXT_PRIMARY,
                border_width=1, border_color="#555555" if active else BORDER,
                font=("Segoe UI", self.fs(12)),
                command=lambda f=fmt: self._conv_select_fmt(f),
            )
            b.grid(row=0, column=i, sticky="ew", padx=(0, self.pd(6) if i < len(FORMATOS_SALIDA)-1 else 0))
            self._conv_fmt_btns[fmt] = b

        self._divider(frame)
        self._conv_q_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self._conv_q_frame.pack(fill="x", padx=self.pd(24))
        q_head = ctk.CTkFrame(self._conv_q_frame, fg_color="transparent")
        q_head.pack(fill="x")
        ctk.CTkLabel(q_head, text="QUALITY",
                     font=("Segoe UI", self.fs(9), "bold"),
                     text_color=TXT_MUTED).pack(side="left")
        self._conv_q_lbl = ctk.CTkLabel(q_head, text="85",
                                          font=("Segoe UI", self.fs(9), "bold"),
                                          text_color=TXT_PRIMARY)
        self._conv_q_lbl.pack(side="right")
        self._conv_q_slider = ctk.CTkSlider(
            self._conv_q_frame, from_=1, to=100, number_of_steps=99,
            fg_color=BG_ELEVATED, progress_color=BG_ACTIVE,
            button_color=TXT_PRIMARY, button_hover_color=WHITE,
            command=lambda v: self._conv_q_lbl.configure(text=str(int(v))),
        )
        self._conv_q_slider.set(85)
        self._conv_q_slider.pack(fill="x", pady=(self.pd(4), 0))

        self._divider(frame)
        self._conv_status, self._conv_counter, self._conv_bar = self._progress_row(frame)
        self._conv_log = self._log_widget(frame)

        self._conv_btn = ctk.CTkButton(
            frame, text="Convert images",
            font=("Segoe UI Semibold", self.fs(14)),
            fg_color=BG_ELEVATED, hover_color=BTN_HOVER,
            text_color=TXT_PRIMARY, border_width=1, border_color=BORDER,
            height=self.ht(46), corner_radius=8,
            command=self._conv_start,
        )
        self._conv_btn.pack(fill="x", padx=self.pd(24), pady=(0, self.pd(4)))


        return frame

    def _conv_pick_folder(self):
        f = filedialog.askdirectory()
        if f:
            self._conv_files = []
            self._conv_entry_in.delete(0, tk.END)
            self._conv_entry_in.insert(0, f)

    def _conv_pick_files(self):
        files = filedialog.askopenfilenames(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.tif"), ("All", "*.*")])
        if files:
            self._conv_files = list(files)
            self._conv_entry_in.delete(0, tk.END)
            self._conv_entry_in.insert(0, f"{len(files)} files selected")

    def _conv_select_fmt(self, fmt):
        for f, b in self._conv_fmt_btns.items():
            if f == fmt:
                b.configure(fg_color=BG_ACTIVE, text_color=WHITE, border_color="#555555")
            else:
                b.configure(fg_color=BG_ELEVATED, text_color=TXT_PRIMARY, border_color=BORDER)
        self._conv_fmt = fmt
        if fmt in ("WEBP", "JPG"):
            self._conv_q_frame.pack(fill="x", padx=self.pd(24))
        else:
            self._conv_q_frame.pack_forget()

    def _conv_get_inputs(self):
        exts = EXT_MAP_IMG[self._conv_fmt_in.get()]
        if self._conv_files:
            return [f for f in self._conv_files if os.path.splitext(f)[1].lower() in exts]
        folder = self._conv_entry_in.get().strip()
        if not folder or not os.path.isdir(folder):
            return []
        return [os.path.join(folder, f) for f in os.listdir(folder)
                if os.path.splitext(f)[1].lower() in exts]

    def _conv_start(self):
        files = self._conv_get_inputs()
        out   = self._conv_entry_out.get().strip()
        if not files:
            messagebox.showerror("Error", "No images found with the selected format.")
            return
        if not out:
            messagebox.showerror("Error", "Please select an output folder.")
            return
        calidad = int(self._conv_q_slider.get())
        self._conv_bar.set(0)
        self._conv_counter.configure(text=f"0 / {len(files)}")
        self._log_clear(self._conv_log)
        self._conv_status.configure(text="Converting…")
        self._conv_btn.configure(state="disabled", text="Converting…")
        threading.Thread(
            target=convertir_imagenes,
            args=(files, out, self._conv_fmt, calidad,
                  lambda d, t: (self.after(0, lambda: self._conv_bar.set(d/t)),
                                self.after(0, lambda: self._conv_counter.configure(text=f"{d} / {t}"))),
                  lambda txt: self._log_write(self._conv_log, txt),
                  self._conv_fin),
            daemon=True,
        ).start()

    def _conv_fin(self, ok, errores):
        def _d():
            self._conv_btn.configure(state="normal", text="Convert images")
            self._conv_status.configure(text="Done")
            msg = f"Converted: {ok} image{'s' if ok != 1 else ''}"
            if errores:
                msg += f"\nErrors: {errores}"
            messagebox.showinfo("Done", msg)
        self.after(0, _d)

    # ==========================================================
    # TAB 2 — IMAGE RESIZER
    # ==========================================================
    def _build_resizer(self, parent):
        self._rsz_files         = []
        self._rsz_preset        = 1
        self._rsz_chip_btns     = []

        frame = ctk.CTkScrollableFrame(parent, fg_color=BG_BASE,
                                        scrollbar_button_color=BG_ELEVATED,
                                        scrollbar_button_hover_color=BTN_HOVER)

        ctk.CTkFrame(frame, fg_color="transparent", height=8).pack()
        self._divider(frame)
        self._rsz_entry_in = self._input_block(
            frame,
            on_folder=lambda: self._rsz_pick_folder(),
            on_files =lambda: self._rsz_pick_files(),
        )

        self._divider(frame)
        self._label(frame, "FILTER BY FORMAT")
        self._rsz_fmt_in = ctk.CTkOptionMenu(
            frame, values=list(EXT_MAP_IMG.keys()),
            height=self.ht(34), corner_radius=8,
            fg_color=BG_PANEL, button_color=BG_ELEVATED,
            button_hover_color=BTN_HOVER, text_color=TXT_PRIMARY,
            dropdown_fg_color=BG_PANEL, dropdown_text_color=TXT_PRIMARY,
            dropdown_hover_color=BG_ELEVATED,
            font=("Segoe UI", self.fs(12)),
        )
        self._rsz_fmt_in.set("All formats")
        self._rsz_fmt_in.pack(fill="x", padx=self.pd(24))

        self._rsz_entry_out = self._folder_row(frame, None, "Output Folder", "resized")

        self._divider(frame)
        self._label(frame, "TARGET SIZE")
        chips = ctk.CTkFrame(frame, fg_color="transparent")
        chips.pack(fill="x", padx=self.pd(24))
        for i, (label, _) in enumerate(PRESET_SIZES):
            chips.columnconfigure(i, weight=1)
        for i, (label, _) in enumerate(PRESET_SIZES):
            b = ctk.CTkButton(
                chips, text=label, height=self.ht(34), corner_radius=8,
                fg_color=BG_ELEVATED, hover_color=BTN_HOVER,
                text_color=TXT_MUTED, border_width=1, border_color=BORDER,
                font=("Segoe UI", self.fs(11)),
                command=lambda idx=i: self._rsz_select_preset(idx),
            )
            b.grid(row=0, column=i, sticky="ew", padx=(0, self.pd(6) if i < len(PRESET_SIZES)-1 else 0))
            self._rsz_chip_btns.append(b)

        self._rsz_custom = ctk.CTkFrame(frame, fg_color="transparent")
        self._rsz_custom.pack(fill="x", padx=self.pd(24), pady=(self.pd(6), 0))
        self._rsz_entry_w = self._entry(self._rsz_custom, width=200, placeholder_text="Width px")
        self._rsz_entry_w.pack(side="left", padx=(0, self.pd(8)))
        self._rsz_entry_h = self._entry(self._rsz_custom, width=200, placeholder_text="Height px")
        self._rsz_entry_h.pack(side="left")
        self._rsz_custom.pack_forget()

        self._rsz_select_preset(1)

        self._divider(frame)
        skip_bg = ctk.CTkFrame(frame, fg_color="#1e1e1e", corner_radius=8,
                                border_color=BORDER, border_width=1)
        skip_bg.pack(fill="x", padx=self.pd(24))
        skip_inner = ctk.CTkFrame(skip_bg, fg_color="transparent")
        skip_inner.pack(fill="x", padx=self.pd(14), pady=self.pd(12))
        self._rsz_skip_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            skip_inner, text="",
            variable=self._rsz_skip_var,
            onvalue=True, offvalue=False,
            switch_width=self.ht(34), switch_height=self.ht(20),
            button_color="#888888", button_hover_color="#aaaaaa",
            progress_color="#555555", fg_color="#2e2e2e",
        ).pack(side="left", padx=(0, self.pd(12)))
        txt_col = ctk.CTkFrame(skip_inner, fg_color="transparent")
        txt_col.pack(side="left")
        ctk.CTkLabel(txt_col, text="Skip images at or below target resolution",
                     font=("Segoe UI", self.fs(12)), text_color=TXT_PRIMARY, anchor="w").pack(anchor="w")
        ctk.CTkLabel(txt_col, text="Images ≤ selected size will be ignored",
                     font=("Segoe UI", self.fs(10)), text_color=TXT_MUTED, anchor="w").pack(anchor="w")

        self._divider(frame)
        self._rsz_status, self._rsz_counter, self._rsz_bar = self._progress_row(frame)
        self._rsz_log = self._log_widget(frame)

        self._rsz_btn = ctk.CTkButton(
            frame, text="Resize images",
            font=("Segoe UI Semibold", self.fs(14)),
            fg_color=BG_ELEVATED, hover_color=BTN_HOVER,
            text_color=TXT_PRIMARY, border_width=1, border_color=BORDER,
            height=self.ht(46), corner_radius=8,
            command=self._rsz_start,
        )
        self._rsz_btn.pack(fill="x", padx=self.pd(24), pady=(0, self.pd(4)))


        return frame

    def _rsz_pick_folder(self):
        f = filedialog.askdirectory()
        if f:
            self._rsz_files = []
            self._rsz_entry_in.delete(0, tk.END)
            self._rsz_entry_in.insert(0, f)

    def _rsz_pick_files(self):
        files = filedialog.askopenfilenames(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.tif"), ("All", "*.*")])
        if files:
            self._rsz_files = list(files)
            self._rsz_entry_in.delete(0, tk.END)
            self._rsz_entry_in.insert(0, f"{len(files)} files selected")

    def _rsz_select_preset(self, idx):
        self._rsz_preset = idx
        for i, b in enumerate(self._rsz_chip_btns):
            if i == idx:
                b.configure(fg_color=BG_ACTIVE, border_color="#555555", text_color=WHITE)
            else:
                b.configure(fg_color=BG_ELEVATED, border_color=BORDER, text_color=TXT_MUTED)
        if PRESET_SIZES[idx][1] is None:
            self._rsz_custom.pack(fill="x", padx=self.pd(24), pady=(self.pd(6), 0))
        else:
            self._rsz_custom.pack_forget()

    def _rsz_get_inputs(self):
        exts = EXT_MAP_IMG[self._rsz_fmt_in.get()]
        if self._rsz_files:
            return [f for f in self._rsz_files if os.path.splitext(f)[1].lower() in exts]
        folder = self._rsz_entry_in.get().strip()
        if not folder or not os.path.isdir(folder):
            return []
        return [os.path.join(folder, f) for f in os.listdir(folder)
                if os.path.splitext(f)[1].lower() in exts]

    def _rsz_get_size(self):
        _, size = PRESET_SIZES[self._rsz_preset]
        if size:
            return size
        try:
            w = int(self._rsz_entry_w.get())
            h = int(self._rsz_entry_h.get())
            if w > 0 and h > 0:
                return (w, h)
        except ValueError:
            pass
        return None

    def _rsz_start(self):
        files = self._rsz_get_inputs()
        out   = self._rsz_entry_out.get().strip()
        size  = self._rsz_get_size()
        if not files:
            messagebox.showerror("Error", "No images found with the selected format.")
            return
        if not out:
            messagebox.showerror("Error", "Please select an output folder.")
            return
        if not size:
            messagebox.showerror("Error", "Please enter a valid width and height.")
            return
        ancho, alto = size
        self._rsz_bar.set(0)
        self._rsz_counter.configure(text=f"0 / {len(files)}")
        self._log_clear(self._rsz_log)
        self._rsz_status.configure(text="Processing…")
        self._rsz_btn.configure(state="disabled", text="Resizing…")
        threading.Thread(
            target=redimensionar_imagenes,
            args=(files, out, ancho, alto,
                  lambda d, t: (self.after(0, lambda: self._rsz_bar.set(d/t)),
                                self.after(0, lambda: self._rsz_counter.configure(text=f"{d} / {t}"))),
                  lambda txt: self._log_write(self._rsz_log, txt),
                  self._rsz_fin),
            kwargs={"ignorar_menores": self._rsz_skip_var.get()},
            daemon=True,
        ).start()

    def _rsz_fin(self, ok, errores, omitidas):
        def _d():
            self._rsz_btn.configure(state="normal", text="Resize images")
            self._rsz_status.configure(text="Done")
            msg = f"Completed: {ok} resized"
            if omitidas:
                msg += f"  ·  {omitidas} skipped"
            if errores:
                msg += f"  ·  {errores} errors"
            messagebox.showinfo("Done", msg)
        self.after(0, _d)

    # ==========================================================
    # TAB 3 — DDS CONVERTER
    # ==========================================================
    def _build_dds(self, parent):
        self._dds_files       = []
        self._dds_mode        = "TO_DDS"
        self._dds_fmt         = "AUTO"
        self._dds_img_fmt     = "PNG"
        self._dds_mipmaps     = True

        frame = ctk.CTkScrollableFrame(parent, fg_color=BG_BASE,
                                        scrollbar_button_color=BG_ELEVATED,
                                        scrollbar_button_hover_color=BTN_HOVER)

        ctk.CTkFrame(frame, fg_color="transparent", height=8).pack()
        # MODE TOGGLE
        self._divider(frame)
        self._dds_btn_mode = ctk.CTkButton(
            frame, text="⇄  Switch to DDS → Image",
            font=("Segoe UI", self.fs(11)),
            fg_color=BG_ELEVATED, hover_color=BTN_HOVER,
            text_color=TXT_PRIMARY, border_width=1, border_color=BORDER,
            height=self.ht(32), corner_radius=8,
            command=self._dds_toggle_mode,
        )
        self._dds_btn_mode.pack(fill="x", padx=self.pd(24))

        # TEXCONV
        self._divider(frame)
        self._label(frame, "TEXCONV.EXE")
        tc_row = ctk.CTkFrame(frame, fg_color="transparent")
        tc_row.pack(fill="x", padx=self.pd(24))
        tc_row.columnconfigure(0, weight=1)
        self._dds_entry_tc = self._entry(tc_row, placeholder_text="Path to texconv.exe…")
        auto = self._res("texconv.exe")
        if os.path.exists(auto):
            self._dds_entry_tc.insert(0, auto)
        self._dds_entry_tc.grid(row=0, column=0, sticky="ew", padx=(0, self.pd(8)))
        self._btn(tc_row, "…", self._dds_pick_texconv,
                  width=self.ht(34)).grid(row=0, column=1)
        ctk.CTkLabel(frame, text="  Download from: github.com/microsoft/DirectXTex/releases",
                     font=("Segoe UI", self.fs(8)), text_color=TXT_MUTED
                     ).pack(anchor="w", padx=self.pd(24), pady=(self.pd(2), 0))

        # INPUT
        self._divider(frame)
        self._dds_lbl_input = self._label_ref(frame, "INPUT  ( Image → DDS )")
        self._dds_entry_in  = self._entry(frame, placeholder_text="Select a folder or files…")
        self._dds_entry_in.pack(fill="x", padx=self.pd(24), pady=(0, self.pd(6)))
        io_row = ctk.CTkFrame(frame, fg_color="transparent")
        io_row.pack(fill="x", padx=self.pd(24))
        io_row.columnconfigure(0, weight=1)
        io_row.columnconfigure(1, weight=1)
        self._btn(io_row, "  Folder", self._dds_pick_folder).grid(row=0, column=0, sticky="ew", padx=(0, self.pd(6)))
        self._btn(io_row, "  Files",  self._dds_pick_files).grid(row=0, column=1, sticky="ew")

        # OUTPUT
        self._divider(frame)
        self._label(frame, "OUTPUT FOLDER")
        out_row = ctk.CTkFrame(frame, fg_color="transparent")
        out_row.pack(fill="x", padx=self.pd(24))
        out_row.columnconfigure(0, weight=1)
        self._dds_entry_out = self._entry(out_row)
        self._dds_entry_out.insert(0, "dds_output")
        self._dds_entry_out.grid(row=0, column=0, sticky="ew", padx=(0, self.pd(8)))
        self._btn(out_row, "…", lambda: self._pick_out(self._dds_entry_out),
                  width=self.ht(34)).grid(row=0, column=1)

        # DYNAMIC BODY
        self._dds_body = ctk.CTkFrame(frame, fg_color="transparent")
        self._dds_body.pack(fill="x")

        # Frame TO_DDS
        self._dds_frame_to_dds = ctk.CTkFrame(self._dds_body, fg_color="transparent")
        self._divider(self._dds_frame_to_dds)
        self._label(self._dds_frame_to_dds, "FILTER BY FORMAT")
        self._dds_fmt_in = ctk.CTkOptionMenu(
            self._dds_frame_to_dds, values=list(EXT_MAP_IMG.keys()),
            height=self.ht(34), corner_radius=8,
            fg_color=BG_PANEL, button_color=BG_ELEVATED,
            button_hover_color=BTN_HOVER, text_color=TXT_PRIMARY,
            dropdown_fg_color=BG_PANEL, dropdown_text_color=TXT_PRIMARY,
            dropdown_hover_color=BG_ELEVATED, font=("Segoe UI", self.fs(12)),
        )
        self._dds_fmt_in.set("All formats")
        self._dds_fmt_in.pack(fill="x", padx=self.pd(24))

        self._divider(self._dds_frame_to_dds)
        self._label(self._dds_frame_to_dds, "DDS FORMAT")
        self._dds_fmt_btns = {}
        dds_row = ctk.CTkFrame(self._dds_frame_to_dds, fg_color="transparent")
        dds_row.pack(fill="x", padx=self.pd(24))
        keys = list(DDS_OUT_FORMATS.keys())
        for i in range(len(keys)):
            dds_row.columnconfigure(i, weight=1)
        for i, (label, val) in enumerate(DDS_OUT_FORMATS.items()):
            active = (val == "AUTO")
            b = ctk.CTkButton(
                dds_row, text=label, height=self.ht(30), corner_radius=8,
                fg_color=BG_ACTIVE if active else BG_ELEVATED,
                hover_color=BTN_HOVER,
                text_color=WHITE if active else TXT_PRIMARY,
                border_width=1, border_color="#555555" if active else BORDER,
                font=("Segoe UI", self.fs(10)),
                command=lambda v=val: self._dds_select_fmt(v),
            )
            b.grid(row=0, column=i, sticky="ew", padx=(0, self.pd(5) if i < len(keys)-1 else 0))
            self._dds_fmt_btns[val] = b

        self._dds_desc = ctk.CTkLabel(
            self._dds_frame_to_dds,
            text="  Auto: BC3 with alpha, BC1 without — recommended for FiveM",
            font=("Segoe UI", self.fs(8)), text_color=TXT_MUTED,
        )
        self._dds_desc.pack(anchor="w", padx=self.pd(24), pady=(self.pd(3), 0))

        self._divider(self._dds_frame_to_dds)
        mip_row = ctk.CTkFrame(self._dds_frame_to_dds, fg_color="transparent")
        mip_row.pack(fill="x", padx=self.pd(24), pady=(0, self.pd(3)))
        mip_info = ctk.CTkFrame(mip_row, fg_color="transparent")
        mip_info.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(mip_info, text="Generate Mipmaps",
                     font=("Segoe UI", self.fs(11)), text_color=TXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(mip_info, text="Required for FiveM textures",
                     font=("Segoe UI", self.fs(8)), text_color=TXT_MUTED).pack(anchor="w")
        self._dds_mip_sw = ctk.CTkSwitch(
            mip_row, text="", onvalue=True, offvalue=False,
            fg_color=BG_ELEVATED, progress_color=BG_ACTIVE,
            button_color=TXT_PRIMARY, button_hover_color=WHITE,
            command=lambda: setattr(self, "_dds_mipmaps", bool(self._dds_mip_sw.get())),
        )
        self._dds_mip_sw.select()
        self._dds_mip_sw.pack(side="right")
        self._dds_frame_to_dds.pack(fill="x")

        # Frame TO_IMG
        self._dds_frame_to_img = ctk.CTkFrame(self._dds_body, fg_color="transparent")
        self._divider(self._dds_frame_to_img)
        self._label(self._dds_frame_to_img, "OUTPUT FORMAT")
        self._dds_img_btns = {}
        img_row = ctk.CTkFrame(self._dds_frame_to_img, fg_color="transparent")
        img_row.pack(fill="x", padx=self.pd(24))
        for i in range(len(IMG_OUT_FORMATS)):
            img_row.columnconfigure(i, weight=1)
        for i, fmt in enumerate(IMG_OUT_FORMATS):
            active = (fmt == "PNG")
            b = ctk.CTkButton(
                img_row, text=fmt, height=self.ht(30), corner_radius=8,
                fg_color=BG_ACTIVE if active else BG_ELEVATED,
                hover_color=BTN_HOVER,
                text_color=WHITE if active else TXT_PRIMARY,
                border_width=1, border_color="#555555" if active else BORDER,
                font=("Segoe UI", self.fs(10)),
                command=lambda f=fmt: self._dds_select_img_fmt(f),
            )
            b.grid(row=0, column=i, sticky="ew", padx=(0, self.pd(5) if i < len(IMG_OUT_FORMATS)-1 else 0))
            self._dds_img_btns[fmt] = b

        # SHARED: STATUS + LOG + PROGRESS + BUTTON
        self._divider(frame)
        self._dds_status, self._dds_counter, self._dds_bar = self._progress_row(frame)
        self._dds_log = self._log_widget(frame)

        self._dds_btn = ctk.CTkButton(
            frame, text="Convert",
            font=("Segoe UI Semibold", self.fs(14)),
            fg_color=BG_ELEVATED, hover_color=BTN_HOVER,
            text_color=TXT_PRIMARY, border_width=1, border_color=BORDER,
            height=self.ht(46), corner_radius=8,
            command=self._dds_start,
        )
        self._dds_btn.pack(fill="x", padx=self.pd(24), pady=(0, self.pd(4)))


        return frame

    def _label_ref(self, parent, text):
        lbl = ctk.CTkLabel(parent, text=text,
                            font=("Segoe UI", self.fs(9), "bold"),
                            text_color=TXT_MUTED)
        lbl.pack(anchor="w", padx=self.pd(24), pady=(0, self.pd(4)))
        return lbl

    def _dds_toggle_mode(self):
        self._dds_files = []
        self._dds_entry_in.delete(0, tk.END)
        self._log_clear(self._dds_log)
        self._dds_status.configure(text="Ready")
        self._dds_bar.set(0)
        self._dds_counter.configure(text="0 / 0")
        if self._dds_mode == "TO_DDS":
            self._dds_mode = "TO_IMG"
            self._dds_btn_mode.configure(text="⇄  Switch to Image → DDS")
            self._dds_lbl_input.configure(text="INPUT  ( DDS → Image )")
            self._dds_entry_in.configure(placeholder_text="Select DDS files or folder…")
            self._dds_entry_out.delete(0, tk.END)
            self._dds_entry_out.insert(0, "img_output")
            self._dds_frame_to_dds.pack_forget()
            self._dds_frame_to_img.pack(fill="x")
        else:
            self._dds_mode = "TO_DDS"
            self._dds_btn_mode.configure(text="⇄  Switch to DDS → Image")
            self._dds_lbl_input.configure(text="INPUT  ( Image → DDS )")
            self._dds_entry_in.configure(placeholder_text="Select a folder or files…")
            self._dds_entry_out.delete(0, tk.END)
            self._dds_entry_out.insert(0, "dds_output")
            self._dds_frame_to_img.pack_forget()
            self._dds_frame_to_dds.pack(fill="x")

    def _dds_pick_texconv(self):
        f = filedialog.askopenfilename(
            title="Select texconv.exe",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")])
        if f:
            self._dds_entry_tc.delete(0, tk.END)
            self._dds_entry_tc.insert(0, f)

    def _dds_pick_folder(self):
        f = filedialog.askdirectory()
        if f:
            self._dds_files = []
            self._dds_entry_in.delete(0, tk.END)
            self._dds_entry_in.insert(0, f)

    def _dds_pick_files(self):
        if self._dds_mode == "TO_DDS":
            ft = [("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.tif"), ("All", "*.*")]
        else:
            ft = [("DDS files", "*.dds"), ("All files", "*.*")]
        files = filedialog.askopenfilenames(filetypes=ft)
        if files:
            self._dds_files = list(files)
            self._dds_entry_in.delete(0, tk.END)
            self._dds_entry_in.insert(0, f"{len(files)} files selected")

    def _dds_select_fmt(self, val):
        for v, b in self._dds_fmt_btns.items():
            if v == val:
                b.configure(fg_color=BG_ACTIVE, text_color=WHITE, border_color="#555555")
            else:
                b.configure(fg_color=BG_ELEVATED, text_color=TXT_PRIMARY, border_color=BORDER)
        self._dds_fmt = val
        descs = {
            "AUTO":      "Auto: BC3 with alpha, BC1 without — recommended for FiveM",
            "BC3_UNORM": "BC3 / DXT5: compression with transparency. For clothing, props…",
            "BC1_UNORM": "BC1 / DXT1: compression without alpha. For backgrounds, floors…",
            "BC7_UNORM": "BC7: maximum quality, larger file. For high-definition textures.",
            "BC4_UNORM": "BC4: grayscale / roughness and metallic maps.",
        }
        self._dds_desc.configure(text="  " + descs.get(val, ""))

    def _dds_select_img_fmt(self, fmt):
        for f, b in self._dds_img_btns.items():
            if f == fmt:
                b.configure(fg_color=BG_ACTIVE, text_color=WHITE, border_color="#555555")
            else:
                b.configure(fg_color=BG_ELEVATED, text_color=TXT_PRIMARY, border_color=BORDER)
        self._dds_img_fmt = fmt

    def _dds_get_inputs(self):
        exts = EXT_MAP_IMG[self._dds_fmt_in.get()] if self._dds_mode == "TO_DDS" else [".dds"]
        if self._dds_files:
            return [f for f in self._dds_files if os.path.splitext(f)[1].lower() in exts]
        folder = self._dds_entry_in.get().strip()
        if not folder or not os.path.isdir(folder):
            return []
        return [os.path.join(folder, f) for f in os.listdir(folder)
                if os.path.splitext(f)[1].lower() in exts]

    def _dds_start(self):
        tc    = self._dds_entry_tc.get().strip()
        out   = self._dds_entry_out.get().strip()
        files = self._dds_get_inputs()
        if not tc or not os.path.exists(tc):
            messagebox.showerror("texconv.exe not found",
                "Please select the path to texconv.exe.\n"
                "Download it from: github.com/microsoft/DirectXTex/releases")
            return
        if not files:
            messagebox.showerror("Error", "No files found with the selected format.")
            return
        if not out:
            messagebox.showerror("Error", "Please select an output folder.")
            return
        self._dds_bar.set(0)
        self._dds_counter.configure(text=f"0 / {len(files)}")
        self._log_clear(self._dds_log)
        self._dds_status.configure(text="Converting…")
        self._dds_btn.configure(state="disabled", text="Converting…")
        if self._dds_mode == "TO_DDS":
            threading.Thread(
                target=convert_to_dds,
                args=(files, out, self._dds_fmt, self._dds_mipmaps,
                      lambda d, t: (self.after(0, lambda: self._dds_bar.set(d/t)),
                                    self.after(0, lambda: self._dds_counter.configure(text=f"{d} / {t}"))),
                      lambda txt: self._log_write(self._dds_log, txt),
                      self._dds_fin, tc),
                daemon=True,
            ).start()
        else:
            threading.Thread(
                target=convert_dds_to_img,
                args=(files, out, self._dds_img_fmt,
                      lambda d, t: (self.after(0, lambda: self._dds_bar.set(d/t)),
                                    self.after(0, lambda: self._dds_counter.configure(text=f"{d} / {t}"))),
                      lambda txt: self._log_write(self._dds_log, txt),
                      self._dds_fin, tc),
                daemon=True,
            ).start()

    def _dds_fin(self, ok, errors):
        def _d():
            self._dds_btn.configure(state="normal", text="Convert")
            self._dds_status.configure(text="Done")
            msg = f"Converted: {ok} file{'s' if ok != 1 else ''}"
            if errors:
                msg += f"\nErrors: {errors}"
            messagebox.showinfo("Done", msg)
        self.after(0, _d)


# ==========================================================
# EJECUCIÓN
# ==========================================================
if __name__ == "__main__":
    app = AteneaToolkit()
    app.mainloop()
