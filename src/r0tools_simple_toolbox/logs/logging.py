import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(log_file: Path, level: int = logging.INFO, console: bool = True) -> None:

    if log_file.exists() and not log_file.is_file():
        raise RuntimeError(f"Attempting to create/ensure directory when a file path has been given: '{log_file}'.")

    log_file.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)

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


def reset_log_file(log_file: Path) -> None:
    try:
        with open(log_file, "w", encoding="utf-8") as f:
            f.write("")
    except Exception as e:
        raise RuntimeError(f"Error resetting log file: {e}")
