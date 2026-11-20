import ast
import os
import xml.etree.ElementTree as ET
from pathlib import Path


CORE_MODULES = {
    "sys", "builtins", "os", "io", "importlib", "types", "abc", "enum",
    "struct", "zlib", "binascii", "_struct", "_io", "_abc", "_frozen_importlib",
    "_frozen_importlib_external", "encodings", "codecs", "nt", "ntpath",
    "posixpath", "pathlib", "stat", "time", "math", "errno", "re", "sre_compile",
    "sre_parse", "functools", "collections", "operator", "keyword", "heapq",
    "itertools", "reprlib", "copyreg", "typing", "dataclasses", "json", "threading",
    "subprocess", "signal", "locale", "warnings", "traceback", "linecache",
    "tokenize", "token", "ast", "dis", "inspect", "importlib_metadata",
    "xml", "pyexpat", "_elementtree",
}
GUI_MODULES = {
    "tkinter", "_tkinter", "PySide6", "shiboken6", "PyQt5", "PyQt6", "sip",
    "pyminiwebview", "pyminiwebview_helpers", "pyminiwebview_win32",
}
CODE_SUFFIXES = {".py", ".pyc", ".pyd", ".dll"}
PLUGIN_IMPORTS = {
    "PySide6": "pyside6",
    "PyQt5": "pyqt5",
    "PyQt6": "pyqt6",
    "tkinter": "tk-inter",
    "numpy": "numpy",
}


def directory_size(path):
    path = Path(path)
    if path.is_file():
        return path.stat().st_size
    total = 0
    for root, _, files in os.walk(path):
        for filename in files:
            try:
                total += (Path(root) / filename).stat().st_size
            except OSError:
                pass
    return total


def detect_plugins(entry):
    try:
        tree = ast.parse(Path(entry).read_text(encoding="utf-8-sig"))
    except (OSError, SyntaxError, UnicodeError):
        return []
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".", 1)[0])
    return sorted({PLUGIN_IMPORTS[name] for name in imports & PLUGIN_IMPORTS.keys()})


def own_module_names(entry):
    entry = Path(entry)
    names = {entry.stem, "__main__"}
    for item in entry.parent.iterdir():
        if item.name.startswith("."):
            continue
        if item.is_dir() and (item / "__init__.py").is_file():
            names.add(item.name)
        elif item.is_file() and item.suffix == ".py":
            names.add(item.stem)
    return names


def string_references(entry):
    references = set()
    for path in Path(entry).parent.glob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        except (OSError, SyntaxError, UnicodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                value = node.value.split(".", 1)[0]
                if value.isidentifier():
                    references.add(value)
    return references


def report_modules(report_path):
    if not report_path or not Path(report_path).is_file():
        return set()
    try:
        root = ET.parse(report_path).getroot()
    except (ET.ParseError, OSError):
        return set()
    names = set()
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "module":
            continue
        name = element.attrib.get("name", "").split(".", 1)[0]
        if name.isidentifier():
            names.add(name)
    return names


def enumerate_candidates(dist_dir, entry, extra_whitelist=(), report_path=None):
    dist_dir = Path(dist_dir)
    whitelist = CORE_MODULES | GUI_MODULES | set(extra_whitelist) | own_module_names(entry)
    strings = string_references(entry)
    candidates = {}
    large_data = []

    for item in dist_dir.iterdir():
        if item.name.startswith(".") or item.name.endswith(".dist"):
            continue
        size = directory_size(item)
        if item.is_dir():
            name = item.name
            files = [path for path in item.rglob("*") if path.is_file()]
            has_code = any(path.suffix.lower() in CODE_SUFFIXES for path in files)
            if not has_code:
                if size >= 1024 * 1024:
                    large_data.append({"name": name, "size_bytes": size})
                continue
            is_extension = any(path.suffix.lower() == ".pyd" for path in files)
        elif item.suffix.lower() in (".pyd", ".py", ".pyc"):
            name = item.stem
            files = [item]
            is_extension = item.suffix.lower() == ".pyd"
        else:
            continue
        if not name.isidentifier() or name in whitelist:
            continue
        candidates[name] = {
            "name": name,
            "size_bytes": size,
            "is_c_extension": is_extension,
            "sample_files": [str(path.relative_to(dist_dir)) for path in files[:5]],
            "source": "dist",
            "has_data_files": any(
                path.suffix.lower() not in CODE_SUFFIXES for path in files
            ),
        }

    for name in report_modules(report_path) - whitelist:
        if name.isidentifier():
            candidates.setdefault(name, {
                "name": name,
                "size_bytes": 0,
                "is_c_extension": False,
                "sample_files": [],
                "source": "nuitka-report",
                "has_data_files": False,
            })

    for candidate in candidates.values():
        reasons = []
        if candidate["has_data_files"]:
            reasons.append("包含数据文件")
        if candidate["name"] in strings:
            reasons.append("被字符串引用，可能动态导入")
        candidate["risk_reasons"] = reasons
        candidate["uncertain"] = bool(reasons)
        candidate["validation_layer"] = "compiled" if reasons else "source"
    return sorted(candidates.values(), key=lambda item: item["name"]), large_data
