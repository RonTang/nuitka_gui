import ctypes
import os
import shutil
from ctypes import wintypes
from pathlib import Path

from pyminiwebview_helpers import call_js
from pyminiwebview_win32 import open_file_dialog, save_file_dialog

from .candidates import detect_plugins, directory_size
from .orchestrator import PrunerEngine
from .report import export_file, make_report
from .web_assets import detect_web_assets


class _BROWSEINFO(ctypes.Structure):
    _fields_ = [
        ("hwndOwner", wintypes.HWND), ("pidlRoot", ctypes.c_void_p),
        ("pszDisplayName", wintypes.LPWSTR), ("lpszTitle", wintypes.LPCWSTR),
        ("ulFlags", wintypes.UINT), ("lpfn", ctypes.c_void_p),
        ("lParam", wintypes.LPARAM), ("iImage", ctypes.c_int),
    ]


def pick_directory(hwnd=None):
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    ole32 = ctypes.WinDLL("ole32", use_last_error=True)
    shell32.SHBrowseForFolderW.argtypes = [ctypes.POINTER(_BROWSEINFO)]
    shell32.SHBrowseForFolderW.restype = ctypes.c_void_p
    shell32.SHGetPathFromIDListW.argtypes = [ctypes.c_void_p, wintypes.LPWSTR]
    shell32.SHGetPathFromIDListW.restype = wintypes.BOOL
    ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
    display = ctypes.create_unicode_buffer(260)
    info = _BROWSEINFO(
        hwnd, None, ctypes.cast(display, wintypes.LPWSTR),
        "选择输出目录", 0x41, None, 0, 0,
    )
    identifier = shell32.SHBrowseForFolderW(ctypes.byref(info))
    if not identifier:
        return ""
    try:
        path = ctypes.create_unicode_buffer(32768)
        return path.value if shell32.SHGetPathFromIDListW(identifier, path) else ""
    finally:
        ole32.CoTaskMemFree(identifier)


class UIBridge:
    def __init__(self, host):
        self.host = host
        self.engine = PrunerEngine(self._event)
        self.closed = False

    def bind(self):
        functions = {
            "pruner_start": self.engine.start,
            "pruner_pause": self.engine.pause,
            "pruner_resume": self.engine.resume,
            "pruner_abort": self.engine.abort,
            "pruner_reset": self.engine.reset,
            "pruner_get_state": self.get_state,
            "pruner_pick_file": self.pick_file,
            "pruner_pick_directory": lambda: pick_directory(self.host.hwnd),
            "pruner_inspect_entry": self.inspect_entry,
            "pruner_path_size": self.path_size,
            "pruner_export": self.export,
            "pruner_open_output": self.open_output,
            "pruner_defaults": self.defaults,
        }
        for name, function in functions.items():
            self.host.bridge.expose(function, name=name)

    def get_state(self):
        state = self.engine.snapshot()
        state["report"] = make_report(state) if state.get("final") else None
        return state

    def pick_file(self, kind):
        filters = {
            "py": [("Python 脚本", "*.py"), ("所有文件", "*.*")],
            "ico": [("图标", "*.ico"), ("所有文件", "*.*")],
            "all": [("所有文件", "*.*")],
        }.get(kind, [("所有文件", "*.*")])
        return open_file_dialog(self.host.hwnd, "选择文件", filters) or ""

    def inspect_entry(self, entry):
        if not entry:
            return {"plugins": [], "data_items": []}
        return {
            "plugins": detect_plugins(entry),
            "data_items": detect_web_assets(entry),
        }

    def path_size(self, path):
        if not path or not Path(path).exists():
            return {"exists": False, "size_bytes": 0}
        return {"exists": True, "size_bytes": directory_size(path)}

    def export(self, kind):
        state = self.engine.snapshot()
        if not state.get("config"):
            raise ValueError("没有可导出的配置")
        from .config import PrunerConfig
        config = PrunerConfig.from_dict(state["config"])
        extensions = {"bat": "*.bat", "py": "*.py", "json": "*.json"}
        if kind not in extensions:
            raise ValueError("不支持的导出格式")
        destination = save_file_dialog(
            self.host.hwnd, "导出报告", [("导出文件", extensions[kind])],
            initial_dir=config.output_dir, initial_file="final_command." + kind,
        )
        if not destination:
            return ""
        return export_file(config, kind, destination)

    def open_output(self):
        state = self.engine.snapshot()
        if state.get("config"):
            os.startfile(state["config"]["output_dir"])
        return ""

    def defaults(self):
        root = Path(__file__).resolve().parent.parent
        entry = root / "spore_trainer_web.py"
        icon = root / "spore.ico"
        return {
            "entry": str(entry) if entry.is_file() else "",
            "output_dir": str(root / "nuitka_output"),
            "icon": str(icon) if icon.is_file() else "",
            "signed_plugin": str(root / "signed_payload_plugin.py"),
            "jobs": os.cpu_count() or 4,
            "upx_available": bool(shutil.which("upx")),
        }

    def _event(self, event, payload):
        if self.closed or not self.host.view:
            return
        def push():
            if not self.closed and self.host.view:
                try:
                    call_js(self.host.view, event, payload)
                except (RuntimeError, ValueError):
                    pass
        try:
            self.host.view.dispatch(push)
        except RuntimeError:
            pass
