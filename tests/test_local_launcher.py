"""Guard against reintroducing the broken Anaconda-base gallery launcher.

The actual same-port Jaal app is exercised by Windows Chromium in CI; this
test checks the CMD launcher does not silently select an unrelated Python.
"""
from pathlib import Path
import unittest


class WindowsLauncherSafetyTests(unittest.TestCase):
    def test_uses_only_isolated_python_and_explains_setup(self):
        root = Path(__file__).resolve().parents[1]
        script = (root / "start-gallery.bat").read_text(encoding="utf-8")
        self.assertIn('if exist ".venv\\Scripts\\python.exe"', script)
        self.assertIn('if /I "%CONDA_DEFAULT_ENV%"=="jaal-viewer"', script)
        self.assertIn('conda run -n jaal-viewer --no-capture-output', script)
        self.assertIn("goto :missing_environment", script)
        self.assertIn("Refusing to use Anaconda (base)", script)
        self.assertIn("Not necessarily a missing Flask package".lower(),
                      script.lower())
        self.assertIn("JAAL_ENABLE_LARGE_LOCAL=1", script)
        self.assertIn("127.0.0.1 --port 8059", script)
        self.assertIn("conda create -n jaal-viewer python=3.11 -y", script)
        self.assertNotIn("python -m flask --app app:app", script.replace(
            'call conda run -n jaal-viewer --no-capture-output python -m flask --app app:app',
            '').replace(
            '"%JAAL_PYTHON%" -m flask --app app:app',
            ''))
