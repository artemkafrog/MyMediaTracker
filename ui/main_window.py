import tkinter as tk
from tkinter import ttk, messagebox

from src.catalog import MediaCatalog
from src.database import DatabaseManager
from src.enums import Status
from src.reminder import Reminder
from src.file_io import export_to_csv

from .widgets import StatusFilterFrame, SearchFrame, ItemsTree
from .dialog_windows import AddItemDialog, ViewItemDialog, ChangeStatusDialog, StatsDialog


class MediaTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MediaTracker")
        self.root.geometry("900x600")
        self.root.minsize(800, 500)
        
        self.catalog = MediaCatalog()
        self.db = DatabaseManager()
        self.reminder = Reminder(self.catalog)
        self._load_from_db()
        
        self._setup_ui()
        self._refresh_list()
    
    def _load_from_db(self):
        items = self.db.get_all_items()
        for item in items:
            self.catalog.add_item(item)
        print(f"Loaded {len(items)} items from database")
    
    def _setup_ui(self):
        self.root.configure(bg='#f0f0f0')
        
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        self._create_header(main_frame)
        self._create_filter_frame(main_frame)
        self._create_tree(main_frame)
        self._create_status_bar(main_frame)
        self._create_context_menu()
    
    def _create_header(self, parent):
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text="MediaTracker", font=('Arial', 18, 'bold')).pack(side=tk.LEFT)
        
        btn_frame = ttk.Frame(header_frame)
        btn_frame.pack(side=tk.RIGHT)
        
        ttk.Button(btn_frame, text="Add", command=self._add_item, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Refresh", command=self._refresh_list, width=10).pack(side=tk.LEFT, padx=2)
    
    def _create_filter_frame(self, parent):
        filter_frame = ttk.Frame(parent)
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_filter = StatusFilterFrame(filter_frame, self._refresh_list)
        self.status_filter.pack(side=tk.LEFT)
        
        self.search_frame = SearchFrame(filter_frame, self._search_items)
        self.search_frame.pack(side=tk.LEFT, padx=(20, 0))
    
    def _create_tree(self, parent):
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.tree = ItemsTree(tree_frame)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind('<Double-1>', self._view_item)
        self.tree.bind('<Button-3>', self._show_context_menu)
    
    def _create_status_bar(self, parent):
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_label = ttk.Label(status_frame, text="")
        self.status_label.pack(side=tk.LEFT)
        
        btn_frame = ttk.Frame(status_frame)
        btn_frame.pack(side=tk.RIGHT)
        
        ttk.Button(btn_frame, text="Change Status", command=self._change_status, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Delete", command=self._delete_item, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Export CSV", command=self._export_csv, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Stats", command=self._show_stats, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Backup", command=self._create_backup, width=10).pack(side=tk.LEFT, padx=2)
    
    def _create_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="View", command=self._view_item)
        self.context_menu.add_command(label="Change Status", command=self._change_status)
        self.context_menu.add_command(label="Delete", command=self._delete_item)
    
    def _refresh_list(self):
        self.tree.clear()
        
        status_filter = self.status_filter.get_filter()
        
        if status_filter == "All":
            items = list(self.catalog)
        else:
            for s in Status:
                if s.value == status_filter:
                    items = self.catalog.get_by_status(s)
                    break
            else:
                items = list(self.catalog)
        
        for item in items:
            item_id = id(item)
            genres_str = ", ".join(item.genres[:2])
            if len(item.genres) > 2:
                genres_str += "..."
            
            self.tree.add_item((
                item_id,
                item.title[:30],
                item.get_media_type().value,
                item.status.value,
                f"{item.rating:.1f}",
                genres_str
            ))
        
        self.status_label.config(text=f"Total: {len(items)} items")
    
    def _search_items(self, query):
        if not query:
            self._refresh_list()
            return
        
        try:
            items = self.catalog.search_all(query)
            if not items:
                messagebox.showinfo("Search", f"No items found for: {query}")
                return
            
            self.tree.clear()
            
            for item in items:
                item_id = id(item)
                genres_str = ", ".join(item.genres[:2])
                if len(item.genres) > 2:
                    genres_str += "..."
                
                self.tree.add_item((
                    item_id,
                    item.title[:30],
                    item.get_media_type().value,
                    item.status.value,
                    f"{item.rating:.1f}",
                    genres_str
                ))
            
            self.status_label.config(text=f"Found: {len(items)} items")
            
        except Exception as e:
            messagebox.showerror("Error", f"Search error: {e}")
    
    def _get_selected_item(self):
        item_id = self.tree.get_selected_id()
        if item_id is None:
            messagebox.showwarning("Warning", "Please select an item")
            return None
        
        try:
            return self.catalog.get_item(item_id)
        except Exception:
            messagebox.showerror("Error", "Item not found")
            return None
    
    def _add_item(self):
        AddItemDialog(self.root, self.catalog, self.db)
        self._refresh_list()
    
    def _view_item(self, event=None):
        item = self._get_selected_item()
        if item:
            ViewItemDialog(self.root, item)
    
    def _change_status(self):
        item = self._get_selected_item()
        if item:
            ChangeStatusDialog(self.root, self.catalog, self.db, item, self._refresh_list)
    
    def _delete_item(self):
        item = self._get_selected_item()
        if not item:
            return
        
        if not messagebox.askyesno("Confirm Delete", f"Delete '{item.title}'?"):
            return
        
        try:
            item_id = id(item)
            self.catalog.remove_item(item_id)
            self.db.delete_item(item_id)
            
            messagebox.showinfo("Success", f"Item '{item.title}' deleted")
            self._refresh_list()
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def _export_csv(self):
        try:
            result = export_to_csv(self.catalog)
            messagebox.showinfo("Success", f"Export completed!\nFiles: {', '.join(result.keys())}")
        except Exception as e:
            messagebox.showerror("Error", f"Export error: {e}")
    
    def _show_stats(self):
        StatsDialog(self.root, self.db)
    
    def _create_backup(self):
        try:
            import shutil
            import os
            from datetime import date
            
            backup_dir = "backups"
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = date.today().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"media_tracker_backup_{timestamp}.db")
            
            shutil.copy2(self.db._db_path, backup_path)
            
            csv_dir = os.path.join(backup_dir, f"csv_backup_{timestamp}")
            export_to_csv(self.catalog, csv_dir)
            
            messagebox.showinfo("Success", f"Backup created!\nDB: {backup_path}\nCSV: {csv_dir}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Backup error: {e}")
    
    def _show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)