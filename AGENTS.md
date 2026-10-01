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

本机 `python` 有可能解析到 scoop 的 uv shim（3.11，**里面没装 httpx**），
那份解释器跑 `test_core_offline.py` / `services/poi/test_poi.py` 会在 import 处就
`ModuleNotFoundError: No module named 'httpx'` —— 不是代码坏了。换一个装了 httpx 的解释器
（实测 `D:/app/scoop/apps/python/current/python` = 3.14.7 + httpx 0.28.1 全绿）或先 `pip install httpx`；
CI 侧由 workflow 里的 `pip install httpx` 负责。

改过 `mobile/app/package.json` 或 lock 之后，**必须再跑一次干净安装**再提交：
本机 npm 是 11，CI 是 node 22 自带 npm 10，两者对 lock 的严格程度不同，
只有 `rm -rf node_modules && npx npm@10 ci` 过了才算同步（npm 11 会放过 npm 10 拒绝的树）。

Android/APK 只在 CI 构建：`.github/workflows/ci.yml`
（python → mobile → plugin → preview → android，外加两个 dispatch-only 的：device
当前账号调度不了、device-dry 是它不依赖 KVM 的那几步）。

**像素真相在本机模拟器，不在 CI。** CI 的 `device` job 要 GitHub *larger runner*
（Linux + `/dev/kvm`），而文档写明 larger runners 只对 Team / Enterprise Cloud 的
**组织**开放，本仓库属于个人账号 —— 那个 job 是"哪天搬进 org 就能用"的现成配置，
从未运行验证过。别再去试 standard runner：**Linux** 没有 `/dev/kvm`；**macOS**
上 `emulator -accel-check` 会退出 0 假装可用，真启动却是
`HVF error: HV_UNSUPPORTED`（runner 自己就是 `VirtualMac2,1` 虚拟机，没有嵌套虚拟化）。
要看真机像素：

```powershell
# 前提：APK 由 CI 出（gh run download -n lycoapp-debug -D <tmp>），本机绝不跑 gradle
# device job 里不依赖 KVM 的那几步可以先在标准 runner 上真跑一遍（下载产物、验 bundle、
# 门禁脚本能起来且无设备时干净退出）：
#   gh workflow run ci.yml --ref main -f dry_run_device=true
# 剩下的模拟器启动本身，这台账号调度不了。
$env:LOCALAPPDATA\Android\Sdk\emulator\emulator.exe -avd lyco-preview -no-window `
  -no-audio -no-boot-anim -no-snapshot-save -gpu swiftshader_indirect   # 起机约 80s
cd mobile/app; npx react-native start                       # debug APK 不带 bundle，必须有 Metro
python scripts/device_ui_check.py <tmp>/app-debug.apk <out>  # 8 条断言 + 三张 PNG
```

AVD `lyco-preview`（android-36 / x86_64，占 ~6 GB）的建立命令在
`docs/MODULE_TASKS.md`「B 段：模拟器像素真相」。

`device_ui_check.py` 断言的是"两个 tab 并排、tab 顶边落在状态栏带以下、输入框底边落在
导航条带以上、点 tab 真能换屏、键盘弹起时 composer 不被 IME 埋掉"。三条单独反向验过：
退回 `App.tsx` 红 4 条，退回 `ChatScreen.tsx` 只红键盘那条，把 dump 里第二个 tab 的
bounds 改写成"竖着堆"则并排那条判 False（证明不是永真式）。
CI 的 `android` job 在 dispatch 时还会多出 `lycoapp-release`：只有 release 变体把
`assets/index.android.bundle` 打进 APK（debug 变体连 `assets/` 都没有），构建后有一步
python 断言 bundle 真在里面。**已实测**这个包能脱离 dev server 跑：Metro 杀掉、
`adb reverse --remove-all` 之后装它，8 条断言全绿（含键盘和并排那两条）。所以想手动看 UI，
`gh run download -n lycoapp-release` + 起模拟器 + 跑脚本就够了，不用起 Metro。
改 UI 时日常看 `storybook-preview`（每次 push 都出），要 Android 像素再走上面这两条命令。
上一次 8/8 的三张图已经提交在 `docs/screens/android/`，所用 APK 的 CI run id 和 sha256
记在 `docs/MODULE_TASKS.md`「B 段」，不必为了"看看长什么样"再开模拟器。
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
