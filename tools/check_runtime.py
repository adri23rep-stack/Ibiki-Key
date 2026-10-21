from __future__ import annotations

import argparse
import importlib
import os
import platform
import sys
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Component:
    import_name: str
    display_name: str
    windows_only: bool = False


COMPONENTS = (
    Component("PySide6", "Interfaz PySide6"),
    Component("keyboard", "Motor de teclado"),
    Component("psutil", "Detección de procesos"),
    Component("pyperclip", "Portapapeles"),
    Component("win32api", "Integración de Windows", windows_only=True),
)


def missing_components(*, windows: bool | None = None) -> list[tuple[Component, str]]:
    is_windows = os.name == "nt" if windows is None else windows
    missing: list[tuple[Component, str]] = []
    for component in COMPONENTS:
        if component.windows_only and not is_windows:
            continue
        try:
            importlib.import_module(component.import_name)
        except Exception as exc:
            missing.append((component, f"{type(exc).__name__}: {exc}"))
    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description="Comprueba el entorno de Ibiki Key")
    parser.add_argument("--quiet", action="store_true", help="Solo devolver el código de salida")
    args = parser.parse_args()
    version_ok = (3, 10) <= sys.version_info[:2] < (3, 13)
    missing = missing_components()
    if args.quiet:
        return 0 if version_ok and not missing else 1

    print("Ibiki Key · diagnóstico del entorno")
    print(f"Python: {platform.python_version()} ({sys.executable})")
    print(f"Sistema: {platform.platform()}")
    if version_ok:
        print("[OK] Versión de Python compatible")
    else:
        print("[ERROR] Se necesita Python 3.10, 3.11 o 3.12")
    missing_names = {item.import_name for item, _ in missing}
    for component in COMPONENTS:
        if component.windows_only and os.name != "nt":
            print(f"[OMITIDO] {component.display_name} (solo Windows)")
        elif component.import_name in missing_names:
            detail = next(detail for item, detail in missing if item == component)
            print(f"[FALTA] {component.display_name}: {detail}")
        else:
            print(f"[OK] {component.display_name}")
    print("[OK] Mouse nativo incluido; no requiere el paquete externo 'mouse'")
    if missing:
        print("\nEjecuta repair_runtime.bat para reparar los componentes faltantes.")
    return 0 if version_ok and not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
