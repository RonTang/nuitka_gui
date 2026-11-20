import argparse
import os
import sys
import time

from .orchestrator import PrunerEngine


def parser():
    result = argparse.ArgumentParser(description="Nuitka 自动精简打包器")
    result.add_argument("entry", help="Python 入口脚本")
    result.add_argument("output_dir", help="输出目录")
    result.add_argument("--mode", choices=("onefile", "standalone"), default="onefile")
    result.add_argument("--console", choices=("disable", "attach", "force"), default="disable")
    result.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    result.add_argument("--timeout", type=int, default=20, help="单轮超时（分钟）")
    result.add_argument("--smoke-command", default='"{executable}"')
    result.add_argument("--no-auto-smoke", action="store_true")
    result.add_argument("--assertion", default="SMOKE_OK")
    result.add_argument("--plugin", action="append", default=[])
    result.add_argument("--whitelist", action="append", default=[])
    result.add_argument("--icon", default="")
    result.add_argument("--extra-args", default="")
    result.add_argument("--deep-review", action="store_true")
    result.add_argument("--deep-review-attempts", type=int, default=5)
    result.add_argument("--custom-onefile", action="store_true")
    result.add_argument("--signed-plugin", default="")
    result.add_argument("--no-lto", action="store_true")
    return result


def main():
    args = parser().parse_args()
    config = {
        "entry": args.entry,
        "output_dir": args.output_dir,
        "mode": args.mode,
        "console": args.console,
        "jobs": args.jobs,
        "timeout_minutes": args.timeout,
        "smoke_command": args.smoke_command,
        "auto_smoke": not args.no_auto_smoke,
        "assertion": args.assertion,
        "plugins": args.plugin,
        "whitelist": args.whitelist,
        "icon": args.icon,
        "extra_args": args.extra_args,
        "deep_review": args.deep_review,
        "deep_review_attempts": args.deep_review_attempts,
        "custom_onefile": args.custom_onefile,
        "signed_plugin": args.signed_plugin,
        "lto": not args.no_lto,
    }
    engine = PrunerEngine(lambda event, payload: print(payload, flush=True) if event == "onLog" else None)
    try:
        engine.start(config)
        while engine.snapshot()["running"]:
            time.sleep(0.25)
    except KeyboardInterrupt:
        engine.abort()
        engine.shutdown()
        return 130
    state = engine.snapshot()
    if state["status"] != "done":
        print(state.get("error") or "任务未完成", file=sys.stderr)
        return 1
    print(f"最终产物: {state['final']['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
