import argparse
import ctypes
import os
import subprocess
import sys
import threading
import time
from ctypes import wintypes


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260),
    ]


def process_descendants(root_pid):
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32FirstW.restype = wintypes.BOOL
    kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32NextW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
    if snapshot == wintypes.HANDLE(-1).value:
        return {root_pid}
    parents = {}
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(entry)
    try:
        found = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while found:
            parents[entry.th32ProcessID] = entry.th32ParentProcessID
            found = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)
    result = {root_pid}
    changed = True
    while changed:
        changed = False
        for pid, parent in parents.items():
            if parent in result and pid not in result:
                result.add(pid)
                changed = True
    return result


def visible_windows(root_pid):
    if os.name != "nt":
        return []
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    windows = []
    process_ids = process_descendants(root_pid)

    def callback(hwnd, _):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in process_ids and user32.IsWindowVisible(hwnd):
            windows.append(hwnd)
        return True

    user32.EnumWindows(callback_type(callback), 0)
    return windows


def close_windows(windows):
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.PostMessageW.argtypes = [
        wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
    ]
    for hwnd in windows:
        user32.PostMessageW(hwnd, 0x0010, 0, 0)


def terminate_tree(process):
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=15, check=False,
        )
    else:
        process.terminate()


def run(command, assertion, timeout):
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
    process = subprocess.Popen(
        command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
        bufsize=1, creationflags=creationflags,
    )
    assertion_seen = False
    error_seen = False

    def forward_output():
        nonlocal assertion_seen, error_seen
        for line in process.stdout:
            if assertion in line:
                assertion_seen = True
            if (
                "Traceback (most recent call last):" in line
                or line.startswith("Bridge call ")
                or line.startswith("Exception in thread ")
            ):
                error_seen = True
            data = line.encode("utf-8", errors="replace")
            if hasattr(sys.stdout, "buffer"):
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()
            else:
                sys.stdout.write(data.decode("utf-8"))
                sys.stdout.flush()

    reader = threading.Thread(target=forward_output, daemon=True)
    reader.start()
    started = time.monotonic()
    close_sent = False
    try:
        while process.poll() is None:
            elapsed = time.monotonic() - started
            if elapsed >= timeout:
                print("AUTO_SMOKE_TIMEOUT", flush=True)
                terminate_tree(process)
                return 1
            if not close_sent and elapsed >= 0.5:
                windows = visible_windows(process.pid)
                if windows:
                    time.sleep(min(0.5, max(0, timeout - elapsed)))
                    close_sent = True
                    print("AUTO_SMOKE_WINDOW_READY", flush=True)
                    close_windows(visible_windows(process.pid))
            time.sleep(0.1)
        returncode = process.wait()
        reader.join(timeout=3)
        if returncode == 0:
            if error_seen:
                print("AUTO_SMOKE_RUNTIME_ERROR", flush=True)
                return 1
            if not assertion_seen:
                print(assertion, flush=True)
            return 0
        return returncode or 1
    finally:
        if process.poll() is None:
            terminate_tree(process)
        reader.join(timeout=1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--assertion", default="SMOKE_OK")
    parser.add_argument("--timeout", type=float, default=45)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("missing target command")
    try:
        return run(command, args.assertion, args.timeout)
    except OSError as error:
        print(error, file=sys.stderr)
        return 127


if __name__ == "__main__":
    raise SystemExit(main())
