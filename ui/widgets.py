import tkinter as tk
from tkinter import ttk

class StatusFilterFrame(ttk.Frame):
    def __init__(self, parent, on_filter_changed):
        super().__init__(parent)
        self.on_filter_changed = on_filter_changed
        self._setup_ui()
    
    def _setup_ui(self):
        ttk.Label(self, text="Filter by status:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.status_filter = tk.StringVar(value="All")
        self.status_combo = ttk.Combobox(
            self, 
            textvariable=self.status_filter,
            values=["All", "watched", "watching", "planned", "on_hold"],
            width=15
        )
        self.status_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.status_combo.bind('<<ComboboxSelected>>', lambda e: self.on_filter_changed())
    
    def get_filter(self):
        return self.status_filter.get()


class SearchFrame(ttk.Frame):
    def __init__(self, parent, on_search):
        super().__init__(parent)
        self.on_search = on_search
        self._setup_ui()
    
    def _setup_ui(self):
        ttk.Label(self, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self, textvariable=self.search_var, width=20)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(self, text="Search", command=self._search, width=10).pack(side=tk.LEFT)
        ttk.Button(self, text="Clear", command=self._clear, width=10).pack(side=tk.LEFT, padx=(5, 0))
    
    def _search(self):
        self.on_search(self.search_var.get().strip())
    
    def _clear(self):
        self.search_var.set("")
        self.on_search("")
    
    def get_query(self):
        return self.search_var.get().strip()


class ItemsTree(ttk.Treeview):
    def __init__(self, parent):
        columns = ("ID", "Title", "Type", "Status", "Rating", "Genres")
        super().__init__(parent, columns=columns, show="headings", height=15)
        
        self.heading("ID", text="ID")
        self.heading("Title", text="Title")
        self.heading("Type", text="Type")
        self.heading("Status", text="Status")
        self.heading("Rating", text="Rating")
        self.heading("Genres", text="Genres")
        
        self.column("ID", width=80)
        self.column("Title", width=200)
        self.column("Type", width=100)
        self.column("Status", width=120)
        self.column("Rating", width=80)
        self.column("Genres", width=200)
    
    def clear(self):
        for item in self.get_children():
            self.delete(item)
    
    def add_item(self, item_data):
        self.insert("", tk.END, values=item_data)
    
    def get_selected_id(self):
        selection = self.selection()
        if selection:
            return int(self.item(selection[0])['values'][0])
        return None
    
    def get_selected_item_data(self):
        selection = self.selection()
        if selection:
            return self.item(selection[0])['values']
        return None