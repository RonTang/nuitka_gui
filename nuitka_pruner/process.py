import os
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProcessResult:
    returncode: int
    duration_s: float
    output: str
    timed_out: bool = False
    aborted: bool = False


class ProcessRunner:
    def __init__(self, abort_event, log_callback):
        self.abort_event = abort_event
        self.log_callback = log_callback
        self._lock = threading.Lock()
        self._process = None

    def run(self, command, log_path, timeout_s, cwd=None, env=None,
            capture_limit=2_000_000):
        log_path = Path(log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        output = []
        output_size = 0
        output_lock = threading.Lock()
        started = time.monotonic()
        timed_out = False
        aborted = False
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
        self.log_callback("$ " + subprocess.list2cmdline([str(part) for part in command]))
        try:
            process = subprocess.Popen(
                [str(part) for part in command],
                cwd=str(cwd) if cwd else None,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=creationflags,
            )
        except OSError as error:
            self.log_callback(str(error))
            with log_path.open("a", encoding="utf-8") as stream:
                stream.write(str(error) + "\n")
            return ProcessResult(127, time.monotonic() - started, str(error))

        with self._lock:
            self._process = process

        def read_output():
            with log_path.open("w", encoding="utf-8") as stream:
                for line in process.stdout:
                    stream.write(line)
                    stream.flush()
                    self.log_callback(line)
                    nonlocal output_size
                    with output_lock:
                        if output_size < capture_limit:
                            output.append(line)
                            output_size += len(line)

        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()
        try:
            while process.poll() is None:
                if self.abort_event.is_set():
                    aborted = True
                    self._kill_tree(process)
                    break
                if time.monotonic() - started >= timeout_s:
                    timed_out = True
                    self.log_callback(f"进程超过 {timeout_s:.0f} 秒超时，正在终止进程树")
                    self._kill_tree(process)
                    break
                self.abort_event.wait(0.1)
            returncode = process.wait()
            reader.join(timeout=5)
        finally:
            with self._lock:
                if self._process is process:
                    self._process = None
        with output_lock:
            text = "".join(output)
        return ProcessResult(
            returncode, time.monotonic() - started, text, timed_out, aborted
        )

    def _kill_tree(self, process):
        if process.poll() is not None:
            return
        if os.name == "nt":
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=15,
                    check=False,
                )
            except subprocess.SubprocessError:
                pass
        try:
            process.kill()
        except OSError:
            pass
