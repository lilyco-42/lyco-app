# lyco-app AGENTS.md — 所有 AI 必读

## 铁律

1. **不本机编译**：`.so` / APK / 二进制构建一律走 GitHub Actions（参考 huzpsb/llama_cpp_android_ci
   模式）。本机只跑 Python 逻辑测试，绝不在本机跑 ndk-build / cargo-ndk / gradle assemble。
2. **先调研再动手**：沿用 lyco-skill（预研先行 + OODA），新模块先 gh 搜现成方案。
3. **模型与大文件不进 git**：`*.gguf`、`.cache/`、`__pycache__/` 已忽略；模型走 HF 下载。
4. **core 不依赖 mobile**：双向只经过 services 函数接口（见 docs/ARCHITECTURE.md）。

## 模块分工

见 `docs/MODULE_TASKS.md`（难度 / 负责人 / 耦合度，含 2026-09-30 的逐条复核记录）。
Cline 派单用免费模型（当前：`z-ai/glm-5.3-flash`），单子必须带验收标准。

## 测试入口（改完必须自己跑一遍再提交）

```bash
python test_core_offline.py            # core 逻辑：无模型、无网络，CI 跑这份
python test_core.py                    # 本机 smoke：需要 llama-cli + D:/gal/AliceInCradle/kb
python services/poi/test_poi.py        # 高德封装，脚本自带入口（环境里没有 pytest）
python services/reviews/test_reviews.py
node --test mobile/sensors/test_permissions.mjs
cd mobile/app && npx tsc --noEmit && npx jest
cd plugins/dsh-lyco-chat && node --test test_plugin.mjs
cd mobile/app && npm run storybook:build   # 设计态预览（react-native-web），产物 storybook-static/
```

改过 `mobile/app/package.json` 或 lock 之后，**必须再跑一次干净安装**再提交：
本机 npm 是 11，CI 是 node 22 自带 npm 10，两者对 lock 的严格程度不同，
只有 `rm -rf node_modules && npx npm@10 ci` 过了才算同步（npm 11 会放过 npm 10 拒绝的树）。

Android/APK 只在 CI 构建：`.github/workflows/ci.yml`
（python → mobile → plugin → preview → android，外加按需的 device）。
`device` job 在 **macOS arm64 runner** 上用 API 33 aarch64 模拟器真装真点，产出
`emulator-screenshots` 产物；Linux runner 拿不到 `/dev/kvm`，x86_64 AVD 软件模拟
启动不进来，所以这条只能在 macOS 上跑。macOS 分钟按倍率计费，因此它
**只在 `workflow_dispatch` 时跑**：`gh workflow run ci.yml`（dispatch 默认就在 main 上）。
改 UI 时日常看 `storybook-preview`（每次 push 都出），要像素真相再手动触发 device。
`gradlew` 从 Windows 提交会丢执行位，workflow 里已 `chmod +x`；本地别补这个动作，
也别在本地跑 gradle。

## core 的事实来源

`core/` 是 lyco-model `rag_loop.py` 的移植，两边同步靠
`lyco-model/DEMO_100rounds.md` §10-12 的实测结论：Wikipedia 已判死（本机出口全 403）、
verify 查的是 claim 不只是关键词重叠、DeepWiki 只重试限流、`-c` 会被 `-np` 按槽位拆分。
要动 core 前先读那三节，别把修过的洞再挖回来。

要把 core 搬进手机时先读 `docs/ON_DEVICE_PYTHON.md`：安卓只能嵌入式模式（没有
`python`/`pip`、`stdout` 进 logcat），子进程不被官方支持 —— 全仓库只有
`core/summarizer.py` 一处 `subprocess` 需要换成 JNI。
