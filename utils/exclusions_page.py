"""
GUI page for managing user-defined scan exclusions.
"""

import os
import tkinter as tk
from tkinter import Frame, Label, Button, Listbox, Scrollbar, filedialog, messagebox, Entry, StringVar
from tkinter import END, BOTH, LEFT, RIGHT, Y, X, TOP, BOTTOM
from utils.user_exclusions import get_user_exclusions


class ExclusionsPage(Frame):
    """GUI page for managing scan exclusions."""
    
    def __init__(self, parent, show_page_callback):
        super().__init__(parent, bg="#ffffff")
        self.show_page = show_page_callback
        self.user_excl = get_user_exclusions()
        
        # Title
        title_frame = Frame(self, bg="#009AA5", height=60)
        title_frame.pack(fill=X)
        title_frame.pack_propagate(False)
        
        Label(
            title_frame,
            text="⚙️ Scan Exclusions",
            font=("Arial", 20, "bold"),
            bg="#009AA5",
            fg="white"
        ).pack(pady=15)
        
        # Main content
        content = Frame(self, bg="#ffffff")
        content.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # Instructions
        Label(
            content,
            text="Exclude folders and files from scanning. These items will be skipped during all scans.",
            font=("Arial", 11),
            bg="#ffffff",
            fg="#555555",
            wraplength=800,
            justify=LEFT
        ).pack(anchor="w", pady=(0, 20))
        
        # ===== Excluded Paths Section =====
        paths_frame = Frame(content, bg="#ffffff")
        paths_frame.pack(fill=BOTH, expand=True, pady=(0, 20))
        
        Label(
            paths_frame,
            text="📁 Excluded Folders & Files",
            font=("Arial", 14, "bold"),
            bg="#ffffff",
            fg="#333333"
        ).pack(anchor="w", pady=(0, 10))
        
        # Listbox with scrollbar
        list_frame = Frame(paths_frame, bg="#ffffff")
        list_frame.pack(fill=BOTH, expand=True)
        
        scrollbar = Scrollbar(list_frame)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        self.paths_listbox = Listbox(
            list_frame,
            font=("Courier New", 10),
            yscrollcommand=scrollbar.set,
            selectmode=tk.SINGLE,
            bg="#f9f9f9",
            relief=tk.SOLID,
            borderwidth=1
        )
        self.paths_listbox.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.config(command=self.paths_listbox.yview)
        
        # Buttons for paths
        path_buttons = Frame(paths_frame, bg="#ffffff")
        path_buttons.pack(fill=X, pady=(10, 0))
        
        Button(
            path_buttons,
            text="➕ Add Folder",
            font=("Arial", 11),
            bg="#007777",
            fg="white",
            command=self.add_folder,
            cursor="hand2"
        ).pack(side=LEFT, padx=(0, 10))
        
        Button(
            path_buttons,
            text="➕ Add File",
            font=("Arial", 11),
            bg="#007777",
            fg="white",
            command=self.add_file,
            cursor="hand2"
        ).pack(side=LEFT, padx=(0, 10))
        
        Button(
            path_buttons,
            text="➖ Remove Selected",
            font=("Arial", 11),
            bg="#cc4444",
            fg="white",
            command=self.remove_path,
            cursor="hand2"
        ).pack(side=LEFT, padx=(0, 10))
        
        # ===== Excluded Extensions Section =====
        ext_frame = Frame(content, bg="#ffffff")
        ext_frame.pack(fill=X, pady=(0, 20))
        
        Label(
            ext_frame,
            text="📄 Excluded File Extensions",
            font=("Arial", 14, "bold"),
            bg="#ffffff",
            fg="#333333"
        ).pack(anchor="w", pady=(0, 10))
        
        Label(
            ext_frame,
            text="Skip files with specific extensions (e.g., .mp4, .iso, .vmdk)",
            font=("Arial", 10),
            bg="#ffffff",
            fg="#666666"
        ).pack(anchor="w", pady=(0, 10))
        
        # Extensions list
        ext_list_frame = Frame(ext_frame, bg="#ffffff")
        ext_list_frame.pack(fill=X)
        
        ext_scrollbar = Scrollbar(ext_list_frame)
        ext_scrollbar.pack(side=RIGHT, fill=Y)
        
        self.ext_listbox = Listbox(
            ext_list_frame,
            font=("Courier New", 10),
            yscrollcommand=ext_scrollbar.set,
            selectmode=tk.SINGLE,
            bg="#f9f9f9",
            relief=tk.SOLID,
            borderwidth=1,
            height=6
        )
        self.ext_listbox.pack(side=LEFT, fill=BOTH, expand=True)
        ext_scrollbar.config(command=self.ext_listbox.yview)
        
        # Extension input and buttons
        ext_input_frame = Frame(ext_frame, bg="#ffffff")
        ext_input_frame.pack(fill=X, pady=(10, 0))
        
        Label(
            ext_input_frame,
            text="Extension:",
            font=("Arial", 11),
            bg="#ffffff"
        ).pack(side=LEFT, padx=(0, 10))
        
        self.ext_var = StringVar()
        self.ext_entry = Entry(
            ext_input_frame,
            textvariable=self.ext_var,
            font=("Arial", 11),
            width=15
        )
        self.ext_entry.pack(side=LEFT, padx=(0, 10))
        
        Button(
            ext_input_frame,
            text="➕ Add Extension",
            font=("Arial", 11),
            bg="#007777",
            fg="white",
            command=self.add_extension,
            cursor="hand2"
        ).pack(side=LEFT, padx=(0, 10))
        
        Button(
            ext_input_frame,
            text="➖ Remove Selected",
            font=("Arial", 11),
            bg="#cc4444",
            fg="white",
            command=self.remove_extension,
            cursor="hand2"
        ).pack(side=LEFT)
        
        # ===== Common Exclusions (Quick Add) =====
        quick_frame = Frame(content, bg="#f0f0f0", relief=tk.SOLID, borderwidth=1)
        quick_frame.pack(fill=X, pady=(20, 0))
        
        Label(
            quick_frame,
            text="⚡ Quick Add Common Exclusions",
            font=("Arial", 12, "bold"),
            bg="#f0f0f0",
            fg="#333333"
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        quick_buttons = Frame(quick_frame, bg="#f0f0f0")
        quick_buttons.pack(fill=X, padx=10, pady=(0, 10))
        
        common_exclusions = [
            ("Video Files (.mp4, .avi, .mkv)", ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv']),
            ("ISO/Disk Images", ['.iso', '.img', '.vhd', '.vmdk']),
            ("Archives", ['.zip', '.rar', '.7z', '.tar', '.gz']),
            ("Game Folders", None)  # Special handling
        ]
        
        for label, extensions in common_exclusions:
            if extensions:
                Button(
                    quick_buttons,
                    text=label,
                    font=("Arial", 10),
                    bg="#005555",
                    fg="white",
                    command=lambda exts=extensions: self.quick_add_extensions(exts),
                    cursor="hand2"
                ).pack(side=LEFT, padx=(0, 10), pady=5)
        
        # Bottom buttons
        bottom_frame = Frame(self, bg="#ffffff")
        bottom_frame.pack(fill=X, side=BOTTOM, padx=20, pady=20)
        
        Button(
            bottom_frame,
            text="🔄 Refresh Lists",
            font=("Arial", 12),
            bg="#007777",
            fg="white",
            command=self.refresh_lists,
            cursor="hand2"
        ).pack(side=LEFT, padx=(0, 10))
        
        Button(
            bottom_frame,
            text="🗑️ Clear All Exclusions",
            font=("Arial", 12),
            bg="#cc4444",
            fg="white",
            command=self.clear_all,
            cursor="hand2"
        ).pack(side=LEFT)
        
        Button(
            bottom_frame,
            text="⬅️ Back",
            font=("Arial", 12),
            bg="#666666",
            fg="white",
            command=lambda: self.show_page("settings"),
            cursor="hand2"
        ).pack(side=RIGHT)
        
        # Initial load
        self.refresh_lists()
    
    def refresh_lists(self):
        """Reload exclusion lists from config."""
        self.user_excl.load()
        
        # Refresh paths
        self.paths_listbox.delete(0, END)
        for path in self.user_excl.get_excluded_paths():
            self.paths_listbox.insert(END, path)
        
        # Refresh extensions
        self.ext_listbox.delete(0, END)
        for ext in self.user_excl.get_excluded_extensions():
            self.ext_listbox.insert(END, ext)
    
    def add_folder(self):
        """Add a folder to exclusions."""
        folder = filedialog.askdirectory(title="Select Folder to Exclude")
        if folder:
            if self.user_excl.add_path(folder):
                self.refresh_lists()
                messagebox.showinfo("Success", f"Folder excluded:\n{folder}")
            else:
                messagebox.showerror("Error", "Failed to add folder to exclusions.")
    
    def add_file(self):
        """Add a file to exclusions."""
        file_path = filedialog.askopenfilename(title="Select File to Exclude")
        if file_path:
            if self.user_excl.add_path(file_path):
                self.refresh_lists()
                messagebox.showinfo("Success", f"File excluded:\n{file_path}")
            else:
                messagebox.showerror("Error", "Failed to add file to exclusions.")
    
    def remove_path(self):
        """Remove selected path from exclusions."""
        selection = self.paths_listbox.curselection()
        if selection:
            path = self.paths_listbox.get(selection[0])
            if self.user_excl.remove_path(path):
                self.refresh_lists()
                messagebox.showinfo("Success", f"Removed from exclusions:\n{path}")
            else:
                messagebox.showerror("Error", "Failed to remove path.")
        else:
            messagebox.showwarning("No Selection", "Please select a path to remove.")
    
    def add_extension(self):
        """Add extension from input field."""
        ext = self.ext_var.get().strip()
        if ext:
            if self.user_excl.add_extension(ext):
                self.ext_var.set("")
                self.refresh_lists()
                messagebox.showinfo("Success", f"Extension excluded: {ext}")
            else:
                messagebox.showerror("Error", "Failed to add extension.")
        else:
            messagebox.showwarning("Input Required", "Please enter a file extension.")
    
    def remove_extension(self):
        """Remove selected extension from exclusions."""
        selection = self.ext_listbox.curselection()
        if selection:
            ext = self.ext_listbox.get(selection[0])
            if self.user_excl.remove_extension(ext):
                self.refresh_lists()
                messagebox.showinfo("Success", f"Removed extension: {ext}")
            else:
                messagebox.showerror("Error", "Failed to remove extension.")
        else:
            messagebox.showwarning("No Selection", "Please select an extension to remove.")
    
    def quick_add_extensions(self, extensions):
        """Add multiple extensions at once."""
        added = 0
        for ext in extensions:
            if self.user_excl.add_extension(ext):
                added += 1
        self.refresh_lists()
        messagebox.showinfo("Success", f"Added {added} extensions to exclusions.")
    
    def clear_all(self):
        """Clear all exclusions after confirmation."""
        result = messagebox.askyesno(
            "Clear All Exclusions",
            "Are you sure you want to remove ALL exclusions?\n\nThis action cannot be undone.",
            icon=messagebox.WARNING
        )
        if result:
            self.user_excl.clear_all()
            self.refresh_lists()
            messagebox.showinfo("Success", "All exclusions have been cleared.")
