"""Isolated real v2 window behind a launcher process, used only by QA."""
import json
import os
from pathlib import Path
import subprocess
import sys

folder = Path(sys.argv[2])
if sys.argv[1] == 'launcher':
    child = subprocess.Popen([sys.executable, '-B', __file__, 'child', str(folder)])
    raise SystemExit(child.wait())

root_path = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root_path))
sys.path.append(str(root_path / '.venv' / 'Lib' / 'site-packages'))
from dataclasses import replace
import tkinter as tk
from presentationpresenter import ui
from presentationpresenter.settings import AppSettings

ui.save_settings = lambda *args, **kwargs: None

def ask_save(*args, **kwargs):
    (folder / 'asked').write_text('save prompt', encoding='utf-8')
    return False if (folder / 'allow-close').exists() else None

ui.messagebox.askyesnocancel = ask_save
root = tk.Tk()
editor = ui.MainWindow(root, AppSettings(), recovery_dir=folder / 'recovery')
editor.commit(replace(editor.document, title='QA close with launcher'))
root.after(300, lambda: (folder / 'ready.json').write_text(
    json.dumps({'pid': os.getpid(), 'title': root.title()}), encoding='utf-8'))
root.after(20000, root.destroy)  # Never leave a QA window alive after a failed test.
root.mainloop()
