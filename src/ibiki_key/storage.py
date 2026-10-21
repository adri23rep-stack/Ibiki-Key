from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from .constants import APP_NAME, ORGANIZATION
from .models import AppState, Macro, Profile, default_profile, utc_now

log = logging.getLogger(__name__)


def resolve_data_dir(project_root: Path) -> tuple[Path, bool]:
    portable = (project_root / "portable.flag").exists()
    if portable:
        return project_root / "data", True
    base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    return base / ORGANIZATION / APP_NAME, False


class Storage:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.profiles_file = data_dir / "ibiki-state.json"
        self.backup_dir = data_dir / "backups"
        self.exports_dir = data_dir / "exports"
        self.logs_dir = data_dir / "logs"
        self._lock = threading.RLock()
        for directory in (data_dir, self.backup_dir, self.exports_dir, self.logs_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def load(self) -> AppState:
        with self._lock:
            if not self.profiles_file.exists():
                state = AppState(profiles=[default_profile()])
                state.active_profile_id = state.profiles[0].id
                self.save(state, make_backup=False)
                return state
            try:
                raw = json.loads(self.profiles_file.read_text(encoding="utf-8"))
                return AppState.from_dict(raw)
            except Exception:
                log.exception("No se pudo leer el estado; intentando copia de seguridad")
                recovered = self._load_latest_backup()
                if recovered:
                    return recovered
                broken = self.profiles_file.with_suffix(".json.corrupt")
                try:
                    shutil.copy2(self.profiles_file, broken)
                except OSError:
                    pass
                state = AppState(profiles=[default_profile()])
                state.active_profile_id = state.profiles[0].id
                return state

    def save(self, state: AppState, make_backup: bool = True) -> None:
        with self._lock:
            for profile in state.profiles:
                profile.validate()
                profile.updated_at = utc_now()
            if make_backup and self.profiles_file.exists():
                self.create_backup()
            payload = json.dumps(state.to_dict(), ensure_ascii=False, indent=2)
            self._atomic_write(self.profiles_file, payload)

    def _atomic_write(self, target: Path, text: str) -> None:
        fd, tmp_name = tempfile.mkstemp(prefix=f".{target.stem}-", suffix=".tmp", dir=target.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, target)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    def create_backup(self) -> Path | None:
        if not self.profiles_file.exists():
            return None
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        destination = self.backup_dir / f"ibiki-state-{stamp}.json"
        shutil.copy2(self.profiles_file, destination)
        self._trim_backups(20)
        return destination

    def _trim_backups(self, keep: int) -> None:
        backups = sorted(self.backup_dir.glob("ibiki-state-*.json"), reverse=True)
        for old in backups[keep:]:
            try:
                old.unlink()
            except OSError:
                log.warning("No se pudo eliminar la copia antigua %s", old)

    def _load_latest_backup(self) -> AppState | None:
        for backup in sorted(self.backup_dir.glob("ibiki-state-*.json"), reverse=True):
            try:
                return AppState.from_dict(json.loads(backup.read_text(encoding="utf-8")))
            except Exception:
                continue
        return None

    def export_profile(self, profile: Profile, destination: Path) -> Path:
        if destination.suffix.lower() != ".ibiki":
            destination = destination.with_suffix(".ibiki")
        payload = {
            "format": "ibiki-profile",
            "version": 1,
            "profile": profile.to_dict(),
        }
        self._atomic_write(destination, json.dumps(payload, ensure_ascii=False, indent=2))
        return destination

    def import_profile(self, source: Path) -> Profile:
        raw: dict[str, Any] = json.loads(source.read_text(encoding="utf-8"))
        if raw.get("format") != "ibiki-profile" or "profile" not in raw:
            raise ValueError("El archivo no es un perfil de Ibiki Key")
        profile = Profile.from_dict(raw["profile"])
        profile = profile.clone(profile.name)
        profile.settings["auto_switch"] = False
        profile.settings["scripts_allowed"] = False
        profile.settings["trusted_actions"] = False
        profile.settings["locked"] = False
        return profile

    def export_macro(self, macro: Macro, destination: Path) -> Path:
        if destination.suffix.lower() != ".ibikimacro":
            destination = destination.with_suffix(".ibikimacro")
        payload = {
            "format": "ibiki-macro",
            "version": 1,
            "macro": {
                "id": macro.id,
                "name": macro.name,
                "scope": macro.scope,
                "steps": [
                    {
                        "id": step.id,
                        "action": {
                            "type": step.action.type,
                            "value": step.action.value,
                            "options": step.action.options,
                        },
                        "delay_after_ms": step.delay_after_ms,
                        "random_delay_ms": step.random_delay_ms,
                        "enabled": step.enabled,
                    }
                    for step in macro.steps
                ],
                "mode": macro.mode,
                "repeat_count": macro.repeat_count,
                "interval_ms": macro.interval_ms,
                "enabled": macro.enabled,
                "stop_on_error": macro.stop_on_error,
            },
        }
        self._atomic_write(destination, json.dumps(payload, ensure_ascii=False, indent=2))
        return destination

    def import_macro(self, source: Path) -> Macro:
        if source.stat().st_size > 5 * 1024 * 1024:
            raise ValueError("El archivo de macro supera el límite de 5 MB")
        raw: dict[str, Any] = json.loads(source.read_text(encoding="utf-8"))
        if raw.get("format") != "ibiki-macro" or "macro" not in raw:
            raise ValueError("El archivo no es una macro de Ibiki Key")
        macro = Macro.from_dict(raw["macro"]).clone(str(raw["macro"].get("name", "Macro importada")))
        macro.validate()
        return macro
