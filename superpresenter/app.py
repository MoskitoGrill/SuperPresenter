"""Application startup. Importing this module does not create windows."""
import logging
from superpresenter.logging_setup import configure_logging
from superpresenter.ui.main_window import GUI


def main():
    configure_logging()
    try:
        gui = GUI()
        gui.song_editor_widget.start_recovery(on_restored=gui.on_editor_restored)
        gui.run()
    except Exception:
        logging.getLogger(__name__).exception('Application startup failed')
        raise
