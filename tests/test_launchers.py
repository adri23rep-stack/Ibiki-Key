from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LauncherTests(unittest.TestCase):
    def test_run_has_local_and_system_fallbacks(self) -> None:
        script = (ROOT / "run.bat").read_text(encoding="utf-8")
        self.assertLess(script.index("check_runtime.py --quiet"), script.index('start "" /D'))
        self.assertIn("call setup.bat --no-pause", script)
        self.assertIn("pythonw.exe", script)
        self.assertIn("Ibiki_Key.pyw", script)

    def test_setup_keeps_installer_output_visible(self) -> None:
        script = (ROOT / "setup.bat").read_text(encoding="utf-8")
        self.assertIn("--prefer-binary", script)
        self.assertIn("tools\\check_runtime.py", script)
        self.assertIn("tools\\smoke_test.py", script)
        self.assertIn("tools\\run_core_tests.py", script)
        self.assertNotIn('>>"%IBIKI_SETUP_LOG%"', script)
        self.assertIn("pause", script)

    def test_setup_supports_exact_compatible_python_versions(self) -> None:
        script = (ROOT / "setup.bat").read_text(encoding="utf-8")
        self.assertIn("for %%V in (3.12 3.11 3.10)", script)
        self.assertIn("find_compatible_python.ps1", script)
        self.assertIn("struct.calcsize('P') == 8", script)
        self.assertIn("INSTALACION COMPLETA", script)
        self.assertIn("Paso que fallo", script)

    def test_every_goto_target_exists(self) -> None:
        for name in (
            "run.bat",
            "run_console.bat",
            "setup.bat",
            "diagnostics.bat",
            "INSTALAR.bat",
            "INICIAR.bat",
        ):
            script = (ROOT / name).read_text(encoding="utf-8")
            labels = {value.lower() for value in re.findall(r"(?m)^:([A-Za-z0-9_]+)\s*$", script)}
            targets = {value.lower() for value in re.findall(r"(?im)\bgoto\s+:?([A-Za-z0-9_]+)", script)}
            self.assertEqual(targets - labels, set(), name)

    def test_launchers_use_windows_line_endings(self) -> None:
        for name in (
            "run.bat",
            "run_console.bat",
            "setup.bat",
            "run_as_admin.bat",
            "INSTALAR.bat",
            "INICIAR.bat",
        ):
            data = (ROOT / name).read_bytes()
            self.assertIn(b"\r\n", data, name)
            self.assertNotIn(b"\n", data.replace(b"\r\n", b""), name)

    def test_build_outputs_are_named_for_live_dashboard(self) -> None:
        portable = (ROOT / "build_portable.bat").read_text(encoding="utf-8")
        installer = (ROOT / "installer" / "Ibiki_Key.iss").read_text(encoding="utf-8")
        self.assertIn("Ibiki_Key-0.4.0-Alpha-Live-Dashboard-Portable.zip", portable)
        self.assertIn("Ibiki_Key-0.4.0-Alpha-Live-Dashboard-Setup", installer)


if __name__ == "__main__":
    unittest.main()
