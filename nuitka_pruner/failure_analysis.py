import re


ACTIVELY_EXCLUDED = re.compile(r"\bModule '([^']+)' was actively excluded")
MISSING_MODULE = re.compile(r"\bNo module named '([^']+)'")
BLOCKED_BY_PRUNER = re.compile(r"\bblocked by pruner: ([A-Za-z_][A-Za-z0-9_.]*)")


def excluded_modules_from_failure(output, excluded):
    excluded = set(excluded)
    for line in reversed((output or "").splitlines()):
        line = line.strip()
        if not line.startswith(("ImportError:", "ModuleNotFoundError:")):
            continue
        match = (
            ACTIVELY_EXCLUDED.search(line) or MISSING_MODULE.search(line)
            or BLOCKED_BY_PRUNER.search(line)
        )
        if match:
            name = match.group(1).split(".", 1)[0]
            if name in excluded:
                return {name}
    return set()
