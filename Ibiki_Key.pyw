from __future__ import annotations

import ctypes
import sys
import traceback
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _report_startup_error(detail: str) -> None:
    logs = ROOT / "data" / "logs"
    try:
        logs.mkdir(parents=True, exist_ok=True)
        (logs / "launch-error.log").write_text(
            f"{datetime.now().isoformat(timespec='seconds')}\n{detail}",
            encoding="utf-8",
        )
    except OSError:
        pass
    message = (
        "Ibiki Key no pudo iniciar.\n\n"
        f"{detail[-1400:]}\n\n"
        "Ejecuta diagnostics.bat o run_console.bat para ver el error completo."
    )
    try:
        ctypes.windll.user32.MessageBoxW(None, message, "Error al iniciar Ibiki Key", 0x10)
    except Exception:
        pass


if __name__ == "__main__":
    try:
        from ibiki_key.app import run

        raise SystemExit(run())
    except SystemExit:
        raise
    except Exception:
        error = traceback.format_exc()
        _report_startup_error(error)
        raise SystemExit(1)
