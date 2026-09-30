# 端侧跑 Python：把 lyco core 放进安卓的可行性审计

`mobile/inference` 是最后一个"要动 native"的模块，而 `core/` + `services/` 全是
Python。这份文档回答一个问题：**这些 Python 代码能不能原样搬进安卓 App。**
依据是 CPython 官方安卓文档（3.14.7，2026-09-30 更新）+ 本仓库今天的实测，不是印象。

## 结论先说

1. **能搬**：core/services 的运行时依赖在安卓上几乎全部可用。
2. **只有一处硬阻塞**：`core/summarizer.py:51` 用 `subprocess` 调 `llama-cli`。
   官方口径是"安卓上创建子进程 *可能* 但不被官方支持"，且不支持 System V IPC →
   `multiprocessing` 直接不可用。所以这一处必须换成 in-process 的 llama.cpp（JNI/.so）。
3. 接缝已经有了：`core.loop.answer(question, summarize_fn=...)`（本次同步自 lyco-model），
   换后端不用动 router/retrievers/verify。
4. **`python -m core.cli` 这条缝在手机上不存在**：移动端只能嵌入式模式，
   没有 REPL、没有 `python`/`pip` 可执行文件，`stdout` 还会被重定向到 logcat
   （`python.stdout`）。所以那条 CLI 是给桌面/DSH 用的，端侧必须是函数调用。

## 运行时 import 审计（core/ + services/ 全部非测试代码）

| import | 用在 | 安卓状态 | 依据 |
|---|---|---|---|
| `json`, `re`, `os`, `sys`, `time`, `typing`, `contextlib`, `traceback` | 到处 | ✅ 正常 | 文件 I/O 按 POSIX 行为 |
| `xml.etree.ElementTree` | `retrievers/rss.py` 解 RSS | ✅ 标准库 | — |
| `argparse` | `core/cli.py` | ⚠️ 用不上（无 CLI 入口），不影响库路径 | 嵌入式模式限制 |
| `httpx` | `retrievers/__init__.py`、`services/poi` | ✅ 纯 Python，见下 | PyPI wheel 检查 |
| `socket`/`ssl`/线程（httpx 底下） | 网络检索 | ✅ "File I/O, socket handling, and threading all behave as they would on any POSIX operating system." | 官方安卓页 |
| `subprocess` | **只有 `core/summarizer.py`** | ❌ 换掉 | "creating subprocesses is possible but officially unsupported"；无 System V IPC → `multiprocessing` 不可用 |

第三方栈不需要 Android wheel：`httpx 0.28.1`、`httpcore 1.0.9`、`anyio 4.15.1`、
`sniffio 1.3.1`、`certifi 2026.7.22`、`idna 3.20`、`h11 0.16.0` —— 当前发行版**全部只有
`py3-none-any` wheel，0 个二进制 wheel**（今天查 PyPI JSON 得到）。因此不需要
cibuildwheel 交叉编译，只要把包目录塞进 assets 里就行。

**待实测**（不能靠推理下结论）：
- `anyio` 运行时会读 `importlib.metadata` 的 dist-info；嵌入式打包如果没带 `.dist-info`
  可能抛异常。真机/模拟器上 import 一次才算数。
- `certifi` 的 CA 路径在只读 assets 下能否被 `ssl` 读到（否则得走安卓系统证书）。

## 分发方式怎么选（官方列的那几条路）

| 方式 | 适配"已有 RN App"？ | 说明 |
|---|---|---|
| **Chaquopy**（Gradle 插件） | ✅ 最合适 | 直接往现有 app module 里塞 Python + 原生库，RN 侧走它提供的调用；我们的依赖是纯 Python，正好是它的舒适区 |
| Briefcase (BeeWare) | ❌ | 它要拥有整个 App 工程，和 RN 壳冲突 |
| Buildozer / python-for-android (Kivy) | ❌（本项目） | 同上，面向 Kivy 自己那套 UI 栈 |
| pyqtdeploy | ❌ | 面向 Qt |
| Termux | ⚠️ 只适合开发/演示 | 我们已有 Termux 一键脚本，但那不是能上架的分发形态（依赖外部 App、无法随包发布） |
| 手写 `libpython` + JNI（官方 6.1 全流程） | ✅ 但最贵 | 可控性最高；等于自己实现一遍 Chaquopy |

**建议路线**：Chaquopy 装解释器 + 把 `core/`、`services/` 作为 site-packages 打进 assets；
`llama.cpp` 仍然走我们自己的 `.so`（`mobile/inference` 的真活，JNI 调用，CI 里构建，
参考 huzpsb/llama_cpp_android_ci 与 pocketpal-ai 的接入方式）；`summarizer` 的安卓后端
= JNI 调 llama.cpp 的 complete，替掉那唯一一处 `subprocess`。

## 端侧模型口径（来自 lyco-model §12 实测，不是估算）

- 0.6B Q4_K_M：CPU 92–95 t/s，单轮 0.8 s 级；1.7B：47 t/s，单轮 2.2 s。
- 内存大头是上下文池不是权重：`-c 8192` 时空载 ~1.5 GB，`-c 16384` 再加 ~0.9 GB
  —— 手机上要省内存**先砍 `-c`，别去调 `-np`**（`-np` 还会把 `-c` 按槽位切，
  槽位越窄越容易把证据 prompt 直接拒掉）。

## 铁律没变

构建全部在 CI（`.github/workflows/ci.yml`），本机不产 `.so`/APK；模型和大文件不进 git。
