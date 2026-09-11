"""Persistent diagnostics without import-time side effects."""
import logging
from logging.handlers import RotatingFileHandler
from superpresenter.services.projection_config import user_config_dir


def configure_logging(directory=None):
    logger = logging.getLogger()
    if any(getattr(handler, '_superpresenter', False) is True for handler in logger.handlers):
        return
    try:
        folder = directory if directory is not None else user_config_dir() / 'logs'
        folder.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(folder / 'superpresenter.log',
                                      maxBytes=2_000_000, backupCount=3, encoding='utf-8')
    except OSError:
        logging.basicConfig(level=logging.INFO)
        logger.exception('Cannot open diagnostic log')
        return
    handler._superpresenter = True
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
