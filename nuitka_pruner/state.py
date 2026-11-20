import copy
import json
import os
import threading
from contextlib import contextmanager
from pathlib import Path


def new_state():
    return {
        "phase": "idle",
        "status": "idle",
        "config": None,
        "fingerprint": "",
        "candidates": [],
        "required": [],
        "prefilter_required": [],
        "excluded": [],
        "unknown": [],
        "prefilter_pending": [],
        "deep_review_pending": [],
        "deep_review_rounds": 0,
        "deep_review_initialized": False,
        "ddmin_progress": {"n": 0, "size": 0},
        "history": [],
        "baseline": {},
        "final": {},
        "current_set": [],
        "logs": [],
        "error": "",
        "started_at": None,
        "elapsed_s": 0,
        "pruned_standalone_size": 0,
    }


class StateStore:
    def __init__(self, path=None):
        self.path = Path(path) if path else None
        self.lock = threading.RLock()
        self.data = new_state()

    def load(self, path=None):
        with self.lock:
            if path:
                self.path = Path(path)
            if not self.path or not self.path.is_file():
                return False
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                raise ValueError("状态文件格式无效")
            state = new_state()
            state.update(loaded)
            if state["status"] in ("running", "paused"):
                state["status"] = "interrupted"
            self.data = state
            return True

    def save(self):
        with self.lock:
            self._save_locked()

    def _save_locked(self):
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(self.data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, self.path)

    @contextmanager
    def transaction(self):
        with self.lock:
            yield self.data
            self._save_locked()

    def snapshot(self):
        with self.lock:
            return copy.deepcopy(self.data)

    def log(self, line, persist=False):
        line = str(line).rstrip("\r\n")
        if not line:
            return
        with self.lock:
            self.data["logs"].append(line)
            if len(self.data["logs"]) > 1200:
                del self.data["logs"][:-1200]
            if persist:
                self._save_locked()

    def record(self, entry):
        with self.lock:
            self.data["history"].append(entry)
            self._save_locked()

    def reset(self, path=None):
        with self.lock:
            self.path = Path(path) if path else self.path
            self.data = new_state()
            self._save_locked()
