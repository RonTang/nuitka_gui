import ast
import os
from pathlib import Path


WEB_ASSET_SUFFIXES = {
    ".html", ".htm", ".js", ".mjs", ".css", ".json", ".svg",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".woff", ".woff2",
    ".ttf", ".otf", ".xlsx", ".xlsm", ".xls", ".xlsb", ".csv",
}
WEBVIEW_MODULES = {"pyminiwebview", "pyminiwebview_helpers", "pyminiwebview_win32"}
def project_python_files(entry):
    entry = Path(entry).resolve()
    root = entry.parent
    pending = [entry]
    seen = set()
    while pending:
        source = pending.pop(0)
        key = os.path.normcase(str(source))
        if key in seen:
            continue
        seen.add(key)
        yield source
        try:
            tree = ast.parse(source.read_text(encoding="utf-8-sig"))
        except (OSError, SyntaxError, UnicodeError):
            continue

        def queue_module(base, module):
            target = base.joinpath(*module.split(".")) if module else base
            candidates = [target.with_suffix(".py"), target / "__init__.py"]
            parents = list(target.parents)
            for parent in parents:
                if parent == root.parent:
                    break
                candidates.append(parent / "__init__.py")
            for path in candidates:
                try:
                    resolved = path.resolve(strict=True)
                except (OSError, RuntimeError):
                    continue
                if resolved.is_file() and resolved.suffix == ".py":
                    key = os.path.normcase(str(resolved))
                    if key not in seen:
                        pending.append(resolved)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    queue_module(root, alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    base = source.parent
                    for _ in range(node.level - 1):
                        base = base.parent
                else:
                    base = root
                queue_module(base, node.module or "")
                for alias in node.names:
                    module = ".".join(part for part in (node.module, alias.name) if part)
                    queue_module(base, module)


def path_from_expression(node, source, root, variables=None):
    if variables is None:
        variables = {}
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        value = node.value.strip()
        if not value or len(value) > 260 or "\n" in value:
            return None
        try:
            return Path(value)
        except (OSError, ValueError):
            return None
    if isinstance(node, ast.Name):
        if node.id == "__file__":
            return source
        return variables.get(node.id)
    if isinstance(node, ast.Attribute):
        if node.attr == "parent":
            parent = path_from_expression(node.value, source, root, variables)
            return parent.parent if parent is not None else None
        return None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left = path_from_expression(node.left, source, root, variables)
        right = path_from_expression(node.right, source, root, variables)
        if left is not None and right is not None and not right.is_absolute():
            return left / right
        return None
    if not isinstance(node, ast.Call):
        return None
    function = node.func
    if isinstance(function, ast.Name) and function.id == "Path":
        if not node.args:
            return Path(".")
        return path_from_expression(node.args[0], source, root, variables)
    if not isinstance(function, ast.Attribute):
        return None
    if function.attr == "cwd":
        return root
    if function.attr in ("resolve", "absolute"):
        return path_from_expression(function.value, source, root, variables)
    if function.attr == "dirname" and node.args:
        value = path_from_expression(node.args[0], source, root, variables)
        return value.parent if value is not None else None
    if function.attr in ("join", "joinpath"):
        parts = []
        if function.attr == "joinpath":
            base = path_from_expression(function.value, source, root, variables)
            if base is None:
                return None
            parts.append(base)
        for argument in node.args:
            value = path_from_expression(argument, source, root, variables)
            if value is None:
                return None
            parts.append(value)
        if not parts:
            return None
        result = parts[0]
        for part in parts[1:]:
            if part.is_absolute():
                return None
            result = result / part
        return result
    return None


def existing_asset(candidate, source, root):
    if candidate is None or candidate.suffix.lower() not in WEB_ASSET_SUFFIXES:
        return None
    paths = [candidate] if candidate.is_absolute() else [
        source.parent / candidate, root / candidate,
    ]
    for path in paths:
        try:
            resolved = path.resolve(strict=True)
        except (OSError, RuntimeError):
            continue
        if resolved.is_file():
            return resolved
    return None


def detect_web_assets(entry):
    entry = Path(entry).resolve()
    root = entry.parent
    uses_webview = False
    discovered = {}
    for source in project_python_files(entry):
        try:
            tree = ast.parse(source.read_text(encoding="utf-8-sig"))
        except (OSError, SyntaxError, UnicodeError):
            continue
        variables = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
                value = path_from_expression(node.value, source, root, variables)
                if value is not None:
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    for target in targets:
                        if isinstance(target, ast.Name):
                            variables[target.id] = value
            if isinstance(node, ast.Import):
                if any(alias.name.split(".", 1)[0] in WEBVIEW_MODULES for alias in node.names):
                    uses_webview = True
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".", 1)[0] in WEBVIEW_MODULES:
                    uses_webview = True
            resolved = existing_asset(
                path_from_expression(node, source, root, variables), source, root
            )
            if resolved is None:
                continue
            try:
                target = resolved.relative_to(root).as_posix()
            except ValueError:
                target = resolved.name
            key = os.path.normcase(str(resolved))
            discovered[key] = {
                "source": str(resolved), "target": target,
                "kind": "file", "auto": True,
            }
    if not uses_webview:
        return []
    return sorted(discovered.values(), key=lambda item: item["source"].lower())


def add_auto_assets(config):
    if not config.auto_data:
        return []
    detected = detect_web_assets(config.entry)
    known = {
        (os.path.normcase(str(Path(item.get("source", "")).resolve())), item.get("target", ""))
        for item in config.data_items
    }
    added = []
    for item in detected:
        key = (os.path.normcase(item["source"]), item["target"])
        if key not in known:
            config.data_items.append(item)
            known.add(key)
            added.append(item)
    return added
