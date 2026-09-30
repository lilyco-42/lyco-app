# dsh-lyco-chat — lyco 作为 DeepSeek Harness 插件

两个工具，都走本仓库自己的 Python 实现（`python -m core.cli`），不在 TS 里
重写第二遍检索：

| 工具 | 作用 | 底层 |
|------|------|------|
| `lyco_ask` | 提问 → 本地知识库 / RustCC / DeepWiki 检索 → 本地小模型总结，并把 `verify` 结论一起返回 | `core.loop.answer` |
| `lyco_nearby_shops` | 身边某类店排序（"哪家理发比较好"） | `services.poi` + `services.reviews` |

## 契约来源

`deepseek-ai/deepseek-harness`（**默认分支是 `master`，不是 `main`** —— 上一轮
就是拿 `main` 的路径去请求，404 后反复重试同一个命令而死循环）：

- `docs/user/develop/basic/index.zh.md` —— 插件 = 导出 `name` / `apply(ctx)` 的 TS 模块，
  通过 `cordis.yml` 的 `insert` 覆盖层加载，插件路径必须绝对。
- `docs/user/develop/basic/tool.zh.md` + `docs/cookbook/adding-a-tool.zh.md` ——
  `inject: ['tools']`、`ctx.tools.register(defineTool({...}))`、参数由 schema 校验、
  `output.schema` 声明规范值、`output.render` 只给模型看文本。
- `docs/cookbook/adding-a-package.zh.md` §5 —— `locale/<lang>.json` 的 `meta.title` /
  `meta.description` 与 `exports`/`files` 要求。

## 加载

```sh
node write_patch.mjs                     # 生成本机的绝对路径 cordis.yml
# 需要 deepseek-harness 的仓库检出（从源码运行）：
pnpm dsh web --patch D:/gal/lyco-app/plugins/dsh-lyco-chat/cordis.yml
```

打开 `http://127.0.0.1:3080`，对模型说"用 lyco_ask 问一下 GGUF 和 llama.cpp 的关系"。

## 环境变量

| 变量 | 作用 | 默认 |
|------|------|------|
| `LYCO_PY` | python 解释器 | `python` |
| `LYCO_REPO_ROOT` | 仓库根（`core.cli` 的 cwd） | 从模块位置向上找 `core/loop.py` |
| `LYCO_CLI_MODULE` | 被调用的模块 | `core.cli`（测试里换成 stub） |
| `AMAP_WEBSERVICE_KEY` | 高德 Web 服务 Key | 无，缺了 `lyco_nearby_shops` 报错 |

## 验证到什么程度

`npm test` → **13/13 通过**，其中：

- 工具是真用 `@deepseek-ai/dsh-tools` 的 `defineTool`（devDependency，npm 上
  0.0.1-rc.1）构造的 —— 第一版就被它拒了：`schema.additionalProperties must be
  explicitly true or false`，说明这层校验是真在跑，不是自我安慰。
- `lyco_ask` / `lyco_nearby_shops` 走完整链路：TS → `execFile(python,
  ['-m', 模块, ...])` → JSON → 规范值 → `render` 文本，子进程用真 python，
  被调模块换成 `test_support/core_cli_stub.py`（不依赖模型和网络）。
- 错误路径实测：python 找不到模块时错误原文进了工具的 `error` 字段并被渲染成
  `lyco_ask failed: ...`，不会伪装成一次成功回答；坐标越界在 spawn 之前就被拒。
- 未被证据支持的答复会在给模型的文本里显式标注 `（未被检索证据支持，慎信）`，
  并把 `verify` 的理由一起给出。

**没验证的**：真在 Harness 里加载。本机没有 deepseek-harness 的仓库检出，也没装
桌面端，所以"`pnpm dsh web --patch` 之后插件被 host 调起"这一步只是按官方教程
的形状写的，未在本机跑通 —— 首次接入时请按上面命令实跑一次再签收。

**已知限制**：`lyco_ask` 需要 llama-cli + GGUF（本机 smoke 才通）；DeepWiki 触发配额
时证据会退化成本地 + RSS 两源（见 `lyco-model/DEMO_100rounds.md` §12：限流只重试不
投毒，但拿不到就是拿不到）。
