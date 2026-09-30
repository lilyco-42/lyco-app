# lyco-app AGENTS.md — 所有 AI 必读

## 铁律

1. **不本机编译**：`.so` / APK / 二进制构建一律走 GitHub Actions（参考 huzpsb/llama_cpp_android_ci
   模式）。本机只跑 Python 逻辑测试，绝不在本机跑 ndk-build / cargo-ndk / gradle assemble。
2. **先调研再动手**：沿用 lyco-skill（预研先行 + OODA），新模块先 gh 搜现成方案。
3. **模型与大文件不进 git**：`*.gguf`、`.cache/`、`__pycache__/` 已忽略；模型走 HF 下载。
4. **core 不依赖 mobile**：双向只经过 services 函数接口（见 docs/ARCHITECTURE.md）。

## 模块分工

见 `docs/MODULE_TASKS.md`（难度 / 负责人 / 耦合度）。
Cline 派单用免费模型（当前：`z-ai/glm-5.3-flash`），单子必须带验收标准。
