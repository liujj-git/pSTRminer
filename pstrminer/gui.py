#!/usr/bin/env python3
"""
pSTRminer GUI - Tkinter graphical interface
===========================================
Three tabs:
  Step 1 - STR Configuration      (HipSTR_configuration.sh)
  Step 2 - Polymorphism Screening (Polymorphism.sh)
  Help                            (in-app usage guide)

Each analysis tab has a parameter panel (left, grouped into cards),
a real-time execution log (right), Run / Stop buttons and a status bar.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import sys
import os
from pathlib import Path
from pstrminer import __version__
from pstrminer.pipeline import run_hipstr_configuration, run_polymorphism

# =============================================================
#  Colour palette
#  (light, print-friendly - suitable for figures in a paper)
# =============================================================
BG          = "#EEF1F6"      # window / canvas (light grey)
PANEL_BG    = "#FFFFFF"      # cards
CARD_BORDER = "#DCE1EA"      # card outline
DIVIDER     = "#E7EBF1"      # thin rules inside cards
ACCENT      = "#2563EB"      # primary blue
ACCENT_HOV  = "#1D4ED8"
DANGER      = "#DC2626"
DANGER_HOV  = "#B91C1C"
SUCCESS     = "#15803D"
WARN        = "#B45309"
TEXT        = "#1E293B"
MUTED       = "#64748B"
FIELD_LINE  = "#CBD3DF"      # entry border

# --- log console (now LIGHT instead of dark terminal) --------
LOG_BG      = "#FFFFFF"
LOG_FG      = "#334155"      # default log text (readable dark)
LOG_INFO    = "#1D4ED8"
LOG_WARN    = "#B45309"
LOG_ERR     = "#DC2626"
LOG_OK      = "#15803D"
LOG_DIM     = "#94A3B8"

# =============================================================
#  Fonts
#  User request: cleaner, larger type (Microsoft YaHei / Times
#  New Roman family).  We default to a clean sans stack and pick
#  the best face actually installed at run time.  Flip
#  USE_SERIF_UI to True for a Times New Roman / serif look.
# =============================================================
USE_SERIF_UI = False

_SANS_STACK = [
    "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", "PingFang SC",
    "Noto Sans CJK SC", "Source Han Sans SC", "Noto Sans SC",
    "Helvetica Neue", "Liberation Sans", "DejaVu Sans", "Arial",
]
_SERIF_STACK = [
    "Times New Roman", "Times", "Songti SC", "Noto Serif CJK SC",
    "Source Han Serif SC", "Liberation Serif", "DejaVu Serif", "Georgia",
]
_MONO_STACK = [
    "Consolas", "SF Mono", "JetBrains Mono", "Cascadia Mono", "Menlo",
    "Noto Sans Mono", "Liberation Mono", "DejaVu Sans Mono", "Courier New",
]

# Safe placeholder families (re-resolved once a Tk root exists).
FONT_FAMILY = "Liberation Serif" if USE_SERIF_UI else "Liberation Sans"
MONO_FAMILY = "Liberation Mono"

# Placeholder font tuples so the module imports before a root exists.
FONT_BODY    = (FONT_FAMILY, 12)
FONT_SMALL   = (FONT_FAMILY, 11)
FONT_H2      = (FONT_FAMILY, 13, "bold")
FONT_H1      = (FONT_FAMILY, 17, "bold")
FONT_TITLE   = (FONT_FAMILY, 22, "bold")
FONT_TAGLINE = (FONT_FAMILY, 12)
FONT_BTN     = (FONT_FAMILY, 12, "bold")
FONT_MONO    = (MONO_FAMILY, 11)
FONT_HELP_H1 = (FONT_FAMILY, 16, "bold")


def _pick_family(candidates, fallback):
    """Return the first installed family from *candidates*."""
    try:
        import tkinter.font as tkfont
        available = {f.lower() for f in tkfont.families()}
        for name in candidates:
            if name.lower() in available:
                return name
    except Exception:
        pass
    return fallback


def resolve_fonts(root):
    """Choose the best available faces and set global font tuples.

    Must be called after a Tk root has been created.
    """
    global FONT_FAMILY, MONO_FAMILY
    global FONT_BODY, FONT_SMALL, FONT_H2, FONT_H1, FONT_TITLE
    global FONT_TAGLINE, FONT_BTN, FONT_MONO, FONT_HELP_H1

    FONT_FAMILY = _pick_family(_SERIF_STACK if USE_SERIF_UI else _SANS_STACK,
                               FONT_FAMILY)
    MONO_FAMILY = _pick_family(_MONO_STACK, MONO_FAMILY)

    FONT_BODY    = (FONT_FAMILY, 12)
    FONT_SMALL   = (FONT_FAMILY, 11)
    FONT_H2      = (FONT_FAMILY, 13, "bold")
    FONT_H1      = (FONT_FAMILY, 17, "bold")
    FONT_TITLE   = (FONT_FAMILY, 22, "bold")
    FONT_TAGLINE = (FONT_FAMILY, 12)
    FONT_BTN     = (FONT_FAMILY, 12, "bold")
    FONT_MONO    = (MONO_FAMILY, 11)
    FONT_HELP_H1 = (FONT_FAMILY, 16, "bold")

    # Make the default named fonts match, so ttk widgets and dialogs
    # inherit the same look.
    try:
        import tkinter.font as tkfont
        for nm in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            try:
                tkfont.nametofont(nm).configure(family=FONT_FAMILY, size=12)
            except Exception:
                pass
        try:
            tkfont.nametofont("TkFixedFont").configure(family=MONO_FAMILY, size=11)
        except Exception:
            pass
    except Exception:
        pass


# layout constants
PAD    = 14      # inner padding of a card
GAP    = 10      # vertical gap between cards
LEFT_W = 500     # fixed width of the parameter column


# =============================================================
#  Small reusable widgets
# =============================================================

class _Tooltip:
    """Hover help bubble."""
    def __init__(self, widget, text):
        self._text = text
        self._tip = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, event=None):
        x = event.widget.winfo_rootx() + 20
        y = event.widget.winfo_rooty() + 26
        self._tip = tw = tk.Toplevel()
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=self._text, font=FONT_SMALL,
                 bg="#FEF9C3", fg=TEXT, relief="solid", borderwidth=1,
                 padx=8, pady=5, wraplength=340, justify="left").pack()

    def _hide(self, event=None):
        if self._tip:
            self._tip.destroy()
            self._tip = None


class Card(tk.Frame):
    """A titled white 'card' with a thin border.  Pack content into .body."""
    def __init__(self, parent, title=None):
        super().__init__(parent, bg=PANEL_BG, highlightthickness=1,
                         highlightbackground=CARD_BORDER, bd=0)
        if title:
            tk.Label(self, text=title, font=FONT_H2, fg=ACCENT, bg=PANEL_BG,
                     anchor="w").pack(fill="x", padx=PAD, pady=(11, 0))
            tk.Frame(self, bg=DIVIDER, height=1).pack(fill="x",
                                                      padx=PAD, pady=(8, 2))
        self.body = tk.Frame(self, bg=PANEL_BG)
        self.body.pack(fill="both", expand=True, padx=PAD, pady=(4, 12))

    def hint(self, text):
        """Add a small muted explanatory line to the body."""
        tk.Label(self.body, text=text, font=FONT_SMALL, fg=MUTED, bg=PANEL_BG,
                 anchor="w", justify="left").pack(fill="x", pady=(0, 4))


class FieldRow(tk.Frame):
    """Label + stretchy Entry (+ optional Browse button) on one line."""
    def __init__(self, parent, label, browse=None, default="",
                 tooltip="", label_width=17):
        super().__init__(parent, bg=PANEL_BG)
        tk.Label(self, text=label, font=FONT_BODY, fg=TEXT, bg=PANEL_BG,
                 width=label_width, anchor="w").pack(side="left")
        self.var = tk.StringVar(value=default)
        if browse:
            tk.Button(self, text="Browse", font=FONT_SMALL, fg=TEXT,
                      bg="#EEF2F8", activebackground="#E2E8F2",
                      relief="flat", cursor="hand2", padx=10, pady=3,
                      command=browse).pack(side="right", padx=(8, 0))
        self.entry = tk.Entry(self, textvariable=self.var, font=FONT_BODY,
                              relief="flat", highlightthickness=1,
                              highlightbackground=FIELD_LINE,
                              highlightcolor=ACCENT, bg="#FFFFFF")
        self.entry.pack(side="left", fill="x", expand=True, ipady=3)
        if tooltip:
            _Tooltip(self.entry, tooltip)

    def get(self):
        return self.var.get().strip()

    def set(self, v):
        self.var.set(v)


class NumRow(tk.Frame):
    """Label + short numeric Entry, right-aligned."""
    def __init__(self, parent, label, default, tooltip="", label_width=24):
        super().__init__(parent, bg=PANEL_BG)
        tk.Label(self, text=label, font=FONT_BODY, fg=TEXT, bg=PANEL_BG,
                 width=label_width, anchor="w").pack(side="left")
        self.var = tk.StringVar(value=str(default))
        self.entry = tk.Entry(self, textvariable=self.var, font=FONT_BODY,
                              width=9, relief="flat", justify="right",
                              highlightthickness=1,
                              highlightbackground=FIELD_LINE,
                              highlightcolor=ACCENT, bg="#FFFFFF")
        self.entry.pack(side="right", ipady=2)
        if tooltip:
            _Tooltip(self.entry, tooltip)

    def get(self):
        return self.var.get().strip()


class LogConsole(tk.Frame):
    """Light, scrollable log with colour-coded lines."""
    def __init__(self, parent):
        super().__init__(parent, bg=LOG_BG, highlightthickness=1,
                         highlightbackground=CARD_BORDER)
        self._txt = scrolledtext.ScrolledText(
            self, font=FONT_MONO, bg=LOG_BG, fg=LOG_FG,
            insertbackground=LOG_FG, relief="flat", state="disabled",
            wrap="word", padx=10, pady=8, borderwidth=0,
        )
        self._txt.pack(fill="both", expand=True, padx=2, pady=2)
        self._txt.tag_config("info",  foreground=LOG_INFO)
        self._txt.tag_config("warn",  foreground=LOG_WARN)
        self._txt.tag_config("error", foreground=LOG_ERR)
        self._txt.tag_config("ok",    foreground=LOG_OK, font=(FONT_MONO[0], 11, "bold"))
        self._txt.tag_config("dim",   foreground=LOG_DIM)

    def _tag(self, line: str):
        lo = line.lower()
        if any(k in lo for k in ("error", "[error]", "traceback", "failed", "no such", "\u2717")):
            return "error"
        if any(k in lo for k in ("warning", "[warn]", "skipping")):
            return "warn"
        if any(k in lo for k in ("completed", "success", "done", "finished", "[ok]", "\u2713")):
            return "ok"
        if any(k in lo for k in ("[step]", "[info]", "[pstrminer]", "substep")):
            return "info"
        if line.startswith("Welcome"):
            return "dim"
        return ""     # plain, readable default colour

    def append(self, line: str):
        tag = self._tag(line)
        self._txt.configure(state="normal")
        if tag:
            self._txt.insert("end", line + "\n", tag)
        else:
            self._txt.insert("end", line + "\n")
        self._txt.see("end")
        self._txt.configure(state="disabled")

    def clear(self):
        self._txt.configure(state="normal")
        self._txt.delete("1.0", "end")
        self._txt.configure(state="disabled")


class RunButton(tk.Button):
    def __init__(self, parent, text, command):
        super().__init__(parent, text=text, command=command, font=FONT_BTN,
                         bg=ACCENT, fg="white", activebackground=ACCENT_HOV,
                         activeforeground="white", relief="flat",
                         cursor="hand2", padx=22, pady=9, bd=0)
        self.bind("<Enter>", lambda e: self.config(bg=ACCENT_HOV))
        self.bind("<Leave>", lambda e: self.config(bg=ACCENT))


class StopButton(tk.Button):
    def __init__(self, parent, command):
        super().__init__(parent, text="Stop", command=command, font=FONT_BTN,
                         bg=DANGER, fg="white", activebackground=DANGER_HOV,
                         activeforeground="white", relief="flat",
                         cursor="hand2", padx=18, pady=9, bd=0,
                         state="disabled")
        self.bind("<Enter>", lambda e: self.config(bg=DANGER_HOV)
                  if str(self["state"]) != "disabled" else None)
        self.bind("<Leave>", lambda e: self.config(bg=DANGER)
                  if str(self["state"]) != "disabled" else None)


class LinkButton(tk.Button):
    """Subtle text button (used for 'Clear log')."""
    def __init__(self, parent, text, command):
        super().__init__(parent, text=text, command=command, font=FONT_SMALL,
                         fg=MUTED, bg=BG, activebackground=BG,
                         activeforeground=ACCENT, relief="flat",
                         cursor="hand2", bd=0, padx=2)


class StatusBar(tk.Frame):
    """Thin coloured status strip."""
    IDLE    = ("#E2E8F0", TEXT,    "Ready")
    RUNNING = (WARN,      "white", "Running\u2026")
    OK      = (SUCCESS,   "white", "Completed successfully")
    FAIL    = (DANGER,    "white", "Finished with errors")

    def __init__(self, parent):
        super().__init__(parent, height=30)
        self._lbl = tk.Label(self, font=FONT_SMALL, anchor="w", padx=12)
        self._lbl.pack(fill="both", expand=True)
        self.set_idle()

    def _apply(self, state):
        bg, fg, txt = state
        self.config(bg=bg)
        self._lbl.config(bg=bg, fg=fg, text=txt)

    def set_idle(self):    self._apply(self.IDLE)
    def set_running(self): self._apply(self.RUNNING)
    def set_ok(self):      self._apply(self.OK)
    def set_fail(self):    self._apply(self.FAIL)


def _two_columns(tab):
    """Create the standard left (parameters) / right (log) columns."""
    left = tk.Frame(tab, bg=BG, width=LEFT_W)
    left.pack(side="left", fill="y", padx=(14, 7), pady=14)
    left.pack_propagate(False)

    right = tk.Frame(tab, bg=BG)
    right.pack(side="left", fill="both", expand=True, padx=(7, 14), pady=14)
    return left, right


def _title_block(parent, title, subtitle):
    tk.Label(parent, text=title, font=FONT_H1, fg=TEXT, bg=BG,
             anchor="w").pack(fill="x")
    tk.Label(parent, text=subtitle, font=FONT_SMALL, fg=MUTED, bg=BG,
             anchor="w").pack(fill="x", pady=(1, 10))


def _log_panel(parent):
    tk.Label(parent, text="Execution Log", font=FONT_H2, fg=TEXT, bg=BG,
             anchor="w").pack(fill="x", pady=(0, 6))
    console = LogConsole(parent)
    console.pack(fill="both", expand=True)
    return console


# =============================================================
#  Tab 1 - STR Configuration
# =============================================================

class ConfigTab(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG)
        self._thread = None
        self._build()

    def _build(self):
        left, right = _two_columns(self)

        # status bar pinned to the bottom of the column
        self._status = StatusBar(left)
        self._status.pack(side="bottom", fill="x")

        _title_block(left, "STR Configuration",
                     "Find STRs in a reference genome and build a HipSTR "
                     "configuration")

        # --- Reference genome (local first, default local) ----
        ref = Card(left, "Reference Genome Source")
        ref.pack(fill="x", pady=(0, GAP))
        self._mode = tk.StringVar(value="local")
        rf = tk.Frame(ref.body, bg=PANEL_BG)
        rf.pack(fill="x", pady=(0, 6))
        tk.Radiobutton(rf, text="Use a local FASTA file", variable=self._mode,
                       value="local", bg=PANEL_BG, activebackground=PANEL_BG,
                       font=FONT_BODY, command=self._toggle_mode).pack(
            side="left", padx=(0, 14))
        tk.Radiobutton(rf, text="Download from UCSC", variable=self._mode,
                       value="ucsc", bg=PANEL_BG, activebackground=PANEL_BG,
                       font=FONT_BODY, command=self._toggle_mode).pack(
            side="left")

        self._fasta_row = FieldRow(
            ref.body, "Local FASTA file", browse=self._browse_fasta,
            tooltip="Path to a reference genome in FASTA format "
                    "(.fa / .fasta / .fna)")
        self._fasta_row.pack(fill="x", pady=3)

        self._genome_row = FieldRow(
            ref.body, "UCSC assembly ID", default="bosTau9",
            tooltip="A UCSC genome assembly ID, e.g. bosTau9, hg38, mm10, "
                    "galGal6. Requires internet access.")
        self._genome_row.pack(fill="x", pady=3)

        # --- TRF (explicit auto vs local choice) --------------
        trf = Card(left, "TRF  (Tandem Repeats Finder)")
        trf.pack(fill="x", pady=(0, GAP))
        self._trf_mode = tk.StringVar(value="auto")
        tf = tk.Frame(trf.body, bg=PANEL_BG)
        tf.pack(fill="x", pady=(0, 4))
        tk.Radiobutton(tf, text="Download automatically", variable=self._trf_mode,
                       value="auto", bg=PANEL_BG, activebackground=PANEL_BG,
                       font=FONT_BODY, command=self._toggle_trf).pack(
            side="left", padx=(0, 14))
        tk.Radiobutton(tf, text="Use a local TRF binary", variable=self._trf_mode,
                       value="local", bg=PANEL_BG, activebackground=PANEL_BG,
                       font=FONT_BODY, command=self._toggle_trf).pack(side="left")
        trf.hint("Choose a local binary for offline or firewalled machines "
                 "that cannot reach GitHub.")
        self._trf_row = FieldRow(
            trf.body, "TRF binary", browse=self._browse_trf,
            tooltip="Path to a trf executable (e.g. trf409.legacylinux64).")
        self._trf_row.pack(fill="x", pady=3)

        # --- Output -------------------------------------------
        out = Card(left, "Output")
        out.pack(fill="x", pady=(0, GAP))
        self._outdir = FieldRow(
            out.body, "Output folder", browse=self._browse_outdir,
            default=str(Path.home() / "pSTRminer_output"),
            tooltip="All generated files are written here.")
        self._outdir.pack(fill="x", pady=3)

        # --- actions ------------------------------------------
        action = tk.Frame(left, bg=BG)
        action.pack(fill="x", pady=(2, 2))
        RunButton(action, "Run Configuration", self._run).pack(side="left")
        self._stop_btn = StopButton(action, self._stop)
        self._stop_btn.pack(side="left", padx=(8, 0))
        LinkButton(action, "Clear log", lambda: self._log.clear()).pack(
            side="right", pady=6)

        # --- right: log ---------------------------------------
        self._log = _log_panel(right)

        self._toggle_mode()
        self._toggle_trf()
        self._log.append("Welcome to pSTRminer. Set the options on the left, "
                         "then click Run Configuration.")

    # -- state toggles ----------------------------------------
    def _toggle_mode(self):
        local = self._mode.get() == "local"
        self._fasta_row.entry.config(state="normal" if local else "disabled")
        self._genome_row.entry.config(state="disabled" if local else "normal")

    def _toggle_trf(self):
        local = self._trf_mode.get() == "local"
        if not local:
            self._trf_row.set("")
        self._trf_row.entry.config(state="normal" if local else "disabled")

    # -- browse dialogs ---------------------------------------
    def _browse_fasta(self):
        p = filedialog.askopenfilename(
            title="Select reference FASTA",
            filetypes=[("FASTA files", "*.fa *.fasta *.fna"), ("All files", "*.*")])
        if p:
            self._fasta_row.set(p)
            self._mode.set("local")
            self._toggle_mode()

    def _browse_trf(self):
        p = filedialog.askopenfilename(title="Select TRF binary",
                                       filetypes=[("All files", "*.*")])
        if p:
            self._trf_mode.set("local")
            self._toggle_trf()
            self._trf_row.set(p)

    def _browse_outdir(self):
        p = filedialog.askdirectory(title="Select output folder")
        if p:
            self._outdir.set(p)

    # -- run / callbacks --------------------------------------
    def _log_cb(self, line):
        self._log.after(0, self._log.append, line)

    def _done_cb(self, rc):
        def _update():
            self._stop_btn.config(state="disabled")
            if rc == 0:
                self._status.set_ok()
                self._log.append("\n[pSTRminer] \u2713 Configuration completed successfully.")
            else:
                self._status.set_fail()
                self._log.append(f"\n[pSTRminer] \u2717 Process exited with code {rc}.")
        self._log.after(0, _update)

    def _run(self):
        outdir = self._outdir.get()
        if not outdir:
            messagebox.showerror("Missing input", "Please choose an output folder.")
            return

        if self._mode.get() == "ucsc":
            genome = self._genome_row.get()
            if not genome:
                messagebox.showerror("Missing input", "Please enter a UCSC assembly ID.")
                return
            kw = dict(genome_name=genome)
        else:
            fasta = self._fasta_row.get()
            if not fasta or not Path(fasta).exists():
                messagebox.showerror("Missing input", "Please select a valid FASTA file.")
                return
            kw = dict(reference_file=fasta)

        self._log.clear()
        self._status.set_running()
        self._stop_btn.config(state="normal")

        trf_path = self._trf_row.get() if self._trf_mode.get() == "local" else ""

        self._thread = run_hipstr_configuration(
            output_dir=outdir,
            trf_path=trf_path if trf_path else "",
            log_callback=self._log_cb,
            done_callback=self._done_cb,
            **kw,
        )

    def _stop(self):
        self._log.append("\n[pSTRminer] Stop requested. The current step will "
                         "finish before halting.")
        self._stop_btn.config(state="disabled")


# =============================================================
#  Tab 2 - Polymorphism Screening
# =============================================================

class PolyTab(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG)
        self._thread = None
        self._build()

    def _build(self):
        left, right = _two_columns(self)

        self._status = StatusBar(left)
        self._status.pack(side="bottom", fill="x")

        _title_block(left, "Polymorphism Screening",
                     "Filter the HipSTR VCF and compute forensic parameters")

        # --- Input files --------------------------------------
        inp = Card(left, "Input Files")
        inp.pack(fill="x", pady=(0, GAP))
        self._config_bed = FieldRow(
            inp.body, "HipSTR config BED", browse=self._browse_bed,
            tooltip="The BED produced by Step 1 (*.configuration.DitoHex.bed).",
            label_width=20)
        self._config_bed.pack(fill="x", pady=3)
        self._input_vcf = FieldRow(
            inp.body, "Input VCF", browse=self._browse_vcf,
            tooltip="A VCF / VCF.GZ genotyped by HipSTR.", label_width=20)
        self._input_vcf.pack(fill="x", pady=3)

        # --- Output -------------------------------------------
        out = Card(left, "Output")
        out.pack(fill="x", pady=(0, GAP))
        self._outdir = FieldRow(
            out.body, "Output folder", browse=self._browse_outdir,
            default=str(Path.home() / "pSTRminer_output"),
            tooltip="Folder where result files are saved.")
        self._outdir.pack(fill="x", pady=3)
        self._prefix = FieldRow(
            out.body, "Output prefix", default="pstrminer_results",
            tooltip="Prefix for output filenames "
                    "(e.g. my_study.forensic_parameters.txt).")
        self._prefix.pack(fill="x", pady=3)

        # --- Filtering ----------------------------------------
        filt = Card(left, "VCF Filtering")
        filt.pack(fill="x", pady=(0, GAP))
        self._filter_mode = tk.StringVar(value="T")
        fm = tk.Frame(filt.body, bg=PANEL_BG)
        fm.pack(fill="x", pady=(0, 6))
        tk.Radiobutton(fm, text="Filter the raw VCF", variable=self._filter_mode,
                       value="T", bg=PANEL_BG, activebackground=PANEL_BG,
                       font=FONT_BODY, command=self._toggle_filter).pack(
            side="left", padx=(0, 14))
        tk.Radiobutton(fm, text="VCF is already filtered", variable=self._filter_mode,
                       value="F", bg=PANEL_BG, activebackground=PANEL_BG,
                       font=FONT_BODY, command=self._toggle_filter).pack(side="left")

        self._filter_frame = tk.Frame(filt.body, bg=PANEL_BG)
        self._filter_frame.pack(fill="x")
        self._p_qual = NumRow(self._filter_frame, "Minimum call quality", 0.9,
            tooltip="Genotype calls below this quality are removed (0-1).")
        self._p_qual.pack(fill="x", pady=2)
        self._p_flank = NumRow(self._filter_frame, "Max flanking indel rate", 0.15,
            tooltip="Remove loci with flanking-indel frequency above this.")
        self._p_flank.pack(fill="x", pady=2)
        self._p_stutter = NumRow(self._filter_frame, "Max stutter rate", 0.15,
            tooltip="Remove loci with stutter frequency above this.")
        self._p_stutter.pack(fill="x", pady=2)
        self._p_abias = NumRow(self._filter_frame, "Min allele bias", -2.0,
            tooltip="Remove calls below this allele-bias value "
                    "(more negative = more permissive).")
        self._p_abias.pack(fill="x", pady=2)
        self._p_sbias = NumRow(self._filter_frame, "Min strand bias", -2.0,
            tooltip="Remove calls below this strand-bias value "
                    "(more negative = more permissive).")
        self._p_sbias.pack(fill="x", pady=2)

        # --- actions ------------------------------------------
        action = tk.Frame(left, bg=BG)
        action.pack(fill="x", pady=(GAP, 2))
        RunButton(action, "Run Screening", self._run).pack(side="left")
        self._stop_btn = StopButton(action, self._stop)
        self._stop_btn.pack(side="left", padx=(8, 0))
        LinkButton(action, "Clear log", lambda: self._log.clear()).pack(
            side="right", pady=6)

        # --- right: log ---------------------------------------
        self._log = _log_panel(right)

        self._toggle_filter()
        self._log.append("Welcome to pSTRminer. Set the options on the left, "
                         "then click Run Screening.")

    def _toggle_filter(self):
        on = self._filter_mode.get() == "T"
        st = "normal" if on else "disabled"
        for row in (self._p_qual, self._p_flank, self._p_stutter,
                    self._p_abias, self._p_sbias):
            row.entry.config(state=st)

    def _browse_bed(self):
        p = filedialog.askopenfilename(
            title="Select HipSTR config BED",
            filetypes=[("BED files", "*.bed"), ("All files", "*.*")])
        if p:
            self._config_bed.set(p)

    def _browse_vcf(self):
        p = filedialog.askopenfilename(
            title="Select HipSTR VCF",
            filetypes=[("VCF files", "*.vcf *.vcf.gz"), ("All files", "*.*")])
        if p:
            self._input_vcf.set(p)

    def _browse_outdir(self):
        p = filedialog.askdirectory(title="Select output folder")
        if p:
            self._outdir.set(p)

    def _log_cb(self, line):
        self._log.after(0, self._log.append, line)

    def _done_cb(self, rc):
        def _update():
            self._stop_btn.config(state="disabled")
            if rc == 0:
                self._status.set_ok()
                self._log.append("\n[pSTRminer] \u2713 Screening completed successfully.")
                outdir = self._outdir.get()
                prefix = self._prefix.get()
                self._log.append(f"[pSTRminer]   Results in: {outdir}/{prefix}.*")
            else:
                self._status.set_fail()
                self._log.append(f"\n[pSTRminer] \u2717 Process exited with code {rc}.")
        self._log.after(0, _update)

    def _validate(self):
        errs = []
        if not self._config_bed.get():
            errs.append("HipSTR config BED is required.")
        elif not Path(self._config_bed.get()).exists():
            errs.append("HipSTR config BED does not exist.")
        if not self._input_vcf.get():
            errs.append("Input VCF is required.")
        elif not Path(self._input_vcf.get()).exists():
            errs.append("Input VCF does not exist.")
        if not self._outdir.get():
            errs.append("Output folder is required.")
        if not self._prefix.get():
            errs.append("Output prefix is required.")
        if self._filter_mode.get() == "T":
            for name, row in [
                ("Minimum call quality",    self._p_qual),
                ("Max flanking indel rate", self._p_flank),
                ("Max stutter rate",        self._p_stutter),
                ("Min allele bias",         self._p_abias),
                ("Min strand bias",         self._p_sbias),
            ]:
                try:
                    float(row.get())
                except ValueError:
                    errs.append(f"'{name}' must be a number.")
        return errs

    def _run(self):
        errs = self._validate()
        if errs:
            messagebox.showerror("Input Error", "\n".join(errs))
            return

        self._log.clear()
        self._status.set_running()
        self._stop_btn.config(state="normal")

        needs = self._filter_mode.get() == "T"
        self._thread = run_polymorphism(
            output_dir=self._outdir.get(),
            config_bed=self._config_bed.get(),
            input_vcf=self._input_vcf.get(),
            output_prefix=self._prefix.get(),
            needs_filter=needs,
            min_call_qual=float(self._p_qual.get())    if needs else 0.9,
            max_call_flank_indel=float(self._p_flank.get())  if needs else 0.15,
            max_call_stutter=float(self._p_stutter.get()) if needs else 0.15,
            min_call_allele_bias=float(self._p_abias.get())  if needs else -2.0,
            min_call_strand_bias=float(self._p_sbias.get())  if needs else -2.0,
            log_callback=self._log_cb,
            done_callback=self._done_cb,
        )

    def _stop(self):
        self._log.append("\n[pSTRminer] Stop requested. The current step will "
                         "finish before halting.")
        self._stop_btn.config(state="disabled")


# =============================================================
#  Tab 3 - Help
# =============================================================

HELP_CONTENT = [
    ("h1", "What pSTRminer does"),
    ("body",
     "pSTRminer identifies polymorphic short tandem repeats (STRs) across a "
     "whole genome and evaluates their forensic parameters. It runs as two "
     "stages, shown as the two tabs above."),
    ("body",
     "Stage 1 - STR Configuration scans a reference genome for candidate STRs "
     "with Tandem Repeats Finder (TRF) and writes a HipSTR configuration (a "
     "BED file describing where the STRs are)."),
    ("body",
     "Between the stages you genotype your samples with HipSTR yourself, using "
     "that configuration and your aligned reads (BAM/CRAM). This produces a "
     "VCF. pSTRminer does not align reads or call genotypes - it hands that to "
     "HipSTR, the tool built for it."),
    ("body",
     "Stage 2 - Polymorphism Screening reads the HipSTR VCF, optionally filters "
     "low-quality calls, converts genotypes to repeat copy numbers, and "
     "computes per-locus forensic parameters."),

    ("h1", "What you need installed"),
    ("bullet",
     "Stage 1: TRF (bundled / auto-downloaded), plus samtools (faidx), "
     "bedtools, wget, git and python2 available on your PATH. On an offline "
     "machine, supply a local FASTA and a local TRF binary."),
    ("bullet",
     "Stage 2: R (the bundled analysis pipeline installs the R packages it "
     "needs where possible). You provide the configuration BED from Stage 1 "
     "and the HipSTR VCF."),

    ("h1", "Step 1 - STR Configuration"),
    ("bullet",
     "Reference Genome Source: keep \"Use a local FASTA file\" (the default) "
     "and browse to your genome, or pick \"Download from UCSC\" and enter an "
     "assembly ID such as bosTau9."),
    ("bullet",
     "TRF: leave on \"Download automatically\", or choose \"Use a local TRF "
     "binary\" and point to your trf executable (useful offline or behind a "
     "firewall)."),
    ("bullet", "Output folder: where the configuration files are written."),
    ("bullet",
     "Click Run Configuration. The result is a HipSTR configuration BED "
     "(...configuration.DitoHex.bed) used by HipSTR and by Step 2."),

    ("h1", "Genotype with HipSTR (between the steps)"),
    ("body",
     "Run HipSTR yourself with the configuration BED and your BAM/CRAM files to "
     "genotype your samples. This produces the VCF that Step 2 reads. See the "
     "HipSTR documentation for details."),

    ("h1", "Step 2 - Polymorphism Screening"),
    ("bullet", "HipSTR config BED: the BED file produced by Step 1."),
    ("bullet", "Input VCF: the VCF (.vcf or .vcf.gz) genotyped by HipSTR."),
    ("bullet",
     "Output folder / prefix: where results go and how they are named "
     "(prefix.forensic_parameters.txt, and so on)."),
    ("bullet",
     "VCF Filtering: \"Filter the raw VCF\" applies the thresholds below to an "
     "unfiltered HipSTR VCF; \"VCF is already filtered\" skips filtering if you "
     "pre-filtered it."),
    ("bullet",
     "Click Run Screening. Outputs include a per-locus genotype / copy-number "
     "table and a table of forensic parameters."),

    ("h1", "Filtering thresholds"),
    ("bullet", "Minimum call quality (0-1): drop genotype calls below this posterior quality."),
    ("bullet", "Max flanking indel rate: drop loci with too many indels in flanking reads."),
    ("bullet", "Max stutter rate: drop loci with excessive PCR stutter."),
    ("bullet",
     "Min allele bias / Min strand bias: drop calls with strong allelic or "
     "strand imbalance (a more negative value keeps more calls). The defaults "
     "follow HipSTR's recommended filtering."),

    ("h1", "Forensic parameters (Stage 2 output)"),
    ("body",
     "For each locus pSTRminer reports He (expected heterozygosity), PIC "
     "(polymorphism information content), Ho (observed heterozygosity), PD "
     "(power of discrimination), MP (match probability, equal to 1 - PD) and "
     "PE (power of exclusion). These match STRAF at every tested locus."),

    ("h1", "Tips"),
    ("bullet",
     "Offline or firewalled machines: use a local FASTA plus a local TRF binary "
     "in Step 1."),
    ("bullet",
     "The command line offers the same two stages: run  pstrminer config ...  "
     "and  pstrminer poly ...  (use  pstrminer --help)."),

    ("h1", "More"),
    ("link", "Repository:  github.com/liujj-git/pSTRminer"),
    ("dim", "Citation: to appear."),
]


class HelpTab(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG)
        self._build()

    def _build(self):
        wrap = tk.Frame(self, bg=PANEL_BG, highlightthickness=1,
                        highlightbackground=CARD_BORDER)
        wrap.pack(fill="both", expand=True, padx=16, pady=16)

        txt = scrolledtext.ScrolledText(
            wrap, font=FONT_BODY, bg=PANEL_BG, fg=TEXT, relief="flat",
            wrap="word", padx=22, pady=18, borderwidth=0, cursor="arrow")
        txt.pack(fill="both", expand=True, padx=2, pady=2)

        txt.tag_config("h1", font=FONT_HELP_H1, foreground=ACCENT,
                       spacing1=16, spacing3=6)
        txt.tag_config("body", font=FONT_BODY, foreground=TEXT,
                       spacing3=8, lmargin1=2, lmargin2=2)
        txt.tag_config("bullet", font=FONT_BODY, foreground=TEXT,
                       spacing3=6, lmargin1=20, lmargin2=36)
        txt.tag_config("link", font=(FONT_FAMILY, 12, "bold"),
                       foreground=ACCENT, spacing1=6, spacing3=4)
        txt.tag_config("dim", font=FONT_SMALL, foreground=MUTED, spacing3=4)

        for style, text in HELP_CONTENT:
            if style == "bullet":
                txt.insert("end", "\u2022  " + text + "\n", "bullet")
            else:
                txt.insert("end", text + "\n", style)

        txt.configure(state="disabled")


# =============================================================
#  Main application window
# =============================================================

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        resolve_fonts(self)              # pick best installed faces first
        self.title("pSTRminer  -  Integrated STR Analysis Pipeline")
        self.geometry("1300x900")
        self.minsize(1080, 720)
        self.configure(bg=BG)
        self._build_header()
        self._build_tabs()
        self._build_footer()

    def _build_header(self):
        hdr = tk.Frame(self, bg=ACCENT, height=62)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="pSTRminer", font=FONT_TITLE, fg="white",
                 bg=ACCENT).pack(side="left", padx=20, pady=10)
        tk.Label(hdr, text="Integrated STR Analysis Pipeline for Forensic Genetics",
                 font=FONT_TAGLINE, fg="#DBEAFE", bg=ACCENT).pack(
            side="left", padx=(2, 10), pady=10)
        tk.Label(hdr, text="v" + __version__, font=FONT_SMALL, fg="#BFDBFE",
                 bg=ACCENT).pack(side="right", padx=20)

    def _build_tabs(self):
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background="#DDE3EC", foreground=MUTED,
                        font=FONT_BODY, padding=[18, 9])
        style.map("TNotebook.Tab",
                  background=[("selected", PANEL_BG)],
                  foreground=[("selected", ACCENT)])

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)

        self._tab_cfg  = ConfigTab(self.nb)
        self._tab_poly = PolyTab(self.nb)
        self._tab_help = HelpTab(self.nb)

        self.nb.add(self._tab_cfg,  text="  Step 1  \u00b7  STR Configuration  ")
        self.nb.add(self._tab_poly, text="  Step 2  \u00b7  Polymorphism Screening  ")
        self.nb.add(self._tab_help, text="  Help  ")

    def _build_footer(self):
        ft = tk.Frame(self, bg="#E2E8F0", height=26)
        ft.pack(fill="x", side="bottom")
        ft.pack_propagate(False)
        tk.Label(ft, text="pSTRminer  |  HipSTR pipeline  |  For academic & "
                          "forensic research use", font=FONT_SMALL, fg=MUTED,
                 bg="#E2E8F0").pack(side="left", padx=12)
        tk.Label(ft, text="github.com/liujj-git/pSTRminer",
                 font=FONT_SMALL, fg=MUTED, bg="#E2E8F0").pack(side="right", padx=12)


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
