# lyco-app 上层规划：项目结构与模块拆分

原则：高内聚低耦合。core 不依赖 mobile；services 只暴露函数接口；
models/assets 只读挂载；各模块可独立测试、独立替换。

```
lyco-app/
  mobile/                 # RN 安卓（首期）
    ui/                   # chat 页、地图页、权限申请页
    inference/            # 端侧 GGUF（llama.cpp .so，抄 PocketPal 接入）
    sensors/              # 定位/相机/麦克风/通知封装
  plugins/
    dsh-lyco-chat/        # 官方 DSH 桌面插件（已最小交付：2 个工具 + 13 项测试）
  core/                   # 与端无关，可被 mobile/desktop 共用
    router/               # 搜 vs 直答（关键词规则，不用模型判）
    retrievers/           # local kb / RSS / DeepWiki MCP（维基已删，本机出口全 403）
    summarizer/           # chat-slm，只做总结
    verify/               # claim 级：数字/单位声明必须有证据 + 认不知道
    action/               # 后期：AutoGLM 模式读屏操作（无障碍）
    cli.py                # python -m core.cli：一个 JSON 对象，给插件/脚本调用
  services/
    poi/                  # 高德 place/around + place/detail
    reviews/              # site: 搜索聚合 → 复用 rag_loop.py
  docs/                   # PERMISSIONS.md / 本规划
```

## 需求 → 模块映射

| 需求 | 模块 | 复用来源 | 接口 |
|------|------|----------|------|
| 聊天 | mobile/ui + core/summarizer | chat-slm GGUF，抄 PocketPal UI | `answer(text) -> text` |
| OODA 结构化任务 | core（+agent 模型） | ooda_sys.txt，lyco-agent GGUF | `act(task) -> Observe..Re-observe` |
| 1km 洗发店列表 | sensors/location + services/poi | 高德 place/around | `nearby(lat,lng,radius,type) -> POI[]` |
| 哪家好 | services/reviews + core | rag_loop.py | `rank_shops(POI[]) -> 排序+理由` |
| 读小红书评论 | core/action（后期） | Open-AutoGLM 模式 + 无障碍 | `read_screen(app) -> 文本` |
| 桌面端 | plugins/dsh-lyco-chat | 官方 DSH apps/desktop | DSH 插件 API |
| 角色形象 | assets（只读） | lyco-ip/design | 头像/壁纸/表情 |

## 耦合红线

1. core 不 import mobile/desktop 任何东西；双向只经过 services 函数接口
2. 模型文件永远只读挂载，不进 git（见 lyco-model/.gitignore 实践）
3. 新增数据源只加 retrievers/ 下一个文件 + source_order 一行，不碰 router/summarizer
4. 动作层（action/）默认关闭，需用户显式开启 + 无障碍授权后才加载
