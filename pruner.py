import sys
import threading
from pathlib import Path

try:
    import pyminiwebview
except ModuleNotFoundError as error:
    if error.name != "pyminiwebview":
        raise
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import pyminiwebview

from pyminiwebview_win32 import FramelessWindow
from pyminiwebview_helpers import call_js
from nuitka_pruner.ui import HTML
from nuitka_pruner.ui_bridge import UIBridge


class PrunerWindow(FramelessWindow):
    def __init__(self, smoke_test=False):
        self.smoke_test = smoke_test
        self.smoke_reported = False
        super().__init__(
            title="Nuitka 自动精简打包器",
            width=1120,
            height=760,
            min_width=900,
            min_height=620,
            app_name="nuitka-pruner",
            bgcolor=0x00F6F8FB,
        )
        self.on_maximize_change = self._on_maximize_change

    def _on_maximize_change(self, maximized):
        if self.view is not None:
            call_js(self.view, "setMaximized", maximized)

    def reveal(self):
        result = super().reveal()
        if self.smoke_test and not self.smoke_reported:
            self.smoke_reported = True
            print("SMOKE_OK", flush=True)
            timer = threading.Timer(0.3, self.close_window)
            timer.daemon = True
            timer.start()
        return result


def main():
    host = PrunerWindow("--smoke-test" in sys.argv)
    bridge = UIBridge(host)
    try:
        bridge.bind()
        host.view.set_html(HTML)
        host.run()
    finally:
        bridge.closed = True
        bridge.engine.shutdown()
        host.close()


if __name__ == "__main__":
    main()
