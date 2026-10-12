import tkinter as tk
from .ui import MainWindow
from .projection import configure_dpi

def main():
    configure_dpi()
    root = tk.Tk()
    MainWindow(root)
    root.mainloop()
