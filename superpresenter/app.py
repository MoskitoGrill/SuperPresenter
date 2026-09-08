"""Application startup. Importing this module does not create windows."""
import logging
from superpresenter.ui.main_window import GUI


def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s: %(message)s')
    gui = GUI()
    gui.song_editor_widget.start_recovery(on_restored=gui.on_editor_restored)
    gui.run()
