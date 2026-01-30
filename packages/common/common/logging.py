import logging
import logging.config
from .config import load_logging_config


def setup_logging() -> None:
    cfg = load_logging_config()
    logging.config.dictConfig(cfg)
