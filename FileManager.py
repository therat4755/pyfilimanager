import os
import shutil
import sys
import platform
import subprocess
import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

class FileManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Python File Manager")
        self.root.geometry("1000x600")
        
        # Configure style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Current directory state
        self.current_path = Path.cwd()
        self.clipboard_files = []
        self.clipboard_action = None  # 'copy' or 'cut'

        # UI Setup
        self._setup_ui()
        self._populate_tree()

    def _setup_ui(self):
        # --- Top Bar (Navigation) ---
        top_frame = ttk.Frame(self.root, padding=5)
        top_frame.pack(fill=tk.X, side=tk.TOP)

        ttk.Button(top_frame, text="⬆ Up", width=5, command=self.go_up).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text="🔄 Refresh", width=8, command=self.refresh).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text="🏠 Home", width=6, command=self.go_home).pack(side=tk.LEFT, padx=2)

        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(top_frame, textvariable=self.path_var)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.path_entry.bind('<Return>', self.on_path_entry_return)
        
        ttk.Button(top_frame, text="Go", width=4, command=self.on_path_entry_return).pack(side=tk.LEFT)

        # --- Toolbar (Operations) ---
        toolbar_frame = ttk.Frame(self.root, padding=5)
        toolbar_frame.pack(fill=tk.X, side=tk.TOP)

        ttk.Button(toolbar_frame, text="📄 New File", command=self.create_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar_frame, text="📂 New Folder", command=self.create_folder).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar_frame, text="✏ Rename", command=self.rename_item).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar_frame, text="✂ Cut", command=self.cut_selection).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar_frame, text="📋 Copy", command=self.copy_selection).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar_frame, text="📌 Paste", command=self.paste_selection).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar_frame, text="❌ Delete", command=self.delete_selection).pack(side=tk.LEFT, padx=2)

        # --- Main View (Treeview) ---
        tree_frame = ttk.Frame(self.root, padding=5)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("name", "size", "type", "date")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="extended")
        
        self.tree.heading("name", text="Name", command=lambda: self.sort_tree("name", False))
        self.tree.heading("size", text="Size", command=lambda: self.sort_tree("size", False))
        self.tree.heading("type", text="Type", command=lambda: self.sort_tree("type", False))
        self.tree.heading("date", text="Date Modified", command=lambda: self.sort_tree("date", False))

        self.tree.column("name", width=400)
        self.tree.column("size", width=100, anchor="e")
        self.tree.column("type", width=100)
        self.tree.column("date", width=150)

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(column=0, row=0, sticky='nsew')
        vsb.grid(column=1, row=0, sticky='ns')
        hsb.grid(column=0, row=1, sticky='ew')
        
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        # Bindings
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Return>", self.on_double_click)
        self.tree.bind("<BackSpace>", lambda e: self.go_up())

        # Status Bar
        self.status_var = tk.StringVar()
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    # --- Navigation Logic ---
    def _populate_tree(self):
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Update Path UI
        self.path_var.set(str(self.current_path))
        
        try:
            # Sort: Folders first, then files. Case insensitive.
            items = list(self.current_path.iterdir())
            items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
            
            count_files = 0
            count_dirs = 0

            for item in items:
                try:
                    stats = item.stat()
                    size_str = self._format_size(stats.st_size) if item.is_file() else ""
                    type_str = "Folder" if item.is_dir() else item.suffix.upper() or "File"
                    date_str = datetime.datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M')
                    
                    # Icons using unicode
                    icon = "📂" if item.is_dir() else "📄"
                    display_name = f"{icon}  {item.name}"

                    self.tree.insert("", "end", iid=str(item), values=(display_name, size_str, type_str, date_str), tags=(str(item),))
                    
                    if item.is_dir(): count_dirs += 1
                    else: count_files += 1

                except PermissionError:
                    continue # Skip files we can't read
            
            self.status_var.set(f" {count_dirs} folders, {count_files} files")

        except Exception as e:
            messagebox.showerror("Error", f"Could not list directory: {e}")
            self.go_up()

    def go_up(self):
        parent = self.current_path.parent
        if parent != self.current_path:
            self.current_path = parent
            self._populate_tree()

    def go_home(self):
        self.current_path = Path.home()
        self._populate_tree()

    def refresh(self):
        self._populate_tree()

    def on_path_entry_return(self, event=None):
        new_path = Path(self.path_var.get())
        if new_path.exists() and new_path.is_dir():
            self.current_path = new_path
            self._populate_tree()
        else:
            messagebox.showerror("Error", "Invalid directory path.")

    def on_double_click(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        
        item_iid = selected[0] # The iid is the full path
        target = Path(item_iid)

        if target.is_dir():
            self.current_path = target
            self._populate_tree()
        else:
            self._open_file(target)

    # --- File Operations ---
    def _open_file(self, file_path):
        """Attempts to open the file with the system's default application."""
        try:
            if platform.system() == 'Windows':
                os.startfile(file_path)
            elif platform.system() == 'Darwin': # macOS
                subprocess.call(('open', str(file_path)))
            else: # Linux and others
                subprocess.call(('xdg-open', str(file_path)))
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {e}")

    def create_folder(self):
        name = simpledialog.askstring("New Folder", "Enter folder name:")
        if name:
            new_path = self.current_path / name
            try:
                new_path.mkdir()
                self.refresh()
            except Exception as e:
                messagebox.showerror("Error", f"Could not create folder: {e}")

    def create_file(self):
        name = simpledialog.askstring("New File", "Enter file name:")
        if name:
            new_path = self.current_path / name
            try:
                new_path.touch()
                self.refresh()
            except Exception as e:
                messagebox.showerror("Error", f"Could not create file: {e}")

    def rename_item(self):
        selected = self.tree.selection()
        if not selected: return
        
        target = Path(selected[0])
        new_name = simpledialog.askstring("Rename", f"Rename '{target.name}' to:", initialvalue=target.name)
        
        if new_name and new_name != target.name:
            try:
                target.rename(target.parent / new_name)
                self.refresh()
            except Exception as e:
                messagebox.showerror("Error", f"Could not rename: {e}")

    def delete_selection(self):
        selected = self.tree.selection()
        if not selected: return

        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {len(selected)} item(s)?\nThis cannot be undone."):
            return

        for iid in selected:
            target = Path(iid)
            try:
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete {target.name}: {e}")
        
        self.refresh()

    def cut_selection(self):
        selected = self.tree.selection()
        if not selected: return
        self.clipboard_files = [Path(iid) for iid in selected]
        self.clipboard_action = 'cut'
        self.status_var.set(f"Cut {len(self.clipboard_files)} items to clipboard")

    def copy_selection(self):
        selected = self.tree.selection()
        if not selected: return
        self.clipboard_files = [Path(iid) for iid in selected]
        self.clipboard_action = 'copy'
        self.status_var.set(f"Copied {len(self.clipboard_files)} items to clipboard")

    def paste_selection(self):
        if not self.clipboard_files: return
        
        for src in self.clipboard_files:
            dst = self.current_path / src.name
            
            # Auto-rename if exists to avoid overwrite (e.g. file_copy.txt)
            if dst.exists():
                stem = dst.stem
                suffix = dst.suffix
                counter = 1
                while dst.exists():
                    dst = self.current_path / f"{stem}_copy{counter}{suffix}"
                    counter += 1

            try:
                if self.clipboard_action == 'copy':
                    if src.is_dir():
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
                elif self.clipboard_action == 'cut':
                    shutil.move(src, dst)
            except Exception as e:
                messagebox.showerror("Error", f"Operation failed for {src.name}: {e}")

        # Clear clipboard if cut
        if self.clipboard_action == 'cut':
            self.clipboard_files = []
            self.clipboard_action = None
            
        self.refresh()

    # --- Helpers ---
    def _format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"

    def sort_tree(self, col, reverse):
        # Retrieve data from tree
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        
        # Sort logic
        try:
            # Try converting to number for size sorting
            if col == "size":
                # Helper to parse size string back to bytes roughly for sorting
                def parse_size(s):
                    if not s: return -1
                    parts = s.split()
                    val = float(parts[0])
                    unit = parts[1]
                    multipliers = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3}
                    return val * multipliers.get(unit, 1)
                l.sort(key=lambda t: parse_size(t[0]), reverse=reverse)
            else:
                l.sort(key=lambda t: t[0].lower(), reverse=reverse)
        except ValueError:
            l.sort(reverse=reverse)

        # Rearrange items in sorted positions
        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)

        # Reverse sort next time
        self.tree.heading(col, command=lambda: self.sort_tree(col, not reverse))


if __name__ == "__main__":
    root = tk.Tk()
    app = FileManagerApp(root)
    root.mainloop()