import json
import os
import runpy
import sys


class ImportBlocker:
    def __init__(self, blocked):
        self.blocked = frozenset(blocked)

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".", 1)[0] in self.blocked:
            raise ImportError(f"blocked by pruner: {fullname}")
        return None


def install(blocked):
    blocker = ImportBlocker(blocked)
    sys.meta_path.insert(0, blocker)
    return blocker


def bootstrap():
    blocked = json.loads(os.environ.get("PRUNER_BLOCKED", "[]"))
    entry = os.environ["PRUNER_ENTRY"]
    sys.argv = [entry, *sys.argv[1:]]
    for name in tuple(sys.modules):
        if name.split(".", 1)[0] in blocked:
            sys.modules.pop(name, None)
    install(blocked)
    runpy.run_path(entry, run_name="__main__")
