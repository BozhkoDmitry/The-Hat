import sys
import logging
from logging.handlers import RotatingFileHandler


def get_logger(name):
    """Функция-фабрика логгеров."""
    formatter = logging.Formatter(
        (
            '%(name)s - %(levelname)s - '
            '%(funcName)s - %(lineno)d - %(message)s'
        )
    )
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    file_handler = RotatingFileHandler(
        'main.log', maxBytes=50000000, backupCount=5
    )
    file_handler.setFormatter(formatter)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stdout_handler)
    return logger
