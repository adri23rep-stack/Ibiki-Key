from __future__ import annotations

import ctypes
import logging
import os
import queue
import threading
import time
from collections.abc import Callable
from ctypes import wintypes
from dataclasses import dataclass

from ..errors import EngineUnavailable

log = logging.getLogger(__name__)

IS_WINDOWS = os.name == "nt"


@dataclass(slots=True)
class MoveEvent:
    x: int
    y: int
    time: float


@dataclass(slots=True)
class WheelEvent:
    delta: int
    time: float
    horizontal: bool = False


@dataclass(slots=True)
class ButtonEvent:
    event_type: str
    button: str
    time: float


class _Point(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class _LowLevelMouseData(ctypes.Structure):
    _fields_ = [
        ("pt", _Point),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class NativeMouseHook:
    """Low-level Windows mouse hook with callbacks dispatched off the hook thread."""

    _STOP = object()

    def __init__(self, callback: Callable[[object], None]):
        _require_windows()
        self.callback = callback
        self._ready = threading.Event()
        self._closed = threading.Event()
        self._events: queue.Queue[object] = queue.Queue(maxsize=4096)
        self._error: Exception | None = None
        self._hook_handle: int | None = None
        self._thread_id: int | None = None
        self._procedure: object | None = None
        self._dispatcher = threading.Thread(
            target=self._dispatch,
            name="IbikiMouseDispatch",
            daemon=True,
        )
        self._thread = threading.Thread(
            target=self._message_loop,
            name="IbikiMouseHook",
            daemon=True,
        )
        self._dispatcher.start()
        self._thread.start()
        if not self._ready.wait(4.0):
            self.close()
            raise EngineUnavailable("Windows no respondió al iniciar el monitor del mouse")
        if self._error:
            self.close()
            raise EngineUnavailable(f"Windows rechazó el monitor del mouse: {self._error}")

    def _message_loop(self) -> None:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        procedure_type = ctypes.WINFUNCTYPE(
            ctypes.c_ssize_t,
            ctypes.c_int,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )
        user32.SetWindowsHookExW.argtypes = [
            ctypes.c_int,
            procedure_type,
            wintypes.HINSTANCE,
            wintypes.DWORD,
        ]
        user32.SetWindowsHookExW.restype = wintypes.HHOOK
        user32.CallNextHookEx.argtypes = [
            wintypes.HHOOK,
            ctypes.c_int,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        user32.CallNextHookEx.restype = ctypes.c_ssize_t
        user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
        user32.UnhookWindowsHookEx.restype = wintypes.BOOL
        kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        kernel32.GetModuleHandleW.restype = wintypes.HMODULE
        kernel32.GetCurrentThreadId.argtypes = []
        kernel32.GetCurrentThreadId.restype = wintypes.DWORD

        def procedure(code: int, message: int, pointer: int) -> int:
            if code >= 0 and not self._closed.is_set():
                try:
                    data = ctypes.cast(
                        pointer,
                        ctypes.POINTER(_LowLevelMouseData),
                    ).contents
                    event = self._translate(message, data)
                    if event is not None:
                        try:
                            self._events.put_nowait(event)
                        except queue.Full:
                            log.warning("Se descartó un evento de mouse por saturación")
                except Exception:
                    log.exception("No se pudo interpretar un evento nativo de mouse")
            return int(user32.CallNextHookEx(self._hook_handle, code, message, pointer))

        try:
            self._thread_id = int(kernel32.GetCurrentThreadId())
            self._procedure = procedure_type(procedure)
            module = kernel32.GetModuleHandleW(None)
            handle = user32.SetWindowsHookExW(14, self._procedure, module, 0)  # WH_MOUSE_LL
            if not handle:
                raise ctypes.WinError(int(kernel32.GetLastError()))
            self._hook_handle = int(handle)
            self._ready.set()
            message = wintypes.MSG()
            while not self._closed.is_set():
                result = int(user32.GetMessageW(ctypes.byref(message), None, 0, 0))
                if result <= 0:
                    break
                user32.TranslateMessage(ctypes.byref(message))
                user32.DispatchMessageW(ctypes.byref(message))
        except Exception as exc:
            self._error = exc
            self._ready.set()
        finally:
            if self._hook_handle:
                user32.UnhookWindowsHookEx(self._hook_handle)
            self._hook_handle = None
            self._closed.set()
            self._ready.set()
            try:
                self._events.put_nowait(self._STOP)
            except queue.Full:
                pass

    @staticmethod
    def _translate(message: int, data: _LowLevelMouseData) -> object | None:
        now = time.time()
        if message == 0x0200:  # WM_MOUSEMOVE
            return MoveEvent(int(data.pt.x), int(data.pt.y), now)
        if message in {0x020A, 0x020E}:  # WM_MOUSEWHEEL / WM_MOUSEHWHEEL
            raw = (int(data.mouseData) >> 16) & 0xFFFF
            signed = raw - 0x10000 if raw & 0x8000 else raw
            return WheelEvent(1 if signed > 0 else -1, now, horizontal=message == 0x020E)
        buttons = {
            0x0201: ("down", "left"),
            0x0202: ("up", "left"),
            0x0203: ("double", "left"),
            0x0204: ("down", "right"),
            0x0205: ("up", "right"),
            0x0206: ("double", "right"),
            0x0207: ("down", "middle"),
            0x0208: ("up", "middle"),
            0x0209: ("double", "middle"),
        }
        if message in buttons:
            event_type, button = buttons[message]
            return ButtonEvent(event_type, button, now)
        if message in {0x020B, 0x020C, 0x020D}:  # XBUTTON down/up/double
            number = (int(data.mouseData) >> 16) & 0xFFFF
            event_type = {0x020B: "down", 0x020C: "up", 0x020D: "double"}[message]
            return ButtonEvent(event_type, "x2" if number == 2 else "x", now)
        return None

    def _dispatch(self) -> None:
        while True:
            event = self._events.get()
            if event is self._STOP:
                return
            try:
                self.callback(event)
            except Exception:
                log.exception("Falló un callback del monitor de mouse")

    def close(self) -> None:
        already_closed = self._closed.is_set()
        self._closed.set()
        if not already_closed and self._hook_handle:
            try:
                ctypes.windll.user32.UnhookWindowsHookEx(self._hook_handle)
            except Exception:
                pass
        if not already_closed and self._thread_id:
            try:
                ctypes.windll.user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)  # WM_QUIT
            except Exception:
                pass
        try:
            self._events.put_nowait(self._STOP)
        except queue.Full:
            pass
        if self._thread.is_alive() and threading.current_thread() is not self._thread:
            self._thread.join(timeout=1.0)
        if self._dispatcher.is_alive() and threading.current_thread() is not self._dispatcher:
            self._dispatcher.join(timeout=1.0)


def hook(callback: Callable[[object], None]) -> NativeMouseHook:
    return NativeMouseHook(callback)


def unhook(handle: object) -> None:
    if isinstance(handle, NativeMouseHook):
        handle.close()


def get_position() -> tuple[int, int]:
    _require_windows()
    point = _Point()
    if not ctypes.windll.user32.GetCursorPos(ctypes.byref(point)):
        raise ctypes.WinError()
    return int(point.x), int(point.y)


def move(
    x: int,
    y: int,
    *,
    absolute: bool = True,
    duration: float = 0.0,
    cancel: threading.Event | None = None,
) -> None:
    _require_windows()
    start_x, start_y = get_position()
    target_x = int(x) if absolute else start_x + int(x)
    target_y = int(y) if absolute else start_y + int(y)
    duration = max(0.0, min(float(duration), 60.0))
    if cancel and cancel.is_set():
        return
    if duration <= 0:
        if not ctypes.windll.user32.SetCursorPos(target_x, target_y):
            raise ctypes.WinError()
        return
    steps = max(1, min(600, round(duration * 60)))
    started = time.monotonic()
    for index in range(1, steps + 1):
        if cancel and cancel.is_set():
            return
        ratio = index / steps
        current_x = round(start_x + (target_x - start_x) * ratio)
        current_y = round(start_y + (target_y - start_y) * ratio)
        ctypes.windll.user32.SetCursorPos(current_x, current_y)
        remaining = started + duration * ratio - time.monotonic()
        if remaining > 0:
            time.sleep(remaining)


def press(button: str = "left") -> None:
    down, _, data = _button_flags(button)
    _mouse_event(down, data)


def release(button: str = "left") -> None:
    _, up, data = _button_flags(button)
    _mouse_event(up, data)


def click(button: str = "left") -> None:
    press(button)
    release(button)


def double_click(button: str = "left", *, cancel: threading.Event | None = None) -> None:
    if cancel and cancel.is_set():
        return
    click(button)
    if cancel:
        if cancel.wait(0.04):
            return
    else:
        time.sleep(0.04)
    click(button)


def wheel(amount: int) -> None:
    _mouse_event(0x0800, int(amount) * 120)  # MOUSEEVENTF_WHEEL


def horizontal_wheel(amount: int) -> None:
    _mouse_event(0x01000, int(amount) * 120)  # MOUSEEVENTF_HWHEEL


def is_pressed(button: str) -> bool:
    _require_windows()
    virtual_keys = {
        "left": 0x01,
        "right": 0x02,
        "middle": 0x04,
        "x": 0x05,
        "x2": 0x06,
    }
    normalized = str(button).strip().lower()
    if normalized not in virtual_keys:
        return False
    return bool(ctypes.windll.user32.GetAsyncKeyState(virtual_keys[normalized]) & 0x8000)


def _button_flags(button: str) -> tuple[int, int, int]:
    normalized = str(button).strip().lower()
    flags = {
        "left": (0x0002, 0x0004, 0),
        "right": (0x0008, 0x0010, 0),
        "middle": (0x0020, 0x0040, 0),
        "x": (0x0080, 0x0100, 1),
        "x2": (0x0080, 0x0100, 2),
    }
    if normalized not in flags:
        raise ValueError(f"Botón de mouse no compatible: {button}")
    return flags[normalized]


def _mouse_event(flags: int, data: int = 0) -> None:
    _require_windows()
    unsigned_data = int(data) & 0xFFFFFFFF
    ctypes.windll.user32.mouse_event(int(flags), 0, 0, unsigned_data, 0)


def _require_windows() -> None:
    if not IS_WINDOWS:
        raise EngineUnavailable("El motor nativo de mouse solo está disponible en Windows")
