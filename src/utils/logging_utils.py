import logging
import sys

def setup_logger(name="RouteMindAI", level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(level)
        fmt = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s')
        ch.setFormatter(fmt)
        logger.addHandler(ch)
    return logger

logger = setup_logger()
