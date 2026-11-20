# Nuitka Pruner GUI

一个面向 Windows 的 Nuitka 自动精简打包器。使用 `pyminiwebview` 和原生 HTML/CSS/JavaScript 构建界面，通过源码预筛、真实 Nuitka 编译验证和按需 ddmin，自动生成体积更小的 standalone 或 onefile 程序。

工具不仅生成排除参数，还会执行最终打包、运行冒烟测试，并输出体积报告和可重复执行的 BAT/PY 打包命令。

## 主要功能

- 基线 standalone 构建与冒烟验证。
- 从 Nuitka 报告和 `.dist` 目录枚举真实候选模块。
- 源码 import 拦截预筛，减少不必要的编译。
- 整组编译验证优先，失败后才进行分层 ddmin。
- 根据异常日志直接定位被误排除的必需模块。
- 可选的深度复核：按体积降序复核预筛必需项，并限制最大编译轮数。
- 自动包含 pyminiwebview 项目引用的 HTML、JS、CSS、图片、字体、Excel 等资源。
- 支持插件、数据文件、图标、LTO、UPX、控制台模式和产品版本信息。
- 可选的自定义 `OnefileBootstrap.c` 壳和 `signed_payload_plugin.py` 证书表复制。
- 暂停、继续、中止、断点续跑和原子状态保存。
- 自动生成候选清单、测试历史、体积对比和最终命令。
- 提供 GUI 和命令行两种使用方式。

## 环境要求

- 64 位 Windows。
- Python 3.9 或更高版本。
- Microsoft Edge WebView2 Runtime，Windows 11 通常已预装。
- Nuitka。
- 仓库已附带 `pyminiwebview.pyd`、Win32 和 helpers 组件，无需另行安装 pyminiwebview。
- 使用 LTO 或自定义 onefile 壳时，需要可用的 MSVC 或 Nuitka 支持的其他 C 编译器。
- 使用 UPX 时，需要 `upx.exe` 位于 `PATH`。
- 构建目录所在磁盘建议至少保留 5GB 可用空间。

## 安装

### 1. 获取本仓库

```bash
git clone https://github.com/RonTang/nuitka_gui.git
cd nuitka_gui
```

### 2. 准备 Python 环境

建议使用虚拟环境：

```bash
py -3.9 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install nuitka
```

也可以直接使用已有的 Python 环境，但启动打包器的 Python 必须同时能够导入 Nuitka 和 pyminiwebview。

### 3. pyminiwebview 已随仓库提供

仓库根目录已包含 64 位 Windows abi3 原生扩展 `pyminiwebview.pyd`，并附带 `pyminiwebview_win32` 和 `pyminiwebview_helpers`。从仓库根目录运行 `pruner.py` 时，Python 会直接加载这些文件，无需另外安装 pyminiwebview。

该扩展使用 `Py_LIMITED_API=0x03090000` Stable ABI（abi3），支持 64 位 CPython 3.9 及更高版本；打包器本身也支持 Python 3.9+。目标机器还需要 WebView2 Runtime。

如果需要更新扩展，可从 pyminiwebview 项目的 Release 或 GitHub Actions Artifacts 获取新版 wheel：

- https://github.com/RonTang/pyminiwebview

检查环境：

```bash
python -c "import pyminiwebview; import nuitka; print('环境正常')"
python -m nuitka --version
```

## 启动

### 图形界面

```bash
python pruner.py
```

使用指定 Python 版本：

```bash
py -3.13 pruner.py
```

如果通过虚拟环境安装依赖：

```bash
.venv\Scripts\python.exe pruner.py
```

### 命令行

最简单的 onefile 精简：

```bash
python -m nuitka_pruner path\to\main.py path\to\output
```

指定 standalone 输出、并行数和超时：

```bash
python -m nuitka_pruner main.py output --mode standalone --jobs 8 --timeout 20
```

命令行默认使用与 GUI 相同的自动冒烟和资源检测。

## 图形界面使用流程

### 第一步：配置

#### 基本设置

- **入口脚本**：目标程序的 Python 入口，例如 `main.py`。
- **输出目录**：状态、日志、报告和最终程序的保存位置。
- **产品名称、产品版本、公司**：写入 Windows 版本信息。
- **附加 Nuitka 参数**：用于添加界面未覆盖的高级参数。

注意：填写产品或公司信息后，需要同时填写有效的产品版本，例如 `1.0.0.0`。如果不需要版本信息，可以将产品名称、产品版本和公司全部留空。

#### 打包模式

- **onefile**：生成单个 EXE，启动时由 bootstrap 解包。
- **standalone 文件夹**：生成包含 EXE、DLL 和资源的目录。

无论最终选择哪种模式，精简迭代内部始终使用 standalone，以避免 onefile 压缩拖慢每一轮测试。

#### 控制台

- `disable`：适用于 GUI 程序。
- `attach`：附加到已有控制台。
- `force`：适用于需要控制台输入输出的 CLI 程序。

#### 图标和插件

图标只影响最终产物。插件可以手动勾选；选择入口后，工具会根据入口中的常见 import 自动预勾选 PySide6、PyQt、tkinter、NumPy 等插件。

#### 数据文件

每行包含：

- 源文件或源目录。
- 相对于分发目录的目标路径。
- 文件或目录类型。

对于 pyminiwebview 项目，默认开启自动资源检测。工具从入口沿本地 import 图扫描，识别能够明确解析到现有文件的资源引用，并保留相对目标目录。

支持的典型写法包括：

```python
Path("web/index.html")
Path(__file__).resolve().parent / "web" / "index.html"
os.path.join(os.path.dirname(__file__), "web", "app.js")
```

自动检测覆盖常见 Web 资源、图片、字体、JSON、CSV 和 Excel 文件。动态拼接且无法静态确定的资源路径，请在数据文件列表中手动添加。

内嵌在 Python 字符串中的 HTML/JS 不需要额外包含文件。

#### 体积优化

以下选项只用于最终构建：

- **LTO**：链接时优化，可能进一步减小体积，但会增加构建时间。
- **no_asserts**：移除断言。
- **no_docstrings**：移除文档字符串。
- **UPX**：默认关闭；启用前必须安装 UPX。

### 第二步：选择冒烟方式

#### 自动冒烟

默认开启，目标程序不需要专门实现 `--smoke-test`。

默认命令：

```text
"{executable}"
```

`{executable}` 是占位符：

- 源码预筛时，由工具替换为 Python，并自动加载入口和 import 拦截器。
- 编译验证时，替换为刚生成的 EXE。

自动模式会：

1. 启动目标程序。
2. 检测目标进程及其子进程的 GUI 窗口。
3. 向窗口发送正常的 `WM_CLOSE`，而不是通过强杀退出码判断成功。
4. 检查目标退出码。
5. 检查日志中的 Traceback、pyminiwebview 桥接异常和线程异常。
6. 正常退出且无已知异常时输出断言 `SMOKE_OK`。

自动冒烟主要验证启动、窗口和正常退出，不能证明所有业务功能都正确。涉及文件解析、数据库、网络、插件或特定业务流程时，建议增加严格功能自检。

#### 严格自定义冒烟

关闭“自动冒烟”后，可以指定自己的命令和断言串。例如目标支持：

```text
"{executable}" --smoke-test
```

目标程序应自行完成核心功能检查，输出：

```text
SMOKE_OK
```

然后以退出码 0 结束。工具要求退出码为 0 且输出包含断言串。

严格自检应尽量覆盖真实功能，而不只是创建窗口。例如 Excel 程序应实际解析一个测试工作簿，GUI 无法无头运行时应自行安排正常退出。

### 第三步：选择精简策略

默认流程已经优先减少编译次数：

1. 构建并验证基线。
2. 整组源码预筛。
3. 根据异常快速定位明显必需项。
4. 对剩余排除项执行一次真实 standalone 编译验证。
5. 只有失败且日志无法定位时，才进入分层 ddmin。
6. 构建最终产物并再次冒烟。

#### 完整 ddmin

默认的快速分层模式优先减少编译次数，但不会编译复核所有预筛必需项，也会固定已经验证的分层集合。如果需要针对当前冒烟预言获得全集上的 1-最小保留集，可以启用“完整 ddmin”：

- 跳过源码预筛对候选集合的约束。
- 复核全部候选，包括预筛认为必需的模块。
- 不使用异常日志预剪枝或分层固定集合。
- 直接在全集上运行经典 ddmin，直到收敛。
- 运行页显示当前粒度 `n / len(keep)`，并支持断点续跑。

完整模式可能产生大量编译，不设置轮次预算，也不能弥补业务冒烟未覆盖的路径。它与深度复核互斥。若整组排除后测试通过，保留集已经为空，无需继续运行 ddmin。

#### 深度复核预筛必需项

源码直跑和 Nuitka 编译后的导入行为可能不同。某些模块在源码模式中必需，但编译后仍可安全排除。

启用“深度复核预筛必需项”后，工具会：

- 按候选体积从大到小排序。
- 逐个将预筛必需项加入排除集并进行真实编译验证。
- 成功的模块立即转入最终排除清单。
- 达到指定预算后停止，不再继续消耗编译时间。

默认最多复核 5 轮，可设置为 1–50 轮。预筛必需项较多时，可以适当增加预算；预算越大，可能获得的排除项越多，但总编译时间也会增加。

### 第四步：运行与控制

“运行”页面显示：

- 当前阶段和状态。
- 真实编译轮数，不包含缓存命中。
- 候选、已排除和必保留数量。
- 本轮排除集合。
- 每轮构建结果、耗时和产物大小。
- 实时日志。

控制按钮：

- **暂停**：当前构建或冒烟结束后暂停，不会强行挂起 C 编译器。
- **继续**：继续暂停的任务。
- **中止**：终止当前进程树，保留已完成历史，之后可以续跑。
- **重置**：清除当前状态和历史，保留日志文件。

每个测试单元结束后都会写入状态。程序异常关闭后，使用相同配置重新开始即可复用已完成的相同测试。

### 第五步：查看和导出报告

完成后，“报告”页面显示：

- 基线 standalone 体积。
- 精简 standalone 体积。
- 最终 onefile 或 standalone 体积。
- 节省体积和比例。
- 安全排除与必须保留清单。
- 动态导入警告。
- nofollow 无法直接处理的大型数据目录。
- 最终完整打包命令。
- `verification_mode`：`fast-layered` 或 `full-ddmin`。
- `smoke_mode`：`automatic` 或 `strict-custom`。

支持复制命令，以及导出 JSON、BAT 和 PY 文件。

## 输出文件

默认写入配置的输出目录：

```text
output/
├── final_dist/              最终 onefile 或 standalone 产物
├── logs/                    每轮构建和冒烟日志
├── .pruner/                 迭代临时目录
├── candidates.json          候选模块、体积和风险信息
├── pruner_state.json        原子保存的断点续跑状态
├── pruner_report.json       体积、清单和历史报告
├── final_command.bat        可直接复用的 Windows 命令
└── final_command.py         使用当前 Python 调用 Nuitka 的脚本
```

迭代构建使用独立临时目录，不添加 `--clean-cache`，以保留 Nuitka 编译缓存。

## 自定义 onefile 壳与证书表复制

仓库包含：

- `OnefileBootstrap.c`
- `signed_payload_plugin.py`

在 GUI 中启用“使用自定义 OnefileBootstrap.c 壳并复制 python3.dll 证书表”后，最终 onefile 构建会添加：

```text
--user-plugin=path\to\signed_payload_plugin.py
```

插件会：

1. 将同目录的自定义 `OnefileBootstrap.c` 用于 onefile bootstrap。
2. 将 `python3.dll` 的证书表复制到包内主程序二进制。
3. 修改与自定义壳匹配的 payload 标头。

该功能只用于最终 onefile，不用于基线或 ddmin 迭代。最终冒烟会验证自定义壳能够正常解包和启动程序。

注意：复制证书表不等于对新 EXE 重新进行 Authenticode 签名。若需要有效的发布签名，仍应使用自己的证书和正式签名工具对最终产物签名。

## CLI 示例

启用深度复核，最多增加 8 次编译：

```bash
python -m nuitka_pruner main.py output --deep-review --deep-review-attempts 8
```

对全部候选运行完整 ddmin：

```bash
python -m nuitka_pruner main.py output --full-ddmin
```

启用自定义 onefile 壳：

```bash
python -m nuitka_pruner main.py output --custom-onefile --signed-plugin "D:\path\to\signed_payload_plugin.py"
```

关闭自动冒烟，使用目标自己的自检：

```bash
python -m nuitka_pruner main.py output --no-auto-smoke --smoke-command '"{executable}" --smoke-test' --assertion SMOKE_OK
```

指定 GUI 控制台、图标和插件：

```bash
python -m nuitka_pruner main.py output --console disable --icon app.ico --plugin pyside6
```

关闭 LTO 以缩短最终构建时间：

```bash
python -m nuitka_pruner main.py output --no-lto
```

查看全部参数：

```bash
python -m nuitka_pruner --help
```

## 常见问题

### 提示 `No module named nuitka`

打包器使用启动它的 Python 调用 Nuitka。请检查：

```bash
python -m nuitka --version
```

如果依赖安装在 Python 3.13，而当前 `python` 指向其他版本，请显式启动：

```bash
py -3.13 pruner.py
```

### Nuitka 提示缺少公司或产品版本

填写产品名称、公司或版本信息时，请同时提供公司名称和有效产品版本，例如 `1.0.0.0`。也可以将产品名称、公司和版本全部留空。

### 普通 GUI 在旧流程中一直等到冒烟超时

请使用当前版本并保持“自动冒烟”开启，默认命令为 `"{executable}"`。目标无需识别 `--smoke-test`。

### 程序能启动，但某个业务功能失败

自动冒烟覆盖不到所有延迟功能。请检查日志中的 Traceback 或桥接异常，将相关模块加入白名单，或为程序增加覆盖该业务路径的严格自检。解析 Excel 等任务必须实际执行解析，不能只验证窗口出现。

### 最终 onefile 比基线小很多，是否能证明所有功能正常

不能。体积和排除数量不是正确性的证明。应结合真实功能自检、动态导入警告和报告中的大型数据目录进行验收。

### 如何加快重复打包

- 不要清理 Nuitka 编译缓存。
- 使用相同输出目录和配置续跑。
- 保持默认的整组验证优先策略。
- 仅在需要进一步压缩时开启深度复核。
- 调试构建可关闭 LTO 和 UPX。

## 开发与贡献

核心代码位于：

```text
pruner.py                    GUI 入口
nuitka_pruner/orchestrator.py  流程调度、预筛、编译验证与深度复核
nuitka_pruner/build.py        Nuitka 命令、构建和冒烟封装
nuitka_pruner/ddmin.py        ddmin 实现
nuitka_pruner/smoke_runner.py 自动窗口和异常冒烟
nuitka_pruner/web_assets.py   pyminiwebview 资源自动检测
nuitka_pruner/ui.py           原生 HTML/CSS/JavaScript 界面
nuitka_pruner/ui_bridge.py    UI 与 Python 桥接
```

更详细的算法和开发约定见 [nuitka-pruner-dev-guide.md](nuitka-pruner-dev-guide.md)。

作者：Ron Tang

邮箱：tzq2008wd@gmail.com
