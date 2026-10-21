from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "ibiki-key.log"
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    file_handler = RotatingFileHandler(log_file, maxBytes=2_000_000, backupCount=4, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    if getattr(sys, "frozen", False) is False:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        root.addHandler(console)
    return log_file
