from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any


IS_WINDOWS = sys.platform == "win32"


@dataclass(frozen=True, slots=True)
class SystemMouseSettings:
    cursor_speed: int
    double_click_ms: int
    scroll_lines: int


def is_admin() -> bool:
    if not IS_WINDOWS:
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin() -> bool:
    if not IS_WINDOWS:
        return False
    params = subprocess.list2cmdline(sys.argv)
    executable = sys.executable
    try:
        result = ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, params, None, 1)
        return result > 32
    except Exception:
        return False


def foreground_window() -> tuple[str, str]:
    """Return (process_name, window_title); empty strings on failure."""
    if not IS_WINDOWS:
        return "", ""
    try:
        import psutil
        import win32gui
        import win32process

        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd) or ""
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        process = psutil.Process(pid).name().lower()
        return process, title
    except Exception:
        return _foreground_window_ctypes()


def process_running(process_name: str) -> bool:
    expected = Path(process_name.strip().lower()).name
    if expected and "." not in expected:
        expected += ".exe"
    try:
        import psutil

        for process in psutil.process_iter(["name"]):
            try:
                if str(process.info.get("name") or "").lower() == expected:
                    return True
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
    except Exception:
        return False
    return False


def _foreground_window_ctypes() -> tuple[str, str]:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return "", ""
    length = user32.GetWindowTextLengthW(hwnd)
    title_buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, title_buffer, length + 1)
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    name = ""
    if handle:
        try:
            size = wintypes.DWORD(32768)
            path_buffer = ctypes.create_unicode_buffer(size.value)
            if kernel32.QueryFullProcessImageNameW(handle, 0, path_buffer, ctypes.byref(size)):
                name = Path(path_buffer.value).name.lower()
        finally:
            kernel32.CloseHandle(handle)
    return name, title_buffer.value


def idle_seconds() -> float:
    if not IS_WINDOWS:
        return 0.0

    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(info)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        return 0.0
    tick = ctypes.windll.kernel32.GetTickCount()
    return max(0.0, (tick - info.dwTime) / 1000.0)


def caps_lock_active() -> bool:
    if not IS_WINDOWS:
        return False
    return bool(ctypes.windll.user32.GetKeyState(0x14) & 1)


def set_cursor_speed(speed: int) -> bool:
    if not IS_WINDOWS:
        return False
    speed = max(1, min(20, int(speed)))
    SPI_SETMOUSESPEED = 0x0071
    SPIF_UPDATEINIFILE = 0x01
    SPIF_SENDCHANGE = 0x02
    return bool(
        ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETMOUSESPEED,
            0,
            speed,
            SPIF_UPDATEINIFILE | SPIF_SENDCHANGE,
        )
    )


def get_cursor_speed() -> int | None:
    if not IS_WINDOWS:
        return None
    value = ctypes.c_int()
    if not ctypes.windll.user32.SystemParametersInfoW(
        0x0070,  # SPI_GETMOUSESPEED
        0,
        ctypes.byref(value),
        0,
    ):
        return None
    return max(1, min(20, int(value.value)))


def set_double_click_time(milliseconds: int) -> bool:
    if not IS_WINDOWS:
        return False
    return bool(ctypes.windll.user32.SetDoubleClickTime(max(100, min(2000, milliseconds))))


def get_double_click_time() -> int | None:
    if not IS_WINDOWS:
        return None
    return int(ctypes.windll.user32.GetDoubleClickTime())


def set_scroll_lines(lines: int) -> bool:
    if not IS_WINDOWS:
        return False
    SPI_SETWHEELSCROLLLINES = 0x0069
    SPIF_UPDATEINIFILE = 0x01
    SPIF_SENDCHANGE = 0x02
    requested = int(lines)
    value = 0xFFFFFFFF if requested == 0xFFFFFFFF else max(1, min(100, requested))
    return bool(
        ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETWHEELSCROLLLINES,
            value,
            None,
            SPIF_UPDATEINIFILE | SPIF_SENDCHANGE,
        )
    )


def get_scroll_lines() -> int | None:
    if not IS_WINDOWS:
        return None
    value = ctypes.c_uint()
    if not ctypes.windll.user32.SystemParametersInfoW(
        0x0068,  # SPI_GETWHEELSCROLLLINES
        0,
        ctypes.byref(value),
        0,
    ):
        return None
    return int(value.value)


def capture_mouse_settings() -> SystemMouseSettings | None:
    speed = get_cursor_speed()
    double_click = get_double_click_time()
    scroll = get_scroll_lines()
    if speed is None or double_click is None or scroll is None:
        return None
    return SystemMouseSettings(speed, double_click, scroll)


def restore_mouse_settings(settings: SystemMouseSettings | None) -> bool:
    if settings is None:
        return False
    results = (
        set_cursor_speed(settings.cursor_speed),
        set_double_click_time(settings.double_click_ms),
        set_scroll_lines(settings.scroll_lines),
    )
    return all(results)


def set_start_with_windows(enabled: bool, command: str) -> None:
    if not IS_WINDOWS:
        return
    import winreg

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, "Ibiki Key", 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, "Ibiki Key")
            except FileNotFoundError:
                pass


def open_target(target: str) -> None:
    if IS_WINDOWS:
        os.startfile(target)  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", target])


def run_command(
    command: str,
    *,
    powershell: bool = False,
    hidden: bool = True,
) -> subprocess.Popen[Any]:
    if not IS_WINDOWS:
        raise RuntimeError("Los comandos automáticos solo están disponibles en Windows")
    creationflags = subprocess.CREATE_NO_WINDOW if hidden else 0
    if powershell:
        args = [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ]
    else:
        args = ["cmd.exe", "/d", "/s", "/c", command]
    return subprocess.Popen(args, creationflags=creationflags)


def set_brightness(percent: int) -> None:
    percent = max(0, min(100, int(percent)))
    command = (
        "$m=(Get-CimInstance -Namespace root/WMI "
        "-ClassName WmiMonitorBrightnessMethods);"
        f"if($m){{$m.WmiSetBrightness(1,{percent})|Out-Null}}"
    )
    run_command(command, powershell=True)


def startup_command(project_root: Path) -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --minimized'
    return f'"{sys.executable}" "{project_root / "main.py"}" --minimized'
