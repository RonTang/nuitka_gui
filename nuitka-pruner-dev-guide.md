# Nuitka 自动精简打包器（ddmin packer）开发指南

> 本文档是写给实现者（Kimi Code / 人工）的完整开发规范。按本指南可实现一个
> 用「delta debugging（ddmin）」自动找出 Nuitka 最小必需模块集合、并输出精简
> 打包参数的桌面工具。

## 0. 目标一句话

输入：一个 Python 入口脚本 + Nuitka 参数 + 冒烟测试。
输出：最小排除清单（`--nofollow-import-to=...` 参数组）+ 最终 onefile 打包 + 体积对比报告。

## 1. 技术栈（硬性约定）

- **窗口与 UI**：`pyminiwebview`（用户自研，github.com/RonTang/pyminiwebview）+ **原生 HTML/CSS/JS**。
- UI 不复杂，**禁止引入任何前端第三方库**（不上 Vue / Element Plus / 任何 CDN 框架）。
- Python 侧用 pyminiwebview 的 JS↔Python 桥暴露 API 供前端调用；具体 API 名称以该仓库文档/示例为准，封装成一层 `ui_bridge.py` 隔离。
- **Python ≥ 3.12**，Windows 桌面（PowerShell 环境）。
- **打包器**：Nuitka（standalone + onefile）。
- 进程调度：`subprocess`（Windows 下注意 `creationflags=CREATE_NEW_PROCESS_GROUP`，保证能杀掉子树）。
- 不引入 heavy 依赖；纯 stdlib 优先（zipfile/ElementTree 解析风格参照 grade_xlsx 项目的取舍）。

## 2. 总体架构：两层过滤 + ddmin

直接对「每轮一次完整 Nuitka 编译」跑 ddmin 不可行（一轮几分钟，几十轮一晚上）。
必须拆成两层，**编译次数压缩到个位数**：

```javascript
入口脚本 ──► [0] 基线 standalone 构建 ──► .dist 目录（基准体积、import 图）
                │
                ▼
        [1] 候选枚举（扫 .dist 目录结构 + 白名单清洗）
                │
                ▼
        [2] 快筛：.dist 大目录肉眼规则（translations、QtWebEngine、test/unittest 子包）
                │
                ▼
        [3] 预筛（源码模式，秒级）：import 拦截器 + 冒烟测试 ──► 安全排除集 excluded_pre
                │
                ▼
        [4] 验证 + ddmin（编译模式，分钟级）：真实 Nuitka 构建 + 冒烟测试
                │
                ▼
        [5] 输出：最小排除清单、最终 onefile 打包、体积报告（可导出 bat/py）
```

第 3 层把候选从几百个砍到个位数存疑名单；第 4 层只对存疑名单做 ddmin 收尾。

## 3. 核心算法：ddmin（修正版）

**禁止**朴素二分（无法处理多个模块同时必需的场景）。标准 ddmin，语义反过来用：
把「排除后冒烟测试通过」当作 ddmin 的 "fail"（即"找到了可排除配置"）。

全程维护三个互斥集合：

```javascript
required = set()   # 排除后崩溃/冒烟失败 → 必须保留
excluded = set()   # 排除后通过 → 安全丢弃
unknown  = set(M)  # 候选集中尚未测试的部分
```

伪代码（正确的 reduce/complement/细分 三分支）：

```python
def ddmin(unknown, required, excluded, n=2):
    # unknown 全部测完
    if not unknown:
        return required, excluded
    # 粒度已到单个
    if len(unknown) <= 1:
        m = unknown.pop()
        if test_exclusion(required | {m}):      # 能跑
            excluded.add(m)
        else:
            required.add(m)
        return required, excluded

    chunks = split(unknown, n)                  # 尽量均分
    for chunk in chunks:
        rest = unknown - chunk                  # 其余作为"必保留"参与本轮测试
        if test_exclusion(required | rest):     # reduce：整块排除后仍能跑
            excluded |= chunk
            return ddmin(rest - set(), required, excluded, n=2)
    for i in range(len(chunks)):                # complement：排除补集
        comp = set().union(*[c for j, c in enumerate(chunks) if j != i])
        if test_exclusion(required | comp):
            excluded |= (unknown - comp)
            return ddmin(comp, required, excluded, max(n - 1, 2))
    if n < len(unknown):                        # 细分粒度
        return ddmin(unknown, required, excluded, min(len(unknown), n * 2))
    # n 已达上限仍全失败：逐个测试
    for m in sorted(unknown):
        if test_exclusion(required | (unknown - {m})):
            excluded.add(m); unknown.discard(m)
            return ddmin(unknown, required, excluded, n=2)
        required.add(m)
    return required, excluded
```

注意：

- 顶层粒度 = **top-level 包**（与 `--nofollow-import-to=包名` 一一对应）。
- 子模块级细粒度只对预筛后体积仍大的单个包开第二轮 ddmin，收益小、轮次翻倍，默认关闭。
- 每轮测试必须记录：测试集合、构建/测试退出码、耗时、产物体积，写入状态文件（见 §8）。

## 4. 模块一：候选枚举

- 首选来源：基线 `.dist` 目录结构（目录层级即包结构，top-level 目录名 = 候选粒度）。
- 备选来源：`python -m nuitka --standalone --show-modules` 输出解析。
- 白名单（永不进入候选）：
- 业务自身代码（入口脚本、同级包，用 `__name__`/`sys.path` 推断）；
- 解释器底层：`sys / builtins / os / io / importlib / types / abc / enum / struct / zlib / binascii` 等；
- GUI 框架核心及其 C 扩展（tkinter → `_tkinter`，PySide6 → `PySide6 / shiboken6` 与 `plugins/platforms/*` 等数据文件）；
- 用户可在配置页追加白名单条目。
- 输出 `candidates.json`：`{name, size_bytes, is_c_extension, sample_files}`。

## 5. 模块二：源码模式预筛（秒级）

用一个 import hook 在**源码直跑**时拦截候选包，跑冒烟测试：

```python
# blocker.py（实现要点，非最终代码）
import sys
BLOCKED = frozenset(open("candidates.txt", encoding="utf-8").read().split())

class _Blocker:
    def find_module(self, name, path=None):
        if name.split(".")[0] in BLOCKED:
            return self
    def load_module(self, name):                # 兼容旧协议；优先实现 find_spec
        raise ImportError(f"blocked by pruner: {name}")

sys.meta_path.insert(0, _Blocker())
```

- 现代写法用 `MetaPathFinder` + `find_spec` 返回 `ModuleSpec(loader=BlockerLoader())`，
`BlockerLoader.exec_module` 抛 `ImportError`。
- 启动方式：`python -X frozen_modules=off -c "import blocker; blocker.install(); runpy.run_path('main.py', run_name='__main__')"`
或写入临时目录的 `sitecustomize.py` + `PYTHONPATH` 注入。
- 语义对齐：`--nofollow-import-to` 下，跑到被排模块的 import 语句 = 运行时 ImportError，
与拦截器行为等价。**try/except 保护的导入（如 zipfile 里的 bz2/lzma）会静默通过**，
这层结果只能算预筛，必须经第 4 层编译验证。
- C 扩展被拦截时 `ImportError` 路径一致，但**数据文件、动态加载**（importlib 字符串导入、
Qt 插件）两层语义可能不同 → 全部标记为「存疑」，进编译验证名单。

## 6. 模块三：Nuitka 构建封装（build.py）

- 命令模板（ddmin 循环内用 standalone，禁 onefile）：

```bat
python -m nuitka --standalone --jobs=%N% --remove-output ^
  --nofollow-import-to={m1} --nofollow-import-to={m2} ... ^
  {extra_args} --output-dir={tmp_dir} main.py
```

- **硬性规则**：
- ddmin 循环里**绝不加 `--clean-cache`**，保留 Nuitka 编译缓存，这是迭代速度的命根子；
- 循环里**禁 UPX / LTO**（省时间不省体积），最终打包才开；
- 每次构建到独立临时目录，结束归档或删除；磁盘水位检查（预留 ≥5GB）；
- 单轮超时（默认 20 min）+ 进程树强杀（job object / taskkill /T）；
- stdout/stderr 实时落盘 `logs/run_xxx.log`。
- `test_exclusion(required_set)`：把 `required_set` 全部加入**白名单参数**
（`--include-module` 或从排除参数中剔除），保证本轮测试语义正确。

## 7. 模块四：冒烟测试规范

- 约定：目标程序支持隐藏自检开关 `--smoke-test`（若已有更好）：
初始化核心路径（不弹窗）→ 打印 `SMOKE_OK` → `sys.exit(0)`；任何异常 exit(非0)。
- GUI 无法无头自检时：程序内 `QTimer.singleShot(3000, app.quit)` / `root.after(3000, root.destroy)`
**自行退出**；**禁止**靠外部 taskkill 判定（被强杀退出码非 0，判定不可靠）。
- 判定逻辑：退出码 0 **且** stdout 含 `SMOKE_OK`（可配置断言串）。
- 基线未全绿**禁止**进入 ddmin 循环（这是底线，防止在坏基线上空转几十轮）。

## 8. 状态持久化与断点续跑（state.py）

- 状态写 `pruner_state.json`（原子写：先 tmp 再 os.replace）：

```json
  {
    "phase": "baseline|prefilter|ddmin|final",
    "candidates": [...], "required": [...], "excluded": [...],
    "unknown": [...], "history": [{"set": [...], "ok": true, "build_s": 183, "size_mb": 42.1}],
    "baseline": {"size_mb": 55.0, "smoke_ok": true}
  }
```

- 每个测试单元（预筛一轮 / 编译一轮）结束即落盘；进程被杀后重开从上次状态恢复。
- 提供「重置」按钮（清状态、保留日志）。

## 9. UI 设计（pyminiwebview + 原生 HTML/CSS/JS）

单页三区块，侧边导航切换（display:none 切换即可，不做路由框架）：

1. **配置**（选项即各类控件，值为最终打包参数；精简迭代阶段一律 standalone，见下「打包模式」说明）：
   - **基本**：入口脚本（浏览对话框）、输出目录、产品名称/版本/公司（`--product-name` 等，
     可留空）、附加参数（多行文本，原样追加到命令行，给高级用户兜底）。
   - **打包模式**（单选）：`onefile` / `standalone 文件夹`。
     注意：**ddmin 循环内部永远用 standalone + 临时目录**（onefile 压缩拖慢迭代）；
     本选项只决定**最终交付产物**形态，报告里两种产物的体积都给出。
   - **控制台**（单选）：`--windows-console-mode=disable`（GUI 默认）/
     `attach` / `force`（CLI 工具选 force）。
   - **图标**：`--windows-icon-from-ico=` 文件选择（.ico）；留空不传该参数。
     图标只影响最终产物，不进 ddmin 循环。
   - **插件**（多选）：`--enable-plugin=` pyside6 / pyqt5 / pyqt6 / tk-inter / numpy 等；
     按入口脚本检测到的 import 自动预勾选，用户可改。
   - **数据文件**：`--include-data-files=` / `--include-data-dir=` 列表（可增删的行编辑器），
     常见误用是焊进大体积资源，列表旁实时显示估算体积。
   - **体积优化**（复选框）：LTO（`--lto=yes`，默认开，需本机有 MSVC/gcc）、
     `no_asserts`、`no_docstrings`、UPX（默认关，开启前检测 upx 是否在 PATH）。
   - **精简控制**：候选白名单追加（tag 式输入，逗号分隔）、并行 jobs（默认 CPU 核数）、
     单轮超时（默认 20 min）、冒烟测试命令与断言串（默认 `SMOKE_OK`）。
2. **运行**：当前阶段（基线/预筛/ddmin/最终）、本轮测试集合展示、绿/红状态表、
实时日志区（`<pre>` + 定时拉取增量，或桥接层推消息）、进度估算
（`已完成轮次 / 预估总轮次`，预估按 `log2` 上界算，不装精确）、暂停/继续/中止按钮。
3. **报告**：required / excluded 两张清单、体积对比（基线 → 最终，原生 `<table>` + CSS 条形，
不引图表库）、一键复制最终打包命令、导出 bat / 导出 py 参数文件。

桥接 API（Python→JS 单向推送 + JS→Python 调用）：

```javascript
# JS 调 Python
pruner.start(config) / pruner.pause() / pruner.resume() / pruner.abort() / pruner.reset()
pruner.pick_file(filter) -> path  # 弹出文件选择（filter: py/ico/all）
pruner.get_state() -> json        # 轮询用
# Python 推 JS
window.onLog(line), window.onPhaseChange(phase), window.onRoundDone(result)
```

实现细节以 pyminiwebview 仓库的桥接 API 为准，全部经 `ui_bridge.py` 隔离，UI 代码不直接接触子进程。

## 10. 输出与最终打包

ddmin 收敛后生成最终命令（onefile + 优化参数）：

```bat
python -m nuitka --standalone --onefile --jobs=%N% ^
  --windows-console-mode=disable ^
  --nofollow-import-to={excluded...} ^
  --lto=yes --python-flag=no_asserts --python-flag=no_docstrings ^
  --remove-output --output-dir=final_dist main.py
```

- UPX 作为可选项（默认关，需本机装有 upx）。
- 报告必须给出：基线体积 / 最终体积 / 节省比例 / 总耗时 / 每轮历史表。

## 11. 已知坑（硬性规则，写进代码注释）

1. **try/except 保护导入**（zipfile→bz2/lzma、shutil→lzma）：排除后静默降级，冒烟测试
必须覆盖真实功能路径，不能只看启动退出码。
2. **无条件底层导入不能排**：实测 `binascii` 被 zipfile 无条件 import，排除即 ModuleNotFoundError
（真实案例，来自成绩统计应用打包，作为本项目 fixture 测试用例）。
3. **库顶层无条件 import 第三方包**：如 pyminiwebview helpers 顶层 import AsyncBridge →
asyncio 排不掉，除非库改 PEP 562 惰性导出。遇到这类，报「库约束」提示用户，不强删。
4. **动态导入**（importlib 字符串、插件机制）：预筛和静态分析都测不到，只能靠冒烟测试覆盖；
报告里对「排除清单中曾被字符串引用」的模块给警告。
5. **数据文件不随 nofollow 消失**：Qt 插件、translations、tcl/tk 库目录等要在最终报告里
单列「体积仍大但 ddmin 管不到的目录」，提示用 `--noinclude-data-files` / 手工删。
6. **GUI 框架白名单**：PySide6/PyQt 的 `plugins/platforms/qwindows.dll` 等是运行时动态加载，
永远进白名单；tkinter 的 tcl/tk 数据目录同理。
7. 排除列表里「本来就不在 import 图的包」是无效参数（实测教训：pandas/numpy 不在图里时
写了也白写，还可能误导用户以为生效）。

## 12. 里程碑

| 里程碑 | 内容 | 验收 |
| --- | --- | --- |
| M1 | 无 UI，CLI 跑通 §0 全流程（含两层过滤 + ddmin） | 在一个真实 PySide6/tkinter demo 上收敛，结果与手工验证一致 |
| M2 | 状态持久化 + 断点续跑 + 日志 | kill -9 后重启恢复，历史不丢 |
| M3 | pyminiwebview UI 壳接入 M2 核心 | 三区块界面可完成一次完整精简 |
| M4 | 报告与导出（bat/py/复制命令） | 导出命令可直接跑通最终打包 |

## 13. fixture 测试用例（开发自测用）

用个已知答案的小项目验证算法正确性：
mini spore 我自己最小打包 onefile可以压缩到3.5MB