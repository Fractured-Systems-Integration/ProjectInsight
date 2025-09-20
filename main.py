import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
from system_info import get_system_info
from exporter import export_to_file
from config import VERSION, APP_NAME
from updater import run_updater
import threading
import sys
import os

def resource_path(relative_path):
    """ Get absolute path to resource (for PyInstaller .exe) """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ---------- FUNCTIONS ----------
def refresh_info():
    def thread_task():
        print("Gathering system information...")  # Debug
        try:
            info = get_system_info()
            text_box.configure(state='normal')
            text_box.delete('1.0', tk.END)
            for key, value in info.items():
                text_box.insert(tk.END, f"{key}: {value}\n")
            text_box.configure(state='disabled')
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            refresh_btn.config(state='normal')
            export_btn.config(state='normal')

    # Optionally disable buttons while loading
    refresh_btn.config(state='disabled')
    export_btn.config(state='disabled')

    threading.Thread(target=thread_task, daemon=True).start()

def export_info():
    file = filedialog.asksaveasfilename(defaultextension=".txt",
                                        filetypes=[("Text files", "*.txt")],
                                        title="Save Report")
    if file:
        try:
            export_to_file(file, text_box.get('1.0', tk.END))
            messagebox.showinfo("Saved", f"System info saved to:\n{file}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

def toggle_theme():
    current = style.theme_use()
    if current == "default":
        style.theme_use("alt")
        root.configure(bg="#2b2b2b")
        text_box.configure(bg="#2e2e2e", fg="white", insertbackground="white")
    else:
        style.theme_use("default")
        root.configure(bg="SystemButtonFace")
        text_box.configure(bg="white", fg="black", insertbackground="black")

# ---------- GUI Setup ----------
root = tk.Tk()
root.title(f"{APP_NAME} v{VERSION}")
root.geometry("800x600")

# Grid layout config
root.rowconfigure(0, weight=1)  # notebook
root.rowconfigure(1, weight=0)  # buttons
root.rowconfigure(2, weight=0)  # footer
root.columnconfigure(0, weight=1)

# Set icon
try:
    root.iconbitmap(resource_path("insight.ico"))
except:
    print("Icon file not found or failed to load.")

style = ttk.Style()
style.theme_use('default')

# ---------- MENU ----------
menubar = tk.Menu(root)

view_menu = tk.Menu(menubar, tearoff=0)
view_menu.add_command(label="Toggle Dark Mode", command=toggle_theme)
menubar.add_cascade(label="View", menu=view_menu)

update_menu = tk.Menu(menubar, tearoff=0)
update_menu.add_command(label="Check for Update", command=run_updater)
menubar.add_cascade(label="Update", menu=update_menu)

help_menu = tk.Menu(menubar, tearoff=0)
help_menu.add_command(label="About", command=lambda: messagebox.showinfo("About", f"{APP_NAME} v{VERSION}\n© 2025 Fractured Systems Integration"))
menubar.add_cascade(label="Help", menu=help_menu)

root.config(menu=menubar)

# ---------- MAIN CONTENT ----------
main_frame = ttk.Frame(root)
main_frame.grid(row=0, column=0, sticky="nsew")

notebook = ttk.Notebook(main_frame)
notebook.pack(expand=True, fill='both', padx=10, pady=(10, 0))

# ---------- SYSTEM INFO TAB ----------
system_frame = ttk.Frame(notebook)
notebook.add(system_frame, text="System Info")

# Logo
try:
    logo_path = resource_path("logo.png")
    logo_img = Image.open(logo_path).resize((150, 150))
    logo_photo = ImageTk.PhotoImage(logo_img)
    logo_label = tk.Label(system_frame, image=logo_photo)
    logo_label.image = logo_photo
    logo_label.pack(pady=(10, 0))
except Exception as e:
    print(f"Logo failed to load: {e}")

# System info box
system_content = ttk.Frame(system_frame)
system_content.pack(fill='both', expand=True, padx=10, pady=10)

text_box = tk.Text(system_content, wrap='word', state='disabled', font=('Segoe UI', 10))
text_box.pack(expand=True, fill='both')

# ---------- BUTTONS ----------
button_frame = ttk.Frame(root, padding=10)
button_frame.grid(row=1, column=0, sticky="ew")

refresh_btn = ttk.Button(button_frame, text="Refresh Info", command=refresh_info)
refresh_btn.pack(side='left', padx=5)

export_btn = ttk.Button(button_frame, text="Export Report", command=export_info)
export_btn.pack(side='left', padx=5)

# ---------- FOOTER ----------
footer = ttk.Label(root, text="© 2025 Fractured Systems Integration", anchor='center', font=('Segoe UI', 9))
footer.grid(row=2, column=0, sticky="ew", pady=(0, 5))

# ---------- INITIAL LOAD ----------
refresh_info()
root.mainloop()
