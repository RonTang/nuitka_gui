import json
import pprint
import shutil
import subprocess
from pathlib import Path

from .build import nuitka_command


def final_command(config, excluded):
    return nuitka_command(config, excluded, final=True)


def command_text(command):
    return subprocess.list2cmdline([str(part) for part in command])


def make_report(state):
    config = state.get("config") or {}
    baseline = state["baseline"].get("size_bytes", 0)
    final = state["final"].get("size_bytes", 0)
    saved = baseline - final
    candidates = {item["name"]: item for item in state["candidates"]}
    warnings = []
    for name in state["excluded"]:
        candidate = candidates.get(name, {})
        if "被字符串引用，可能动态导入" in candidate.get("risk_reasons", []):
            warnings.append(f"{name}: 被字符串引用，请确认冒烟测试覆盖动态导入路径")
    return {
        "verification_mode": "full-ddmin" if config.get("full_ddmin") else "fast-layered",
        "smoke_mode": "automatic" if config.get("auto_smoke", True) else "strict-custom",
        "required": state["required"],
        "excluded": state["excluded"],
        "baseline_size_bytes": baseline,
        "pruned_standalone_size_bytes": state.get("pruned_standalone_size", 0),
        "final_size_bytes": final,
        "saved_bytes": saved,
        "saved_percent": (saved / baseline * 100) if baseline else 0,
        "elapsed_s": state.get("elapsed_s", 0),
        "history": state["history"],
        "large_data": state["baseline"].get("large_data", []),
        "warnings": warnings,
        "final_command": state["final"].get("command", []),
    }


def write_reports(config, state):
    output = Path(config.output_dir)
    report = make_report(state)
    command = final_command(config, state["excluded"])
    report["final_command"] = command
    report_path = output / "pruner_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    bat_path = output / "final_command.bat"
    bat_path.write_text(
        "@echo off\n" + command_text(command) + "\n", encoding="utf-8-sig"
    )
    arguments = command[3:]
    py_path = output / "final_command.py"
    py_path.write_text(
        "import subprocess\nimport sys\n\nNUITKA_ARGS = "
        + pprint.pformat(arguments, width=100, sort_dicts=False)
        + "\n\nif __name__ == '__main__':\n"
          "    raise SystemExit(subprocess.call([sys.executable, '-m', 'nuitka', *NUITKA_ARGS]))\n",
        encoding="utf-8",
    )
    return report, [report_path, bat_path, py_path]


def export_file(config, kind, destination):
    source = Path(config.output_dir) / {
        "bat": "final_command.bat",
        "py": "final_command.py",
        "json": "pruner_report.json",
    }[kind]
    if not source.is_file():
        raise ValueError("报告尚未生成")
    shutil.copyfile(source, destination)
    return str(destination)
