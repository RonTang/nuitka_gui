import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class PrunerConfig:
    entry: str = ""
    output_dir: str = ""
    product_name: str = ""
    product_version: str = ""
    company_name: str = ""
    extra_args: str = ""
    mode: str = "onefile"
    console: str = "disable"
    icon: str = ""
    plugins: list[str] = field(default_factory=list)
    data_items: list[dict] = field(default_factory=list)
    auto_data: bool = True
    lto: bool = True
    no_asserts: bool = True
    no_docstrings: bool = True
    upx: bool = False
    whitelist: list[str] = field(default_factory=list)
    deep_review: bool = False
    full_ddmin: bool = False
    deep_review_attempts: int = 5
    custom_onefile: bool = False
    signed_plugin: str = ""
    jobs: int = field(default_factory=lambda: os.cpu_count() or 4)
    timeout_minutes: int = 20
    auto_smoke: bool = True
    smoke_command: str = '"{executable}"'
    assertion: str = "SMOKE_OK"

    @classmethod
    def from_dict(cls, value):
        defaults = cls()
        result = {}
        for name in cls.__dataclass_fields__:
            result[name] = value.get(name, getattr(defaults, name))
        return cls(**result)

    def normalized(self):
        if sys_version() < (3, 12):
            raise ValueError("需要 Python 3.12 或更高版本")
        entry = Path(self.entry).expanduser().resolve()
        if not entry.is_file() or entry.suffix.lower() != ".py":
            raise ValueError("入口脚本必须是存在的 .py 文件")
        if not self.output_dir.strip():
            raise ValueError("请选择输出目录")
        output = Path(self.output_dir).expanduser().resolve()
        if self.mode not in ("onefile", "standalone"):
            raise ValueError("打包模式必须是 onefile 或 standalone")
        if self.console not in ("disable", "attach", "force"):
            raise ValueError("控制台模式无效")
        if self.icon and not Path(self.icon).expanduser().is_file():
            raise ValueError("图标文件不存在")
        if not 1 <= int(self.jobs) <= 256:
            raise ValueError("并行 jobs 必须在 1 到 256 之间")
        if not 1 <= int(self.deep_review_attempts) <= 50:
            raise ValueError("深度复核次数必须在 1 到 50 之间")
        if self.full_ddmin and self.deep_review:
            raise ValueError("完整 ddmin 已复核所有候选，无需同时启用深度复核")
        if self.custom_onefile:
            if self.mode != "onefile":
                raise ValueError("自定义壳与签名复制仅适用于 onefile 模式")
            plugin = Path(self.signed_plugin).expanduser().resolve()
            if not plugin.is_file():
                raise ValueError("signed_payload_plugin.py 不存在")
            if not (plugin.parent / "OnefileBootstrap.c").is_file():
                raise ValueError("签名插件旁边必须存在 OnefileBootstrap.c")
            self.signed_plugin = str(plugin)
        if not 1 <= int(self.timeout_minutes) <= 240:
            raise ValueError("单轮超时必须在 1 到 240 分钟之间")
        if not self.assertion:
            raise ValueError("冒烟断言串不能为空")
        if any((self.product_name, self.product_version, self.company_name)):
            if not self.product_version:
                raise ValueError("填写产品或公司信息后，产品版本不能为空，例如 1.0.0.0")
            if not self.company_name:
                raise ValueError("填写版本信息后，公司名称不能为空")
        self.entry = str(entry)
        self.output_dir = str(output)
        self.jobs = int(self.jobs)
        self.timeout_minutes = int(self.timeout_minutes)
        self.deep_review_attempts = int(self.deep_review_attempts)
        self.plugins = sorted(set(self.plugins))
        self.whitelist = sorted({
            item.strip() for item in self.whitelist if item.strip()
        })
        self.icon = str(Path(self.icon).expanduser().resolve()) if self.icon else ""
        return self

    def to_dict(self):
        return asdict(self)

    @property
    def work_dir(self):
        return Path(self.output_dir) / ".pruner"

    @property
    def state_path(self):
        return Path(self.output_dir) / "pruner_state.json"

    def fingerprint(self):
        content = Path(self.entry).read_bytes()
        payload = json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(
            payload.encode("utf-8") + b"\0" + content
        ).hexdigest()


def sys_version():
    import sys
    return sys.version_info
