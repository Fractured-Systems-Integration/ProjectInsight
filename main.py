import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from PIL import Image, ImageTk

import yaml

# App modules
from system_info import get_system_info
from exporter import export_to_file
from config import VERSION, APP_NAME
from service import AgentService

# Optional: updater
try:
    from updater import run_updater
except Exception:
    def run_updater():
        messagebox.showinfo("Update", "Updater not available.")

# Optional: syncer (only used if you created syncer.py)
try:
    from syncer import Syncer
    _HAS_SYNCER = True
except Exception:
    _HAS_SYNCER = False

# Optional: ttkbootstrap theming
try:
    import ttkbootstrap as ttkb
    _HAS_TTKB = True
except Exception:
    _HAS_TTKB = False


# --------------------
# Helpers / Config
# --------------------
def _load_cfg():
    """Load insight.yaml if present; fall back to safe defaults."""
    base = {
        "interval_seconds": 30,
        "sqlite_path": "insight.db",
        "retention_days": 14,
        "enable_http": False,
        "http_endpoint": None,
        "device_token": None,
        "tags": {},
    }
    path = os.path.join(os.getcwd(), "insight.yaml")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                base.update(data)
        except Exception:
            # Keep defaults if YAML is malformed
            pass
    return base


def resource_path(relative_path: str) -> str:
    """Get absolute path to resource (handles PyInstaller _MEIPASS)."""
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# --------------------
# Application
# --------------------
class App:
    def __init__(self, root, style: ttk.Style):
        self.root = root
        self.style = style
        self.root.title(f"{APP_NAME} v{VERSION}")
        self.root.geometry("1100x700")

        # Start in dark mode if ttkbootstrap is available
        try:
            if _HAS_TTKB:
                self.style.theme_use("darkly")
            else:
                self.style.theme_use("default")
        except Exception:
            pass

        # Background agent + optional syncer
        self.cfg = _load_cfg()
        self.agent = AgentService(self.cfg)
        self.agent.start()

        self.syncer = None
        if _HAS_SYNCER:
            self.syncer = Syncer(self.cfg)
            self.syncer.start()

        # Build UI
        self._build_menu()
        self._build_layout()

        # State
        self.full_items: list[tuple[str, str]] = []

        # First load
        self.refresh_info()

        # Clean shutdown
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- UI ----------
    def _build_layout(self):
        # Root grid
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        # Main container
        container = ttk.Frame(self.root, padding=(10, 10, 10, 6))
        container.grid(row=0, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)

        # Toolbar
        toolbar = ttk.Frame(container)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        toolbar.columnconfigure(5, weight=1)

        self.search_var = tk.StringVar()
        ttk.Label(toolbar, text="Search:").grid(row=0, column=0, padx=(0, 6))
        self.search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=32)
        self.search_entry.grid(row=0, column=1, padx=(0, 12))
        self.search_entry.bind("<KeyRelease>", self._apply_filter)

        self.refresh_btn = ttk.Button(toolbar, text="Refresh", command=self.refresh_info)
        self.refresh_btn.grid(row=0, column=2, padx=4)

        self.export_btn = ttk.Button(toolbar, text="Export", command=self.export_info)
        self.export_btn.grid(row=0, column=3, padx=4)

        self.theme_btn = ttk.Button(toolbar, text="Toggle Theme", command=self.toggle_theme)
        self.theme_btn.grid(row=0, column=4, padx=4)

        # Content area
        content = ttk.Frame(container)
        content.grid(row=1, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)

        # Left: Table
        left = ttk.Frame(content)
        left.grid(row=0, column=0, sticky="nsew")
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(left, columns=("key", "value"), show="headings", height=22)
        self.tree.heading("key", text="Property")
        self.tree.heading("value", text="Value")
        self.tree.column("key", width=300, anchor="w")
        self.tree.column("value", width=600, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")

        tree_scroll_y = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=tree_scroll_y.set)
        tree_scroll_y.grid(row=0, column=1, sticky="ns")

        # Right: Quick actions + logo
        right = ttk.Frame(content, padding=(10, 0, 0, 0))
        right.grid(row=0, column=1, sticky="ns")

        try:
            logo_path = resource_path("logo.png")
            logo_img = Image.open(logo_path).resize((140, 140))
            logo_photo = ImageTk.PhotoImage(logo_img)
            ttk.Label(right, image=logo_photo).pack(pady=(0, 10))
            self._logo_photo = logo_photo  # keep reference to avoid GC
        except Exception:
            ttk.Label(right, text=APP_NAME, font=("Segoe UI", 14, "bold")).pack(pady=(0, 10))

        ttk.Label(right, text="Quick Actions").pack(pady=(0, 6))
        ttk.Button(right, text="Check for Update", command=run_updater).pack(fill="x", pady=2)
        ttk.Button(right, text="Export Report", command=self.export_info).pack(fill="x", pady=2)
        ttk.Button(right, text="Refresh Info", command=self.refresh_info).pack(fill="x", pady=2)

        # Status bar
        self.status = ttk.Label(self.root, anchor="w", padding=(10, 4))
        self.status.grid(row=2, column=0, sticky="ew")

    def _build_menu(self):
        menubar = tk.Menu(self.root)

        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Toggle Dark Mode", command=self.toggle_theme)
        menubar.add_cascade(label="View", menu=view_menu)

        update_menu = tk.Menu(menubar, tearoff=0)
        update_menu.add_command(label="Check for Update", command=run_updater)
        menubar.add_cascade(label="Update", menu=update_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(
            label="About",
            command=lambda: messagebox.showinfo(
                "About",
                f"{APP_NAME} v{VERSION}\n© 2025 Fractured Systems Integration"
            ),
        )
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    # ---------- Behavior ----------
    def _set_status(self, msg: str):
        self.status.configure(text=msg)

    def _apply_filter(self, event=None):
        q = (self.search_var.get() or "").strip().lower()
        self.tree.delete(*self.tree.get_children())
        for k, v in self.full_items:
            if not q or q in k.lower() or q in str(v).lower():
                self.tree.insert("", "end", values=(k, v))

    def _reload_tree(self, items: list[tuple[str, str]]):
        self.tree.delete(*self.tree.get_children())
        for k, v in items:
            self.tree.insert("", "end", values=(k, v))

    def refresh_info(self):
        def task():
            try:
                self._set_status("Collecting system information...")
                info = get_system_info()
                items = sorted(info.items(), key=lambda kv: kv[0].lower())
                self.full_items = items
                self.tree.after(0, lambda: self._reload_tree(items))
                self._set_status("System information loaded.")
            except Exception as e:
                self._set_status("Error while collecting info.")
                messagebox.showerror("Error", str(e))
            finally:
                self.refresh_btn.config(state="normal")
                self.export_btn.config(state="normal")

        self.refresh_btn.config(state="disabled")
        self.export_btn.config(state="disabled")
        threading.Thread(target=task, daemon=True).start()

    def export_info(self):
        file = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Report",
        )
        if not file:
            return
        try:
            # Export what’s visible (respects filter)
            rows = [self.tree.item(i, "values") for i in self.tree.get_children()]
            text = "\n".join(f"{k}: {v}" for k, v in rows)
            export_to_file(file, text)
            messagebox.showinfo("Saved", f"System info saved to:\n{file}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def toggle_theme(self):
        if _HAS_TTKB:
            try:
                now = self.style.theme_use()
                next_theme = "flatly" if now == "darkly" else "darkly"
                self.style.theme_use(next_theme)
            except Exception:
                pass
        else:
            try:
                now = self.style.theme_use()
                self.style.theme_use("alt" if now == "default" else "default")
            except Exception:
                pass

    def _on_close(self):
        try:
            if hasattr(self, "syncer") and self.syncer:
                self.syncer.stop()
        except Exception:
            pass
        try:
            if hasattr(self, "agent") and self.agent:
                self.agent.stop()
        except Exception:
            pass
        self.root.destroy()


# --------------------
# Entrypoint
# --------------------
def main():
    if _HAS_TTKB:
        root = ttkb.Window(themename="darkly")  # starts dark by default
        style = root.style                       # ttkbootstrap style proxy
    else:
        root = tk.Tk()
        style = ttk.Style()

    App(root, style)
    root.mainloop()


if __name__ == "__main__":
    main()
