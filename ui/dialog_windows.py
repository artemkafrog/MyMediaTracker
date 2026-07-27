import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import date

from src.media import Book, Movie, TVSeries
from src.enums import MediaType, Status
from src.exceptions import DuplicateError


class AddItemDialog:
    def __init__(self, parent, catalog, db):
        self.parent = parent
        self.catalog = catalog
        self.db = db
        self.seasons_data = {}
        self.result = None
        
        self._create_dialog()
    
    def _create_dialog(self):
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Add Item")
        self.dialog.geometry("400x550")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Add New Item", font=('Arial', 14, 'bold')).pack(pady=(0, 15))
        
        self._create_type_selector(main_frame)
        self._create_title_field(main_frame)
        self._create_rating_field(main_frame)
        self._create_status_selector(main_frame)
        self._create_genres_field(main_frame)
        self._create_year_field(main_frame)
        self._create_extra_field(main_frame)
        self._create_seasons_frame(main_frame)
        self._create_buttons(main_frame)
    
    def _create_type_selector(self, parent):
        ttk.Label(parent, text="Type:").pack(anchor=tk.W)
        self.type_var = tk.StringVar(value="Book")
        self.type_combo = ttk.Combobox(
            parent, 
            textvariable=self.type_var,
            values=["Book", "Movie", "TV Series"],
            state="readonly"
        )
        self.type_combo.pack(fill=tk.X, pady=(0, 10))
        self.type_combo.bind('<<ComboboxSelected>>', self._on_type_changed)
    
    def _create_title_field(self, parent):
        ttk.Label(parent, text="Title:").pack(anchor=tk.W)
        self.title_entry = ttk.Entry(parent, width=40)
        self.title_entry.pack(fill=tk.X, pady=(0, 10))
    
    def _create_rating_field(self, parent):
        ttk.Label(parent, text="Rating (0-10):").pack(anchor=tk.W)
        self.rating_entry = ttk.Entry(parent)
        self.rating_entry.insert(0, "0.0")
        self.rating_entry.pack(fill=tk.X, pady=(0, 10))
    
    def _create_status_selector(self, parent):
        ttk.Label(parent, text="Status:").pack(anchor=tk.W)
        self.status_var = tk.StringVar(value="planned")
        self.status_combo = ttk.Combobox(
            parent,
            textvariable=self.status_var,
            values=[s.value for s in Status],
            state="readonly"
        )
        self.status_combo.pack(fill=tk.X, pady=(0, 10))
    
    def _create_genres_field(self, parent):
        ttk.Label(parent, text="Genres (comma separated):").pack(anchor=tk.W)
        self.genres_entry = ttk.Entry(parent)
        self.genres_entry.pack(fill=tk.X, pady=(0, 10))
    
    def _create_year_field(self, parent):
        ttk.Label(parent, text="Year:").pack(anchor=tk.W)
        self.year_entry = ttk.Entry(parent)
        self.year_entry.insert(0, str(date.today().year))
        self.year_entry.pack(fill=tk.X, pady=(0, 10))
    
    def _create_extra_field(self, parent):
        self.extra_frame = ttk.LabelFrame(parent, text="Additional Info")
        self.extra_frame.pack(fill=tk.X, pady=(5, 10))
        
        self.extra_label = ttk.Label(self.extra_frame, text="")
        self.extra_label.pack(pady=5)
        self.extra_entry = ttk.Entry(self.extra_frame)
        self.extra_entry.pack(fill=tk.X, padx=5, pady=(0, 5))
        self.extra_entry.insert(0, "0")
    
    def _create_seasons_frame(self, parent):
        self.seasons_frame = ttk.LabelFrame(parent, text="Seasons (for TV Series)")
        self.seasons_frame.pack(fill=tk.X, pady=(5, 10))
        
        self.seasons_label = ttk.Label(self.seasons_frame, text="", wraplength=350)
        self.seasons_label.pack(pady=5)
        
        ttk.Button(self.seasons_frame, text="Add Season", command=self._add_season).pack(pady=5)
    
    def _create_buttons(self, parent):
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(pady=(10, 0))
        
        ttk.Button(btn_frame, text="Cancel", command=self.dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Add", command=self._submit, width=10).pack(side=tk.LEFT, padx=5)
    
    def _on_type_changed(self, event):
        media_type = self.type_var.get()
        if media_type == "Book":
            self.extra_label.config(text="Pages:")
        elif media_type == "Movie":
            self.extra_label.config(text="Minutes:")
        else:
            self.extra_label.config(text="Seasons:")
        self.extra_entry.delete(0, tk.END)
        self.extra_entry.insert(0, "0")
    
    def _add_season(self):
        try:
            season_num = len(self.seasons_data) + 1
            episodes = simpledialog.askinteger(
                "Season",
                f"Enter episodes count for season {season_num}:",
                parent=self.dialog,
                minvalue=1,
                maxvalue=100
            )
            if episodes:
                self.seasons_data[season_num] = [45] * episodes
                self.seasons_label.config(text=f"Seasons: {list(self.seasons_data.keys())}")
        except Exception:
            pass
    
    def _submit(self):
        try:
            media_type = self.type_var.get()
            title = self.title_entry.get().strip()
            if not title:
                messagebox.showerror("Error", "Title is required")
                return
            
            rating = float(self.rating_entry.get() or 0)
            if rating < 0 or rating > 10:
                messagebox.showerror("Error", "Rating must be between 0 and 10")
                return
            
            status = None
            for s in Status:
                if s.value == self.status_var.get():
                    status = s
                    break
            if not status:
                status = Status.PLANNED
            
            genres = [g.strip() for g in self.genres_entry.get().split(",") if g.strip()]
            year = int(self.year_entry.get() or date.today().year)
            release_date = date(year, 1, 1)
            
            if media_type == "Book":
                pages = int(self.extra_entry.get() or 0)
                item = Book(title, release_date, rating, status, genres, pages)
            elif media_type == "Movie":
                minutes = int(self.extra_entry.get() or 0)
                item = Movie(title, release_date, rating, status, genres, minutes)
            else:
                if not self.seasons_data:
                    messagebox.showerror("Error", "Please add at least one season")
                    return
                item = TVSeries(title, release_date, rating, status, genres, self.seasons_data)
            
            self.catalog.add_item(item)
            self.db.add_item(item)
            
            messagebox.showinfo("Success", "Item added successfully!")
            self.dialog.destroy()
            
        except DuplicateError as e:
            messagebox.showerror("Error", str(e))
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {e}")
        except Exception as e:
            messagebox.showerror("Error", str(e))


class ViewItemDialog:
    def __init__(self, parent, item):
        self.parent = parent
        self.item = item
        self._create_dialog()
    
    def _create_dialog(self):
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Item Details")
        self.dialog.geometry("500x450")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Item Details", font=('Arial', 14, 'bold')).pack(pady=(0, 15))
        
        from src.interactions import describe_item
        desc = describe_item(self.item)
        
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=('Courier', 10), height=15)
        text_widget.insert(tk.END, desc)
        text_widget.config(state=tk.DISABLED)
        
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        ttk.Button(main_frame, text="Close", command=self.dialog.destroy, width=10).pack(pady=(10, 0))


class ChangeStatusDialog:
    def __init__(self, parent, catalog, db, item, on_success):
        self.parent = parent
        self.catalog = catalog
        self.db = db
        self.item = item
        self.on_success = on_success
        self._create_dialog()
    
    def _create_dialog(self):
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Change Status")
        self.dialog.geometry("300x200")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text=f"Current status: {self.item.status.value}").pack(pady=(0, 15))
        
        ttk.Label(main_frame, text="New status:").pack(anchor=tk.W)
        
        self.status_var = tk.StringVar(value=self.item.status.value)
        self.status_combo = ttk.Combobox(
            main_frame,
            textvariable=self.status_var,
            values=[s.value for s in Status],
            state="readonly"
        )
        self.status_combo.pack(fill=tk.X, pady=(5, 15))
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=(10, 0))
        
        ttk.Button(btn_frame, text="Cancel", command=self.dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Update", command=self._submit, width=10).pack(side=tk.LEFT, padx=5)
    
    def _submit(self):
        try:
            new_status = None
            for s in Status:
                if s.value == self.status_var.get():
                    new_status = s
                    break
            
            if not new_status:
                messagebox.showerror("Error", "Invalid status")
                return
            
            item_id = id(self.item)
            self.catalog.update_status(item_id, new_status)
            self.db.update_item(item_id, self.item)
            
            messagebox.showinfo("Success", f"Status changed to: {new_status.value}")
            self.dialog.destroy()
            self.on_success()
            
        except Exception as e:
            messagebox.showerror("Error", str(e))


class StatsDialog:
    def __init__(self, parent, db):
        self.parent = parent
        self.db = db
        self._create_dialog()
    
    def _create_dialog(self):
        try:
            stats = self.db.get_stats()
            
            self.dialog = tk.Toplevel(self.parent)
            self.dialog.title("Statistics")
            self.dialog.geometry("400x350")
            self.dialog.resizable(False, False)
            self.dialog.transient(self.parent)
            self.dialog.grab_set()
            
            main_frame = ttk.Frame(self.dialog, padding="20")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(main_frame, text="Statistics", font=('Arial', 14, 'bold')).pack(pady=(0, 15))
            
            stats_text = f"""
General statistics:
  Total items: {stats['total']}
  Average rating: {stats['avg_rating']}

By status:
"""
            for status, count in stats['by_status'].items():
                stats_text += f"  {status.value}: {count}\n"
            
            stats_text += "\nBy type:\n"
            for media_type, count in stats['by_type'].items():
                stats_text += f"  {media_type.value}: {count}\n"
            
            text_widget = tk.Text(main_frame, wrap=tk.WORD, font=('Courier', 10), height=12)
            text_widget.insert(tk.END, stats_text)
            text_widget.config(state=tk.DISABLED)
            text_widget.pack(fill=tk.BOTH, expand=True)
            
            ttk.Button(main_frame, text="Close", command=self.dialog.destroy, width=10).pack(pady=(10, 0))
            
        except Exception as e:
            messagebox.showerror("Error", f"Error getting statistics: {e}")