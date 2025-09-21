import json
import os
import sys
import threading
from datetime import datetime
from typing import Any, Dict, List

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

import requests


BG_COLOR = "#FDFDFD"
ACCENT = "#0E7AFE"  # Primary blue
ACCENT_ACTIVE = "#0B68D1"
ACCENT_MUTED = "#A5C9FF"
TEXT_PRIMARY = "#111111"
TEXT_MUTED = "#6B7280"
SURFACE = "#FFFFFF"
BORDER = "#E5E7EB"
ROW_EVEN = "#FFFFFF"
ROW_ODD = "#FAFAFA"
STATUS_SEEN_FG = "#106B21"
STATUS_SEEN_BG = "#E8F5E9"

WINDOW_WIDTH = 500
WINDOW_HEIGHT = 550
APP_TITLE = "The Grievance Log"


def _safe_parse_dt(s: str):
    try:
        # Try a few common formats; fall back to as-is ordering
        # ISO first
        return datetime.fromisoformat(s)
    except Exception:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                continue
    return None


class GrievanceApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        # Window setup
        self.title(APP_TITLE)
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)
        self.configure(bg=BG_COLOR)

        # Style
        self._init_styles()

        # Config
        self.api_url = self._load_api_url()

        # UI
        self._build_ui()

        # Load history on startup
        if self.api_url:
            self.after(100, self.fetch_and_display_grievances)

    # -------- Styles & Config --------
    def _init_styles(self) -> None:
        style = ttk.Style()
        # Use default available theme; 'clam' is broadly available
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("TFrame", background=BG_COLOR)
        style.configure("TLabel", background=BG_COLOR, foreground=TEXT_PRIMARY, font=("Segoe UI", 10))
        style.configure("Header.TLabel", background=BG_COLOR, foreground=TEXT_PRIMARY, font=("Segoe UI", 11, "bold"))

        # Buttons
        style.configure("TButton", font=("Segoe UI", 10))
        style.configure(
            "Primary.TButton",
            font=("Segoe UI", 10, "bold"),
            foreground="#ffffff",
            background=ACCENT,
            padding=(10, 6),
            borderwidth=0,
        )
        style.map(
            "Primary.TButton",
            background=[("active", ACCENT_ACTIVE), ("disabled", ACCENT_MUTED)],
            foreground=[("disabled", "#ffffff")],
        )

        # Treeview
        style.configure(
            "Treeview",
            font=("Segoe UI", 9),
            background=SURFACE,
            fieldbackground=SURFACE,
            bordercolor=BORDER,
            borderwidth=1,
            rowheight=22,
        )
        style.map(
            "Treeview",
            background=[("selected", "#DBEAFE")],
            foreground=[("selected", TEXT_PRIMARY)],
        )
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    def _load_api_url(self) -> str:
        # Priority: ENV > config.json (next to script) > error
        env_url = os.environ.get("SHEET_API_URL", "").strip()
        if env_url:
            return env_url

        # Determine base directory for config.json
        # If running as a bundled executable, place config.json next to the EXE
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        config_path = os.path.join(base_dir, "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                url = str(cfg.get("SHEET_API_URL", "")).strip()
                if url:
                    return url
            except Exception:
                pass

        # If we get here, we couldn't find a URL
        self.after(200, lambda: messagebox.showerror(
            "Missing API URL",
            "Please set the SHEET_API_URL environment variable or create a config.json with a SHEET_API_URL field.\n\nSee README for details."
        ))
        return ""

    # -------- UI --------
    def _build_ui(self) -> None:
        # Top: Submission area
        top = ttk.Frame(self, padding=(12, 12, 12, 6))
        top.pack(fill="x")

        lbl = ttk.Label(top, text="What's on your mind?")
        lbl.grid(row=0, column=0, sticky="w")

        self.input_text = tk.Text(top, height=6, wrap="word", bg=SURFACE, relief="solid", bd=1)
        self.input_text.grid(row=1, column=0, sticky="nsew", pady=(6, 6))

        # Placeholder behavior
        self._placeholder_active = False
        self.input_text.tag_configure("placeholder", foreground=TEXT_MUTED)
        self._ensure_placeholder()
        self.input_text.bind("<FocusIn>", self._on_input_focus_in)
        self.input_text.bind("<FocusOut>", self._on_input_focus_out)
        self.input_text.bind("<Control-Return>", lambda e: self._submit_via_shortcut())

        btn_submit = ttk.Button(top, text="Submit Thought", command=self.submit_grievance, style="Primary.TButton")
        btn_submit.grid(row=2, column=0, sticky="e")
        self._submit_btn_ref = btn_submit

        top.columnconfigure(0, weight=1)
        top.rowconfigure(1, weight=1)

        # Separator for visual structure
        sep = ttk.Separator(self, orient="horizontal")
        sep.pack(fill="x", padx=12)

        # Bottom: History area
        bottom = ttk.Frame(self, padding=(12, 6, 12, 12))
        bottom.pack(fill="both", expand=True)

        header = ttk.Frame(bottom)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))

        hist_lbl = ttk.Label(header, text="Submission History", style="Header.TLabel")
        hist_lbl.pack(side="left")

        self.refresh_btn = ttk.Button(header, text="Refresh 🔄", command=self.fetch_and_display_grievances)
        self.refresh_btn.pack(side="right")

        columns = ("Grievance", "Status")
        self.tree = ttk.Treeview(bottom, columns=columns, show="headings", height=16)
        self.tree.heading("Grievance", text="Grievance")
        self.tree.heading("Status", text="Status")
        self.tree.column("Grievance", width=350, anchor="w", stretch=True)
        self.tree.column("Status", width=100, anchor="center", stretch=False)

        vsb = ttk.Scrollbar(bottom, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1, column=1, sticky="ns")

        # Treeview tags for zebra striping and status highlighting
        self.tree.tag_configure("odd", background=ROW_ODD)
        self.tree.tag_configure("even", background=ROW_EVEN)
        self.tree.tag_configure("status-seen", background=STATUS_SEEN_BG, foreground=STATUS_SEEN_FG)
        self.tree.bind("<Double-1>", self._on_tree_double_click)

        bottom.columnconfigure(0, weight=1)
        bottom.rowconfigure(1, weight=1)

        # Shortcuts
        self.bind("<F5>", lambda e: self.fetch_and_display_grievances())

    # -------- Networking & Data --------
    def fetch_and_display_grievances(self) -> None:
        if not self.api_url:
            return

        self._set_refresh_enabled(False)

        def worker():
            try:
                resp = requests.get(self.api_url, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                if not isinstance(data, list):
                    data = []
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Fetch Failed", f"Couldn't retrieve history.\n\n{e}"))
                self.after(0, lambda: self._set_refresh_enabled(True))
                return

            # Optional: sort by Timestamp desc if present
            try:
                def sort_key(row: Dict[str, Any]):
                    ts = row.get("Timestamp") or row.get("timestamp") or ""
                    dt = _safe_parse_dt(str(ts))
                    # Place unknown at the end
                    return dt or datetime.min

                data_sorted = sorted(data, key=sort_key, reverse=True)
            except Exception:
                data_sorted = data

            self.after(0, lambda: self._populate_tree(data_sorted))
            self.after(0, lambda: self._set_refresh_enabled(True))

        threading.Thread(target=worker, daemon=True).start()

    def _populate_tree(self, rows: List[Dict[str, Any]]) -> None:
        self.tree.delete(*self.tree.get_children())
        for idx, row in enumerate(rows):
            grievance = str(row.get("Grievance") or row.get("grievance") or "").strip()
            status = str(row.get("Status") or row.get("status") or "").strip()

            tags = ["even" if idx % 2 == 0 else "odd"]
            status_lower = status.lower()
            if "seen" in status_lower or "✅" in status:
                tags.append("status-seen")

            self.tree.insert("", "end", values=(grievance, status), tags=tags)

    def submit_grievance(self) -> None:
        if not self.api_url:
            messagebox.showerror("Missing API URL", "No API URL configured. Please set SHEET_API_URL or config.json.")
            return

        # Ignore placeholder content
        text = self._get_input_text().strip()
        if not text:
            messagebox.showwarning("Empty Thought", "Please write something before submitting.")
            return

        payload = {
            "Timestamp": datetime.now().isoformat(timespec="seconds"),
            "Grievance": text,
            "Status": "",  # left blank; can be updated in the sheet manually
        }

        # Disable UI interactions during submit
        self._set_submit_enabled(False)

        def worker():
            try:
                resp = requests.post(self.api_url, json=payload, timeout=15)
                resp.raise_for_status()
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Submit Failed", f"Couldn't submit your thought.\n\n{e}"))
                self.after(0, lambda: self._set_submit_enabled(True))
                return

            self.after(0, lambda: messagebox.showinfo("Submitted", "Your thought has been logged."))
            self.after(0, lambda: self.input_text.delete("1.0", "end"))
            self.after(0, self.fetch_and_display_grievances)
            self.after(0, lambda: self._set_submit_enabled(True))

        threading.Thread(target=worker, daemon=True).start()

    # -------- UI State helpers --------
    def _set_refresh_enabled(self, enabled: bool) -> None:
        try:
            self.refresh_btn.configure(state=("normal" if enabled else "disabled"))
        except Exception:
            pass

    def _set_submit_enabled(self, enabled: bool) -> None:
        try:
            self._submit_btn_ref.configure(state=("normal" if enabled else "disabled"))
        except Exception:
            pass

    # -------- Input helpers --------
    def _ensure_placeholder(self) -> None:
        current = self.input_text.get("1.0", "end").strip()
        if not current:
            self._placeholder_active = True
            self.input_text.delete("1.0", "end")
            self.input_text.insert("1.0", "Type your thought here…", ("placeholder",))

    def _clear_placeholder(self) -> None:
        if self._placeholder_active:
            self._placeholder_active = False
            self.input_text.delete("1.0", "end")

    def _on_input_focus_in(self, _event=None) -> None:
        if self._placeholder_active:
            self._clear_placeholder()

    def _on_input_focus_out(self, _event=None) -> None:
        # Reinstate placeholder if left empty
        if not self.input_text.get("1.0", "end").strip():
            self._ensure_placeholder()

    def _get_input_text(self) -> str:
        text = self.input_text.get("1.0", "end")
        # If placeholder is visible, treat as empty
        if self._placeholder_active:
            return ""
        return text

    def _submit_via_shortcut(self) -> None:
        self.submit_grievance()

    # -------- Tree interactions --------
    def _on_tree_double_click(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        if not values:
            return
        grievance = values[0]
        try:
            self.clipboard_clear()
            self.clipboard_append(grievance)
            messagebox.showinfo("Copied", "Grievance text copied to clipboard.")
        except Exception:
            pass


def main() -> None:
    app = GrievanceApp()
    app.mainloop()


if __name__ == "__main__":
    main()
