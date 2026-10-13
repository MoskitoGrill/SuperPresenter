import tkinter as tk
from .ui import MainWindow
from .projection import configure_dpi

def main():
    configure_dpi()
    try:
        from tkinterdnd2 import TkinterDnD
    except ImportError:
        root = tk.Tk()
    else:
        root = TkinterDnD.Tk()
    MainWindow(root)
    root.mainloop()
