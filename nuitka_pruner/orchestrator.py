import json
import threading
import time
import traceback
from pathlib import Path

from .build import BuildResult, Builder
from .candidates import enumerate_candidates
from .config import PrunerConfig
from .ddmin import ddmin
from .failure_analysis import excluded_modules_from_failure
from .report import final_command, write_reports
from .state import StateStore
from .web_assets import add_auto_assets


class RunAborted(Exception):
    pass


class PrunerEngine:
    def __init__(self, listener=None):
        self.listener = listener or (lambda event, payload: None)
        self.store = StateStore()
        self.abort_event = threading.Event()
        self.pause_event = threading.Event()
        self._lock = threading.RLock()
        self._worker = None
        self._reset_requested = False

    def snapshot(self):
        state = self.store.snapshot()
        with self._lock:
            state["running"] = bool(self._worker and self._worker.is_alive())
            state["paused"] = self.pause_event.is_set()
        return state

    def start(self, config=None):
        with self._lock:
            if self._worker and self._worker.is_alive():
                if self.pause_event.is_set():
                    self.pause_event.clear()
                    self.store.log("继续运行", persist=True)
                    return self.snapshot()
                raise RuntimeError("精简任务已在运行")
            if config is None:
                if not self.store.data.get("config"):
                    raise ValueError("没有可续跑的配置")
                normalized = PrunerConfig.from_dict(self.store.data["config"]).normalized()
            else:
                normalized = PrunerConfig.from_dict(config).normalized()
                loaded = StateStore(normalized.state_path)
                loaded.load()
                self.store = loaded
            added_assets = add_auto_assets(normalized)
            resume = (
                self.store.data.get("fingerprint") == normalized.fingerprint()
                and self.store.data.get("phase") not in ("idle", "done")
            )
            if not resume:
                self.store.reset(normalized.state_path)
                with self.store.transaction() as state:
                    state.update({
                        "phase": "baseline",
                        "status": "running",
                        "config": normalized.to_dict(),
                        "fingerprint": normalized.fingerprint(),
                        "started_at": time.time(),
                    })
            else:
                self.store.path = normalized.state_path
                with self.store.transaction() as state:
                    state["status"] = "running"
                    state["error"] = ""
                self.store.log("从上次状态续跑；已完成的相同测试将直接复用", persist=True)
            if added_assets:
                self.store.log(
                    "pyminiwebview 自动包含资源："
                    + ", ".join(item["target"] for item in added_assets),
                    persist=True,
                )
            self.abort_event.clear()
            self.pause_event.clear()
            self._reset_requested = False
            self._worker = threading.Thread(
                target=self._worker_main, name="nuitka-pruner", daemon=True
            )
            self._worker.start()
        return self.snapshot()

    def pause(self):
        if not self._worker or not self._worker.is_alive():
            raise RuntimeError("当前没有运行中的任务")
        self.pause_event.set()
        with self.store.transaction() as state:
            state["status"] = "paused"
        self.store.log("将在当前构建或冒烟测试结束后暂停", persist=True)
        return self.snapshot()

    def resume(self):
        if self._worker and self._worker.is_alive():
            self.pause_event.clear()
            with self.store.transaction() as state:
                state["status"] = "running"
            self.store.log("继续运行", persist=True)
            return self.snapshot()
        return self.start()

    def abort(self):
        self.abort_event.set()
        self.pause_event.clear()
        self.store.log("正在中止进程树……", persist=True)
        return self.snapshot()

    def reset(self):
        if self._worker and self._worker.is_alive():
            self._reset_requested = True
            self.abort_event.set()
            self.pause_event.clear()
        else:
            self.store.reset()
        return self.snapshot()

    def shutdown(self):
        self.abort_event.set()
        self.pause_event.clear()
        worker = self._worker
        if worker and worker.is_alive():
            worker.join(timeout=3)

    def _worker_main(self):
        try:
            self._run()
        except RunAborted:
            if self._reset_requested:
                self.store.reset()
            else:
                with self.store.transaction() as state:
                    state["status"] = "aborted"
                    state["current_set"] = []
                self.store.log("任务已中止，可从状态续跑", persist=True)
        except Exception as error:
            if self._reset_requested:
                self.store.reset()
            else:
                with self.store.transaction() as state:
                    state["status"] = "error"
                    state["error"] = str(error)
                    state["current_set"] = []
                self.store.log(f"错误: {error}", persist=True)
                self.store.log(traceback.format_exc())
        finally:
            self.abort_event.clear()
            self.pause_event.clear()
            self._reset_requested = False

    def _run(self):
        config = PrunerConfig.from_dict(self.store.data["config"]).normalized()
        builder = Builder(config, self.abort_event, self._log)
        self._ensure_baseline(config, builder)
        if not config.full_ddmin:
            self._run_prefilter(config, builder)
        self._run_compiled(config, builder)
        self._run_deep_review(config, builder)
        self._run_final(config, builder)

    def _ensure_baseline(self, config, builder):
        baseline = self.store.data["baseline"]
        if not baseline.get("smoke_ok"):
            self._phase("baseline")
            self._log("[基线] 构建 standalone；基线不通过时不会进入精简循环")
            result = builder.build_and_smoke([], "baseline", baseline=True)
            self._check_abort()
            self._record("baseline", [], result)
            if not result.ok:
                raise RuntimeError("基线构建或冒烟测试失败；请修复后再精简")
            with self.store.transaction() as state:
                state["baseline"] = {
                    "size_bytes": result.size_bytes,
                    "size_mb": result.size_bytes / 1024 ** 2,
                    "smoke_ok": True,
                    "dist_dir": str(Path(result.output_dir) / (Path(config.entry).stem + ".dist")),
                    "report_path": str(config.work_dir / "baseline-report.xml"),
                    "enumerated": False,
                }
        if not self.store.data["baseline"].get("enumerated"):
            self._phase("baseline")
            baseline = self.store.data["baseline"]
            candidates, large_data = enumerate_candidates(
                baseline["dist_dir"], config.entry, config.whitelist,
                baseline.get("report_path"),
            )
            pending = [item["name"] for item in candidates if not item["uncertain"]]
            unknown = [item["name"] for item in candidates if item["uncertain"]]
            (Path(config.output_dir) / "candidates.json").write_text(
                json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            with self.store.transaction() as state:
                state["candidates"] = candidates
                state["prefilter_pending"] = pending
                state["unknown"] = unknown
                state["baseline"]["large_data"] = large_data
                state["baseline"]["enumerated"] = True
            self._log(
                f"候选 {len(candidates)} 个：源码预筛 {len(pending)} 个，编译存疑 {len(unknown)} 个"
            )

    def _run_prefilter(self, config, builder):
        self._phase("prefilter")
        if (
            len(self.store.data["prefilter_pending"]) > 1
            and not any(
                entry.get("kind") == "prefilter"
                for entry in self.store.data["history"]
            )
        ):
            self._run_combined_prefilter(config, builder)
        while self.store.data["prefilter_pending"]:
            self._checkpoint()
            name = self.store.data["prefilter_pending"][0]
            blocked = sorted(set(self.store.data["excluded"]) | {name})
            with self.store.transaction() as state:
                state["current_set"] = blocked
            self._log(f"[预筛] 排除 {name}")
            process, ok = builder.source_smoke(blocked, "prefilter_" + name)
            self._check_abort()
            entry = {
                "kind": "prefilter", "set": blocked, "ok": ok,
                "build_s": 0, "test_s": process.duration_s,
                "returncode": process.returncode, "size_bytes": 0,
                "size_mb": 0, "log": str(Path(config.output_dir) / "logs" / f"prefilter_{name}.log"),
            }
            self._record_entry(entry)
            with self.store.transaction() as state:
                target = "excluded" if ok else "required"
                state[target] = sorted(set(state[target]) | {name})
                if not ok:
                    state["prefilter_required"] = sorted(
                        set(state["prefilter_required"]) | {name}
                    )
                state["prefilter_pending"].pop(0)
                state["current_set"] = []

    def _run_combined_prefilter(self, config, builder):
        while len(self.store.data["prefilter_pending"]) > 1:
            self._checkpoint()
            blocked = sorted(self.store.data["prefilter_pending"])
            with self.store.transaction() as state:
                state["current_set"] = blocked
            label = f"prefilter_combined_{len(self.store.data['history']):03d}"
            self._log(f"[预筛] 整组测试 {len(blocked)} 个候选")
            process, ok = builder.source_smoke(blocked, label)
            self._check_abort()
            self._record_entry({
                "kind": "prefilter", "set": blocked, "ok": ok,
                "build_s": 0, "test_s": process.duration_s,
                "returncode": process.returncode, "size_bytes": 0, "size_mb": 0,
                "log": str(Path(config.output_dir) / "logs" / f"{label}.log"),
            })
            if ok:
                with self.store.transaction() as state:
                    state["excluded"] = sorted(set(state["excluded"]) | set(blocked))
                    state["prefilter_pending"] = []
                    state["current_set"] = []
                self._log("整组源码预筛通过，无需逐个测试")
                return
            missing = excluded_modules_from_failure(process.output, blocked)
            if not missing:
                self._log("整组预筛无法从异常定位，回退到逐个源码测试")
                return
            with self.store.transaction() as state:
                state["required"] = sorted(set(state["required"]) | missing)
                state["prefilter_required"] = sorted(
                    set(state["prefilter_required"]) | missing
                )
                state["prefilter_pending"] = [
                    name for name in state["prefilter_pending"] if name not in missing
                ]
                state["current_set"] = []
            self._log("[预筛快速定位] 必须保留：" + ", ".join(sorted(missing)))

    def _run_compiled(self, config, builder):
        self._phase("ddmin")
        if config.full_ddmin:
            self._run_full_ddmin(config, builder)
            return
        possible = sorted(set(self.store.data["excluded"]) | set(self.store.data["unknown"]))
        if not possible:
            with self.store.transaction() as state:
                state["unknown"] = []
            return
        combined = self._compiled_test(config, builder, possible)
        if combined.ok:
            with self.store.transaction() as state:
                state["excluded"] = possible
                state["unknown"] = []
                state["pruned_standalone_size"] = combined.size_bytes
            self._log("整组排除已通过真实构建与冒烟测试，无需继续细分")
            return

        feedback_required = set()
        working = set(possible)
        failure = combined
        while not failure.ok:
            missing = excluded_modules_from_failure(failure.output_tail, working)
            if not missing:
                break
            feedback_required |= missing
            working -= missing
            self._log(
                "[快速定位] 冒烟异常明确指出必须保留：" + ", ".join(sorted(missing))
            )
            failure = self._compiled_test(config, builder, sorted(working))
        if failure.ok:
            with self.store.transaction() as state:
                state["required"] = sorted(set(state["required"]) | feedback_required)
                state["excluded"] = sorted(working)
                state["unknown"] = []
                state["pruned_standalone_size"] = failure.size_bytes
            self._log("根据冒烟异常定位必需模块后，整组验证已通过")
            return

        safe = sorted(set(self.store.data["excluded"]) - feedback_required)
        uncertain = sorted(set(self.store.data["unknown"]) - feedback_required)
        self._log("异常日志无法继续定位；先复用预筛结果，再只对失败层运行 ddmin")
        base = []
        newly_required = set(feedback_required)
        if safe:
            if uncertain and self._compiled_test(config, builder, safe).ok:
                base = safe
                self._log("源码预筛集合已通过独立编译验证，不再参与后续细分")
            else:
                base, keep = self._minimize_layer(config, builder, safe, [])
                newly_required |= keep
        if uncertain:
            candidate_exclusions = sorted(set(base) | set(uncertain))
            initial = self._compiled_test(config, builder, candidate_exclusions)
            if initial.ok:
                excluded = candidate_exclusions
            else:
                safe_uncertain, keep = self._minimize_layer(
                    config, builder, uncertain, base
                )
                excluded = safe_uncertain
                newly_required |= keep
        else:
            excluded = base
        self._check_abort()
        with self.store.transaction() as state:
            state["required"] = sorted(set(state["required"]) | newly_required)
            state["excluded"] = sorted(set(excluded))
            state["unknown"] = []
            state["current_set"] = []

    def _ddmin_progress(self, n, size):
        self._log(f"[ddmin] 粒度 {n}/{size}")
        with self.store.transaction() as state:
            state["ddmin_progress"] = {"n": n, "size": size}

    def _run_full_ddmin(self, config, builder):
        with self.store.transaction() as state:
            state["prefilter_pending"] = []
            state["unknown"] = []
            state["ddmin_progress"] = {"n": 0, "size": 0}
        possible = sorted(item["name"] for item in self.store.data["candidates"])
        if not possible:
            return
        self._log("[完整 ddmin] 复核全部候选，不使用预筛约束、日志剪枝或分层")
        combined = self._compiled_test(config, builder, possible)
        if combined.ok:
            with self.store.transaction() as state:
                state["required"] = []
                state["excluded"] = possible
                state["unknown"] = []
                state["pruned_standalone_size"] = combined.size_bytes
            return
        def test_keep(keep):
            self._checkpoint()
            excluded = sorted(set(possible) - set(keep))
            return self._compiled_test(config, builder, excluded).ok

        keep = ddmin(possible, test_keep, on_progress=self._ddmin_progress)
        self._check_abort()
        with self.store.transaction() as state:
            state["required"] = sorted(keep)
            state["prefilter_required"] = []
            state["excluded"] = sorted(set(possible) - keep)
            state["unknown"] = []
            state["current_set"] = []

    def _minimize_layer(self, config, builder, layer, base):
        layer = set(layer)
        base = set(base)
        with self.store.transaction() as state:
            state["ddmin_progress"] = {"n": 0, "size": 0}
        self._log(f"仅细分当前层的 {len(layer)} 个候选，固定保留其他已验证集合")
        def test_keep(keep):
            self._checkpoint()
            excluded = sorted(base | (layer - set(keep)))
            return self._compiled_test(config, builder, excluded).ok

        keep = ddmin(layer, test_keep, on_progress=self._ddmin_progress)
        return sorted(base | (layer - keep)), keep

    def _compiled_test(self, config, builder, excluded, kind="ddmin"):
        excluded = sorted(set(excluded))
        cached = self._cached_build(excluded)
        if cached is not None:
            self._log(f"[编译] 复用已完成的测试：{', '.join(excluded) or '（无排除）'}")
            return cached
        with self.store.transaction() as state:
            state["current_set"] = excluded
        label = f"{kind}_{len(self.store.data['history']) + 1:04d}"
        self._log(f"[编译] 本轮排除：{', '.join(excluded) or '（无）'}")
        result = builder.build_and_smoke(excluded, label)
        self._check_abort()
        self._record(kind, excluded, result)
        if result.ok:
            with self.store.transaction() as state:
                state["pruned_standalone_size"] = result.size_bytes
        with self.store.transaction() as state:
            state["current_set"] = []
        return result

    def _cached_build(self, excluded):
        if not excluded:
            baseline = self.store.data["baseline"]
            if baseline.get("smoke_ok"):
                return BuildResult(
                    True, 0, 0, 0, 0, baseline["size_bytes"], "",
                    "", "", "",
                )
        for entry in reversed(self.store.data["history"]):
            if entry.get("kind") in ("ddmin", "deep_review") and entry.get("set") == excluded:
                return BuildResult(
                    bool(entry["ok"]), entry.get("build_returncode", 0),
                    entry.get("smoke_returncode"), entry.get("build_s", 0),
                    entry.get("test_s", 0), entry.get("size_bytes", 0),
                    "", "", entry.get("log", ""), entry.get("output_tail", ""),
                )
        return None

    def _run_deep_review(self, config, builder):
        if not config.deep_review:
            return
        self._phase("deep_review")
        if not self.store.data["deep_review_initialized"]:
            candidate_sizes = {
                item["name"]: item.get("size_bytes", 0)
                for item in self.store.data["candidates"]
            }
            pending = sorted(
                set(self.store.data["prefilter_required"]) & set(candidate_sizes),
                key=lambda name: (-candidate_sizes[name], name),
            )
            with self.store.transaction() as state:
                state["deep_review_pending"] = pending
                state["deep_review_rounds"] = 0
                state["deep_review_initialized"] = True
            self._log(
                f"[深度复核] 按体积降序复核 {len(pending)} 个预筛必需项，"
                f"最多增加 {config.deep_review_attempts} 轮编译"
            )
        while (
            self.store.data["deep_review_pending"]
            and self.store.data["deep_review_rounds"] < config.deep_review_attempts
        ):
            self._checkpoint()
            name = self.store.data["deep_review_pending"][0]
            excluded = sorted(set(self.store.data["excluded"]) | {name})
            self._log(
                f"[深度复核] 尝试排除 {name}；剩余候选 "
                f"{len(self.store.data['deep_review_pending']) - 1} 个"
            )
            result = self._compiled_test(
                config, builder, excluded, kind="deep_review"
            )
            self._check_abort()
            with self.store.transaction() as state:
                state["deep_review_rounds"] += 1
                state["deep_review_pending"].pop(0)
                if result.ok:
                    state["excluded"] = sorted(set(state["excluded"]) | {name})
                    state["required"] = [
                        item for item in state["required"] if item != name
                    ]
                    state["prefilter_required"] = [
                        item for item in state["prefilter_required"] if item != name
                    ]
                state["current_set"] = []
        if self.store.data["deep_review_pending"]:
            self._log(
                f"深度复核已达 {config.deep_review_attempts} 轮预算，"
                "剩余模块保持保留，不再继续编译"
            )

    def _run_final(self, config, builder):
        self._phase("final")
        excluded = self.store.data["excluded"]
        with self.store.transaction() as state:
            if not state.get("pruned_standalone_size"):
                state["pruned_standalone_size"] = state["baseline"].get("size_bytes", 0)
            state["ddmin_progress"] = {"n": 0, "size": 0}
        self._log(f"[最终] 使用 {len(excluded)} 个排除参数构建 {config.mode}")
        if config.custom_onefile:
            self._log(
                f"[最终] 启用自定义 OnefileBootstrap.c（标识：{config.onefile_bootstrap_name}），"
                "并复制 python3.dll 证书表"
            )
        result = builder.build_and_smoke(excluded, "final", final=True)
        self._check_abort()
        self._record("final", excluded, result)
        if not result.ok:
            raise RuntimeError("最终构建或冒烟测试失败；请检查日志和最终优化参数")
        elapsed = time.time() - self.store.data["started_at"]
        command = final_command(config, excluded)
        with self.store.transaction() as state:
            state["elapsed_s"] = elapsed
            state["final"] = {
                "size_bytes": result.size_bytes,
                "size_mb": result.size_bytes / 1024 ** 2,
                "path": result.executable,
                "command": command,
                "smoke_ok": True,
            }
        report, paths = write_reports(config, self.store.snapshot())
        with self.store.transaction() as state:
            state["phase"] = "done"
            state["status"] = "done"
            state["final"]["report_files"] = [str(path) for path in paths]
            state["final"]["warnings"] = report["warnings"]
            state["current_set"] = []
        builder.cleanup_baseline()
        self._log(f"完成：报告和最终命令已写入 {config.output_dir}")
        self._notify("onPhaseChange", "done")

    def _record(self, kind, excluded, result):
        self._record_entry({
            "kind": kind,
            "set": sorted(excluded),
            "ok": result.ok,
            "build_s": result.build_s,
            "test_s": result.smoke_s,
            "build_returncode": result.build_returncode,
            "smoke_returncode": result.smoke_returncode,
            "size_bytes": result.size_bytes,
            "size_mb": result.size_bytes / 1024 ** 2,
            "log": result.log_path,
            "output_tail": result.output_tail,
        })

    def _record_entry(self, entry):
        self.store.record(entry)
        self._notify("onRoundDone", entry)

    def _phase(self, phase):
        self._checkpoint()
        with self.store.transaction() as state:
            state["phase"] = phase
            state["status"] = "paused" if self.pause_event.is_set() else "running"
        self._notify("onPhaseChange", phase)

    def _checkpoint(self):
        while self.pause_event.is_set() and not self.abort_event.is_set():
            self.abort_event.wait(0.1)
        self._check_abort()

    def _check_abort(self):
        if self.abort_event.is_set():
            raise RunAborted()

    def _log(self, line):
        self.store.log(line)
        self._notify("onLog", line)

    def _notify(self, event, payload):
        try:
            self.listener(event, payload)
        except Exception:
            pass
