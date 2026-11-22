import os
import shlex
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .candidates import directory_size
from .process import ProcessRunner


@dataclass
class BuildResult:
    ok: bool
    build_returncode: int
    smoke_returncode: Optional[int]
    build_s: float
    smoke_s: float
    size_bytes: int
    output_dir: str
    executable: str
    log_path: str
    output_tail: str = ""


def split_extra_args(value):
    return shlex.split(value or "", posix=True)


def nuitka_command(config, excluded, final=False, output_dir=None, report_path=None):
    output_dir = Path(output_dir or (Path(config.output_dir) / "final_dist"))
    command = [
        sys.executable, "-m", "nuitka", "--standalone",
        f"--jobs={config.jobs}", "--remove-output", "--assume-yes-for-downloads",
        f"--output-dir={output_dir}",
    ]
    if final and config.mode == "onefile":
        command.append("--onefile")
        if config.custom_onefile:
            command.append(f"--user-plugin={config.signed_plugin}")
            command.append(f"--onefile-bootstrap-name={config.onefile_bootstrap_name}")
    for name in sorted(set(excluded)):
        command.append(f"--nofollow-import-to={name}")
    if report_path:
        command.append(f"--report={report_path}")
    for plugin in config.plugins:
        command.append(f"--enable-plugin={plugin}")
    command.append(f"--windows-console-mode={config.console}")
    metadata = {
        "product-name": config.product_name,
        "product-version": config.product_version,
        "company-name": config.company_name,
    }
    for name, value in metadata.items():
        if value:
            command.append(f"--{name}={value}")
    for item in config.data_items:
        source, target = item.get("source", ""), item.get("target", "")
        if not source or not target:
            continue
        option = "include-data-dir" if item.get("kind") == "dir" else "include-data-files"
        command.append(f"--{option}={source}={target}")
    if final:
        if config.icon:
            command.append(f"--windows-icon-from-ico={config.icon}")
        if config.lto:
            command.append("--lto=yes")
        flags = []
        if config.no_asserts:
            flags.append("no_asserts")
        if config.no_docstrings:
            flags.append("no_docstrings")
        if flags:
            command.append("--python-flag=" + ",".join(flags))
        if config.upx:
            if not shutil.which("upx"):
                raise ValueError("已启用 UPX，但 PATH 中找不到 upx")
            command.append("--enable-upx")
    command.extend(filtered_extra_args(config.extra_args, final))
    command.append(config.entry)
    return command


def filtered_extra_args(value, final):
    arguments = split_extra_args(value)
    result = []
    skip_next = False
    pair_options = {"--output-dir", "--jobs", "--output-filename"}
    final_prefixes = ("--lto", "--python-flag", "--windows-icon-from-ico")
    for argument in arguments:
        if skip_next:
            skip_next = False
            continue
        name = argument.split("=", 1)[0]
        if name in pair_options and "=" not in argument:
            skip_next = True
            continue
        if name in pair_options or argument in (
                "--onefile", "--standalone", "--remove-output", "--clean-cache"):
            continue
        if not final and (
                argument == "--enable-upx" or name.startswith(final_prefixes)):
            continue
        result.append(argument)
    return result


def smoke_invocation(config, executable=None, blocked=None):
    arguments = shlex.split(config.smoke_command, posix=True)
    if not arguments:
        raise ValueError("冒烟测试命令不能为空")
    source = blocked is not None
    rendered = []
    found_executable = False
    for argument in arguments:
        if "{entry}" in argument:
            if source:
                continue
            argument = argument.replace("{entry}", config.entry)
        if "{executable}" in argument or "{python}" in argument:
            found_executable = True
            replacement = sys.executable if source or "{python}" in argument else str(executable)
            argument = argument.replace("{executable}", replacement).replace("{python}", sys.executable)
        argument = argument.replace("{output_dir}", config.output_dir)
        rendered.append(argument)
    if not found_executable:
        raise ValueError("冒烟命令必须包含 {executable} 或 {python} 占位符")
    env = os.environ.copy()
    if source:
        rendered[1:1] = [
            "-X", "frozen_modules=off", "-c",
            "from nuitka_pruner.prefilter import bootstrap; bootstrap()",
        ]
        env["PRUNER_BLOCKED"] = __import__("json").dumps(sorted(blocked))
        env["PRUNER_ENTRY"] = config.entry
        package_root = str(Path(__file__).resolve().parent.parent)
        env["PYTHONPATH"] = package_root + os.pathsep + env.get("PYTHONPATH", "")
    if config.auto_smoke:
        package_root = str(Path(__file__).resolve().parent.parent)
        env["PYTHONPATH"] = package_root + os.pathsep + env.get("PYTHONPATH", "")
        rendered = [
            sys.executable, "-m", "nuitka_pruner.smoke_runner",
            "--assertion", config.assertion, "--", *rendered,
        ]
    return rendered, env


class Builder:
    def __init__(self, config, abort_event, log_callback):
        self.config = config
        self.abort_event = abort_event
        self.log_callback = log_callback
        self.runner = ProcessRunner(abort_event, log_callback)
        self.round = 0

    def build_and_smoke(self, excluded, label, baseline=False, final=False):
        self._check_disk()
        self.round += 1
        if final:
            output_dir = Path(self.config.output_dir) / "final_dist"
        elif baseline:
            output_dir = self.config.work_dir / "baseline"
        else:
            output_dir = self.config.work_dir / "builds" / f"round_{self.round:04d}"
        report_path = self.config.work_dir / "baseline-report.xml" if baseline else None
        log_path = Path(self.config.output_dir) / "logs" / f"{label}.log"
        command = nuitka_command(
            self.config, excluded, final=final, output_dir=output_dir,
            report_path=report_path,
        )
        build = self.runner.run(
            command, log_path, self.config.timeout_minutes * 60,
            cwd=Path(self.config.entry).parent,
        )
        executable = self._executable(output_dir, final)
        size = directory_size(executable if final and self.config.mode == "onefile" else output_dir)
        smoke_returncode = None
        smoke_s = 0.0
        tail = build.output[-4000:]
        ok = build.returncode == 0 and not build.timed_out and not build.aborted
        if ok:
            if not executable.is_file():
                self.log_callback(f"找不到预期产物: {executable}")
                return BuildResult(False, 0, None, build.duration_s, 0, size,
                                   str(output_dir), str(executable), str(log_path))
            smoke_command, env = smoke_invocation(self.config, executable)
            smoke_log = log_path.with_name(label + "_smoke.log")
            smoke = self.runner.run(
                smoke_command, smoke_log, min(self.config.timeout_minutes * 60, 180),
                cwd=executable.parent, env=env,
            )
            smoke_returncode = smoke.returncode
            smoke_s = smoke.duration_s
            tail = smoke.output[-4000:]
            # try/except 静默降级不等于真实功能通过；断言和退出码必须同时满足。
            ok = (
                smoke.returncode == 0 and not smoke.timed_out and not smoke.aborted
                and self.config.assertion in smoke.output
            )
            if not ok:
                self.log_callback("冒烟失败：要求退出码为 0 且输出包含断言串")
        result = BuildResult(
            ok, build.returncode, smoke_returncode, build.duration_s, smoke_s,
            size, str(output_dir), str(executable), str(log_path), tail,
        )
        if not baseline and not final:
            shutil.rmtree(output_dir, ignore_errors=True)
        return result

    def source_smoke(self, blocked, label):
        log_path = Path(self.config.output_dir) / "logs" / f"{label}.log"
        command, env = smoke_invocation(self.config, blocked=blocked)
        result = self.runner.run(
            command, log_path, min(self.config.timeout_minutes * 60, 180),
            cwd=Path(self.config.entry).parent, env=env,
        )
        ok = (
            result.returncode == 0 and not result.timed_out and not result.aborted
            and self.config.assertion in result.output
        )
        return result, ok

    def cleanup_baseline(self):
        shutil.rmtree(self.config.work_dir / "baseline", ignore_errors=True)

    def _executable(self, output_dir, final):
        stem = Path(self.config.entry).stem + ".exe"
        if final and self.config.mode == "onefile":
            return output_dir / stem
        return output_dir / (Path(self.config.entry).stem + ".dist") / stem

    def _check_disk(self):
        output = Path(self.config.output_dir)
        output.mkdir(parents=True, exist_ok=True)
        free = shutil.disk_usage(output).free
        if free < 5 * 1024 ** 3:
            raise RuntimeError("磁盘可用空间不足 5GB，无法开始 Nuitka 构建")
