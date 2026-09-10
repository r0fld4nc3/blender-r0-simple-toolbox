import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

_logger: Optional[logging.Logger] = None


def _close_and_remove_handlers(logger: logging.Logger) -> None:
    """Flush, close and remove all handlers from a logger."""
    for handler in logger.handlers[:]:
        try:
            handler.flush()
            handler.close()
        except Exception as e:
            pass
        logger.removeHandler(handler)


def configure_logging(
    logger_name: str, log_file: Path, level: int = logging.INFO, console: bool = True
) -> logging.Logger:

    if log_file.exists() and not log_file.is_file():
        raise RuntimeError(f"Attempting to create/ensure directory when a file path has been given: '{log_file}'.")

    log_file.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger(logger_name)
    root.setLevel(level)
    root.propagate = False

    _close_and_remove_handlers(root)

    # [%(asctime)s]
    formatter = logging.Formatter("[%(levelname)s] [%(name)s] %(message)s", datefmt="%d-%m-%Y %H:%M:%S")

    # Remove any pre-existing handlers.
    root.handlers.clear()

    file_handler = RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    if console:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        root.addHandler(stream_handler)

    global _logger
    _logger = root
    return root


def reset_log_file(log_file: Path) -> None:
    global _logger

    if _logger:
        for handler in _logger.handlers:
            if isinstance(handler, RotatingFileHandler):
                try:
                    handler.doRollover()
                    return
                except Exception as e:
                    print(f"Error rolling over log file: {e}")
                    # raise RuntimeError(f"Error rolling over log file: {e}")

    # Fallback when logging has not been configured
    try:
        with open(log_file, "w", encoding="utf-8") as f:
            f.write("")
    except Exception as e:
        print(f"Error resetting log file: {e}")
        # raise RuntimeError(f"Error resetting log file: {e}")


def shutdown_logging(logger_name: str) -> None:
    logger = logging.getLogger(logger_name)
    _close_and_remove_handlers(logger)

    global _logger
    if _logger is logger:
        _logger = None


def get_root_logger() -> Optional[logging.Logger]:
    global _logger
    return _logger


def set_root_logger_level(level: int) -> None:
    global _logger

    if not _logger:
        return

    _logger.setLevel(level)
