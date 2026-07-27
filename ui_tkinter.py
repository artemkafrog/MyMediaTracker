import tkinter as tk

from ui.main_window import MediaTrackerApp


def main():
    root = tk.Tk()
    app = MediaTrackerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()