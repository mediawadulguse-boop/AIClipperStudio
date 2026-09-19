from __future__ import annotations
import os
import queue
import threading
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from ai_clipper import __version__
from ai_clipper.config import load_config, save_config, AppConfig
from ai_clipper.database import create_project, save_analysis
from ai_clipper.engine_manager import auto_setup, status as engine_status, whisper_model_path
from ai_clipper.media import probe_video, preview_clip, export_clip
from ai_clipper.models import ClipCandidate, TranscriptSegment
from ai_clipper.paths import projects_dir, exports_dir, app_data_dir
from ai_clipper.pipeline import transcribe, analyze
from ai_clipper.transcript import seconds_to_clock

BG = "#111318"
PANEL = "#1a1d24"
PANEL_2 = "#222630"
TEXT = "#f5f7fb"
MUTED = "#9aa3b2"
ACCENT = "#6c63ff"
GOOD = "#4ade80"
WARN = "#fbbf24"


class AIClipperApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"AI Clipper Studio v{__version__}")
        self.geometry("1280x820")
        self.minsize(1050, 700)
        self.configure(bg=BG)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.cfg = load_config()
        self.video_path: str | None = None
        self.project_id: int | None = None
        self.transcript: list[TranscriptSegment] = []
        self.candidates: list[ClipCandidate] = []
        self.events: queue.Queue = queue.Queue()
        self.busy = False

        self._styles()
        self._build_ui()
        self._refresh_engine_badges()
        self.after(150, self._poll_events)

    def _styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("Panel2.TFrame", background=PANEL_2)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Panel.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("PanelMuted.TLabel", background=PANEL, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=("Segoe UI Semibold", 20))
        style.configure("Heading.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI Semibold", 12))
        style.configure("Accent.TButton", background=ACCENT, foreground="white", padding=(14, 9), font=("Segoe UI Semibold", 10))
        style.map("Accent.TButton", background=[("active", "#7c74ff"), ("disabled", "#454858")])
        style.configure("TButton", background=PANEL_2, foreground=TEXT, padding=(11, 8), borderwidth=0)
        style.map("TButton", background=[("active", "#303644")])
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT, rowheight=31, borderwidth=0, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", background=PANEL_2, foreground=TEXT, borderwidth=0, font=("Segoe UI Semibold", 9))
        style.map("Treeview", background=[("selected", ACCENT)], foreground=[("selected", "white")])
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=MUTED, padding=(14, 8))
        style.map("TNotebook.Tab", background=[("selected", PANEL_2)], foreground=[("selected", TEXT)])
        style.configure("TCombobox", fieldbackground=PANEL_2, background=PANEL_2, foreground=TEXT)
        style.configure("Horizontal.TProgressbar", troughcolor=PANEL_2, background=ACCENT)

    def _build_ui(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=24, pady=(18, 10))
        ttk.Label(top, text="AI Clipper Studio", style="Title.TLabel").pack(side="left")
        ttk.Label(top, text="Local-first viral clip intelligence", style="Muted.TLabel").pack(side="left", padx=14, pady=(8, 0))

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=24, pady=(0, 16))
        self.tab_project = ttk.Frame(self.notebook)
        self.tab_setup = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_project, text="Project")
        self.notebook.add(self.tab_setup, text="Setup AI")
        self._build_project_tab()
        self._build_setup_tab()

        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=24, pady=(0, 14))
        self.progress = ttk.Progressbar(bottom, mode="indeterminate")
        self.progress.pack(side="left", fill="x", expand=True)
        self.status_var = tk.StringVar(value="Siap.")
        ttk.Label(bottom, textvariable=self.status_var, style="Muted.TLabel").pack(side="left", padx=(12, 0))

    def _build_project_tab(self):
        page = self.tab_project
        header = ttk.Frame(page, style="Panel.TFrame")
        header.pack(fill="x", pady=(12, 12))
        inner = ttk.Frame(header, style="Panel.TFrame")
        inner.pack(fill="x", padx=18, pady=16)
        ttk.Label(inner, text="1. Pilih video", style="Heading.TLabel").grid(row=0, column=0, sticky="w")
        self.video_var = tk.StringVar(value="Belum ada video dipilih")
        ttk.Label(inner, textvariable=self.video_var, style="PanelMuted.TLabel").grid(row=1, column=0, sticky="w", pady=(6, 0))
        buttons = ttk.Frame(inner, style="Panel.TFrame")
        buttons.grid(row=0, column=1, rowspan=2, sticky="e")
        self.btn_open = ttk.Button(buttons, text="Pilih Video", command=self.choose_video)
        self.btn_open.pack(side="left", padx=(0, 8))
        self.btn_analyze = ttk.Button(buttons, text="Analisis AI", style="Accent.TButton", command=self.start_analysis)
        self.btn_analyze.pack(side="left")
        inner.columnconfigure(0, weight=1)

        body = ttk.Frame(page)
        body.pack(fill="both", expand=True)
        left = ttk.Frame(body, style="Panel.TFrame")
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        right = ttk.Frame(body, style="Panel.TFrame", width=340)
        right.pack(side="right", fill="y", padx=(8, 0))
        right.pack_propagate(False)

        top_left = ttk.Frame(left, style="Panel.TFrame")
        top_left.pack(fill="x", padx=14, pady=(14, 6))
        ttk.Label(top_left, text="Kandidat Clip", style="Heading.TLabel").pack(side="left")
        self.count_var = tk.StringVar(value="0 kandidat")
        ttk.Label(top_left, textvariable=self.count_var, style="PanelMuted.TLabel").pack(side="right")

        cols = ("rank", "score", "time", "duration", "title")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="browse")
        for c, text, width, anchor in [
            ("rank", "#", 40, "center"),
            ("score", "Score", 65, "center"),
            ("time", "Timestamp", 135, "center"),
            ("duration", "Durasi", 65, "center"),
            ("title", "Judul / Hook", 430, "w"),
        ]:
            self.tree.heading(c, text=text)
            self.tree.column(c, width=width, anchor=anchor, stretch=(c == "title"))
        self.tree.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.tree.bind("<<TreeviewSelect>>", self.on_candidate_select)

        ttk.Label(right, text="Detail Kandidat", style="Heading.TLabel").pack(anchor="w", padx=16, pady=(16, 8))
        self.detail_title = tk.StringVar(value="Pilih kandidat clip")
        ttk.Label(right, textvariable=self.detail_title, style="Panel.TLabel", wraplength=310, font=("Segoe UI Semibold", 11)).pack(anchor="w", padx=16)
        self.detail_score = tk.StringVar(value="")
        ttk.Label(right, textvariable=self.detail_score, style="PanelMuted.TLabel").pack(anchor="w", padx=16, pady=(6, 8))

        self.detail_text = tk.Text(right, bg=PANEL_2, fg=TEXT, insertbackground=TEXT, relief="flat", wrap="word", height=16, font=("Segoe UI", 9), padx=10, pady=10)
        self.detail_text.pack(fill="both", expand=True, padx=16, pady=(0, 10))
        self.detail_text.configure(state="disabled")

        action = ttk.Frame(right, style="Panel.TFrame")
        action.pack(fill="x", padx=16, pady=(0, 16))
        self.btn_preview = ttk.Button(action, text="Preview", command=self.preview_selected, state="disabled")
        self.btn_preview.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.btn_export = ttk.Button(action, text="Export", style="Accent.TButton", command=self.export_selected, state="disabled")
        self.btn_export.pack(side="left", fill="x", expand=True, padx=(5, 0))

    def _build_setup_tab(self):
        page = self.tab_setup
        box = ttk.Frame(page, style="Panel.TFrame")
        box.pack(fill="x", pady=12)
        inner = ttk.Frame(box, style="Panel.TFrame")
        inner.pack(fill="x", padx=18, pady=18)
        ttk.Label(inner, text="Engine lokal", style="Heading.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(inner, text="Engine diunduh sekali ke komputer. Video tidak perlu dikirim ke cloud.", style="PanelMuted.TLabel").grid(row=1, column=0, columnspan=3, sticky="w", pady=(5, 12))

        self.engine_vars = {k: tk.StringVar(value="Memeriksa…") for k in ["ffmpeg", "whisper", "llama"]}
        for i, (key, label) in enumerate([("ffmpeg", "FFmpeg"), ("whisper", "Whisper"), ("llama", "Qwen / llama.cpp")], start=2):
            ttk.Label(inner, text=label, style="Panel.TLabel").grid(row=i, column=0, sticky="w", pady=5)
            ttk.Label(inner, textvariable=self.engine_vars[key], style="PanelMuted.TLabel").grid(row=i, column=1, sticky="w", padx=16)

        ttk.Label(inner, text="Mode AI", style="Panel.TLabel").grid(row=6, column=0, sticky="w", pady=(16, 5))
        self.mode_var = tk.StringVar(value=self.cfg.ai_mode)
        mode = ttk.Combobox(inner, textvariable=self.mode_var, state="readonly", values=["local_llm", "local_lite"], width=22)
        mode.grid(row=6, column=1, sticky="w", padx=16, pady=(16, 5))

        ttk.Label(inner, text="Whisper", style="Panel.TLabel").grid(row=7, column=0, sticky="w", pady=5)
        self.whisper_var = tk.StringVar(value=self.cfg.whisper_model)
        ttk.Combobox(inner, textvariable=self.whisper_var, state="readonly", values=["small", "medium", "large-v3-turbo"], width=22).grid(row=7, column=1, sticky="w", padx=16, pady=5)

        ttk.Label(inner, text="Qwen", style="Panel.TLabel").grid(row=8, column=0, sticky="w", pady=5)
        self.qwen_var = tk.StringVar(value=self.cfg.qwen_model)
        ttk.Combobox(inner, textvariable=self.qwen_var, state="readonly", values=["Qwen/Qwen3-4B-GGUF:Q4_K_M", "Qwen/Qwen3-8B-GGUF:Q4_K_M"], width=22).grid(row=8, column=1, sticky="w", padx=16, pady=5)

        buttons = ttk.Frame(inner, style="Panel.TFrame")
        buttons.grid(row=9, column=0, columnspan=3, sticky="w", pady=(18, 0))
        self.btn_setup = ttk.Button(buttons, text="Setup Otomatis", style="Accent.TButton", command=self.start_setup)
        self.btn_setup.pack(side="left")
        ttk.Button(buttons, text="Simpan Pengaturan", command=self.save_settings).pack(side="left", padx=8)
        ttk.Button(buttons, text="Buka Folder Data", command=self.open_data_folder).pack(side="left")

    def choose_video(self):
        path = filedialog.askopenfilename(
            title="Pilih video",
            filetypes=[("Video", "*.mp4 *.mov *.mkv *.avi *.webm"), ("Semua file", "*.*")]
        )
        if not path:
            return
        self.video_path = path
        self.video_var.set(Path(path).name)
        self.project_id = create_project(path)
        self._clear_candidates()
        try:
            info = probe_video(path)
            self.status_var.set(f"Video siap • {int(info['duration']//60)}m {int(info['duration']%60)}s • {info['width']}×{info['height']}")
        except Exception:
            self.status_var.set("Video dipilih.")

    def save_settings(self):
        self.cfg.ai_mode = self.mode_var.get()
        self.cfg.whisper_model = self.whisper_var.get()
        self.cfg.qwen_model = self.qwen_var.get()
        save_config(self.cfg)
        self.status_var.set("Pengaturan disimpan.")
        self._refresh_engine_badges()

    def start_setup(self):
        if self.busy:
            return
        self.save_settings()
        self._set_busy(True, "Menyiapkan engine lokal…")
        def job():
            try:
                auto_setup(self.cfg.whisper_model, self.cfg.ai_mode == "local_llm", lambda s: self.events.put(("status", s)))
                self.events.put(("setup_done", None))
            except Exception as e:
                self.events.put(("error", f"Setup gagal: {e}\n\n{traceback.format_exc()}"))
        threading.Thread(target=job, daemon=True).start()

    def start_analysis(self):
        if self.busy:
            return
        if not self.video_path:
            messagebox.showinfo("AI Clipper", "Pilih video terlebih dahulu.")
            return
        self.save_settings()
        st = engine_status()
        if not st["ffmpeg"] or not st["whisper"] or not whisper_model_path(self.cfg.whisper_model).exists():
            self.notebook.select(self.tab_setup)
            messagebox.showinfo("Setup diperlukan", "Jalankan Setup Otomatis terlebih dahulu agar FFmpeg, Whisper, dan model tersedia.")
            return
        self._set_busy(True, "Memulai analisis…")
        video = self.video_path
        pid = self.project_id or create_project(video)
        self.project_id = pid
        workdir = projects_dir() / f"project_{pid}"
        def job():
            try:
                tr = transcribe(video, workdir, self.cfg, lambda s: self.events.put(("status", s)))
                self.events.put(("status", f"Transkripsi selesai: {len(tr)} segmen."))
                clips = analyze(tr, self.cfg, lambda s: self.events.put(("status", s)))
                save_analysis(pid, tr, clips)
                self.events.put(("analysis_done", (tr, clips)))
            except Exception as e:
                self.events.put(("error", f"Analisis gagal: {e}\n\n{traceback.format_exc()}"))
        threading.Thread(target=job, daemon=True).start()

    def _set_busy(self, busy: bool, status: str | None = None):
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.btn_open.configure(state=state)
        self.btn_analyze.configure(state=state)
        self.btn_setup.configure(state=state)
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()
        if status:
            self.status_var.set(status)

    def _poll_events(self):
        try:
            while True:
                kind, data = self.events.get_nowait()
                if kind == "status":
                    self.status_var.set(str(data))
                elif kind == "setup_done":
                    self._set_busy(False, "Setup engine selesai. Siap menganalisis video.")
                    self._refresh_engine_badges()
                elif kind == "analysis_done":
                    self.transcript, self.candidates = data
                    self._populate_candidates()
                    self._set_busy(False, f"Selesai. {len(self.candidates)} kandidat clip ditemukan.")
                elif kind == "export_done":
                    self._set_busy(False, f"Export selesai: {data}")
                    messagebox.showinfo("Export selesai", f"Clip berhasil dibuat:\n{data}")
                elif kind == "error":
                    self._set_busy(False, "Terjadi kesalahan.")
                    messagebox.showerror("AI Clipper", str(data))
        except queue.Empty:
            pass
        self.after(150, self._poll_events)

    def _refresh_engine_badges(self):
        st = engine_status()
        for key in self.engine_vars:
            self.engine_vars[key].set("✓ Siap" if st.get(key) else "Belum terpasang")

    def _clear_candidates(self):
        self.transcript = []
        self.candidates = []
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.count_var.set("0 kandidat")
        self.detail_title.set("Pilih kandidat clip")
        self.detail_score.set("")
        self._set_detail_text("")
        self.btn_preview.configure(state="disabled")
        self.btn_export.configure(state="disabled")

    def _populate_candidates(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for i, c in enumerate(self.candidates, 1):
            self.tree.insert("", "end", iid=str(i-1), values=(i, c.score, f"{seconds_to_clock(c.start)} → {seconds_to_clock(c.end)}", f"{int(round(c.duration))}s", c.title))
        self.count_var.set(f"{len(self.candidates)} kandidat")
        if self.candidates:
            self.tree.selection_set("0")
            self.tree.focus("0")
            self.on_candidate_select()

    def on_candidate_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if idx >= len(self.candidates):
            return
        c = self.candidates[idx]
        self.detail_title.set(c.title)
        self.detail_score.set(f"Viral Score {c.score}/100  •  {seconds_to_clock(c.start)} – {seconds_to_clock(c.end)}  •  {int(round(c.duration))} detik")
        detail = (
            f"ALASAN\n{c.reason}\n\n"
            f"HOOK {c.hook}   CURIOSITY {c.curiosity}\n"
            f"CONFLICT {c.conflict}   INFO {c.information}\n"
            f"EMOTION {c.emotion}   STANDALONE {c.standalone}\n\n"
            f"TRANSCRIPT\n{c.transcript}"
        )
        self._set_detail_text(detail)
        self.btn_preview.configure(state="normal")
        self.btn_export.configure(state="normal")

    def _set_detail_text(self, text: str):
        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", text)
        self.detail_text.configure(state="disabled")

    def _selected_candidate(self) -> ClipCandidate | None:
        sel = self.tree.selection()
        if not sel:
            return None
        idx = int(sel[0])
        return self.candidates[idx] if idx < len(self.candidates) else None

    def preview_selected(self):
        c = self._selected_candidate()
        if not c or not self.video_path:
            return
        try:
            preview_clip(self.video_path, c.start, c.duration)
        except Exception as e:
            messagebox.showerror("Preview", str(e))

    def export_selected(self):
        c = self._selected_candidate()
        if not c or not self.video_path or self.busy:
            return
        ExportDialog(self, c, self._do_export)

    def _do_export(self, c: ClipCandidate, ratio: str, subtitles: bool):
        if not self.video_path:
            return
        default = exports_dir() / f"clip_{int(c.start)}_{c.score}.mp4"
        out = filedialog.asksaveasfilename(title="Simpan clip", initialdir=str(default.parent), initialfile=default.name, defaultextension=".mp4", filetypes=[("MP4 Video", "*.mp4")])
        if not out:
            return
        self._set_busy(True, "Merender clip…")
        video = self.video_path
        transcript = list(self.transcript)
        def job():
            try:
                export_clip(video, out, c.start, c.end, ratio, subtitles, transcript)
                self.events.put(("export_done", out))
            except Exception as e:
                self.events.put(("error", f"Export gagal: {e}\n\n{traceback.format_exc()}"))
        threading.Thread(target=job, daemon=True).start()

    def open_data_folder(self):
        p = str(app_data_dir())
        if os.name == "nt":
            os.startfile(p)
        else:
            messagebox.showinfo("Folder Data", p)


class ExportDialog(tk.Toplevel):
    def __init__(self, parent: AIClipperApp, candidate: ClipCandidate, on_export):
        super().__init__(parent)
        self.title("Export Clip")
        self.geometry("420x300")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.candidate = candidate
        self.on_export = on_export
        ttk.Label(self, text="Export Clip", style="Title.TLabel").pack(anchor="w", padx=22, pady=(20, 6))
        ttk.Label(self, text=f"{seconds_to_clock(candidate.start)} → {seconds_to_clock(candidate.end)} • Score {candidate.score}", style="Muted.TLabel").pack(anchor="w", padx=22)

        form = ttk.Frame(self, style="Panel.TFrame")
        form.pack(fill="both", expand=True, padx=22, pady=16)
        ttk.Label(form, text="Rasio", style="Panel.TLabel").grid(row=0, column=0, sticky="w", padx=14, pady=(16, 8))
        self.ratio = tk.StringVar(value="9:16")
        ttk.Combobox(form, textvariable=self.ratio, state="readonly", values=["9:16", "4:5", "1:1", "16:9", "original"], width=18).grid(row=0, column=1, sticky="e", padx=14, pady=(16, 8))
        self.sub = tk.BooleanVar(value=True)
        cb = tk.Checkbutton(form, text="Burn subtitle", variable=self.sub, bg=PANEL, fg=TEXT, selectcolor=PANEL_2, activebackground=PANEL, activeforeground=TEXT, highlightthickness=0)
        cb.grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=8)
        ttk.Label(form, text="V1 memakai center crop. Face tracking akan masuk tahap berikutnya.", style="PanelMuted.TLabel", wraplength=340).grid(row=2, column=0, columnspan=2, sticky="w", padx=14, pady=(6, 12))
        form.columnconfigure(1, weight=1)
        ttk.Button(self, text="Export MP4", style="Accent.TButton", command=self.go).pack(anchor="e", padx=22, pady=(0, 18))

    def go(self):
        ratio, sub = self.ratio.get(), self.sub.get()
        self.destroy()
        self.on_export(self.candidate, ratio, sub)


def main():
    app = AIClipperApp()
    app.mainloop()


if __name__ == "__main__":
    main()
