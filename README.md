# lyco-app

Lyco AI 随身助手：手机端 + 桌面端，端侧 GGUF 推理，用系统权限扩展 AI 能力（定位 → POI → 口碑），触及真实生活。

## 一句话需求

把 `lyco-model`（端侧小模型 + RAG 闭环）和 `lyco-ip`（角色资产）装进一个手机 App，
尽可能多拿系统权限，让 AI 能回答"我身边 1km 有几家洗发店，哪家理发好"这类问题。

## 架构

```
mobile (React Native, 首期) ── PocketPal 模式：端侧 GGUF + 系统权限
desktop (Tauri + Rust, 二期) ── 复用 Rust 生态（lilyco / Lazy-UI）
core (Python/Rust) ── rag_loop.py：router → 检索 → chat 总结 → verify
```

## 技术决策（lyco 预研结论）

| 候选 | fit | 结论 |
|------|-----|------|
| RN + 端侧 GGUF（a-ghorbani/pocketpal-ai 模式） | 手机+端侧+权限，一套代码 | ADOPT（手机端） |
| 原生 Android Java（weaktogeek） | 单端，维护 ×2 | 参考实现 |
| Tauri mobile | 移动端生态不成熟 | 不用；桌面端再用 Tauri |
| 云 API 克隆类 RN App | 与端侧定位冲突 | 不用，只抄 UI |
| 高德 Web Service（周边搜索+详情） | 官方 POI，免费 15 万次/月 | ADOPT（POI 数据源） |
| 小红书/贴吧/快手/QQ墙直爬 | 无公开 API + 反爬 + 登录墙 | 不做；用 site: 搜索聚合（已有 rag_loop 模式） |

关键限制（实测得出）：高德 `rating` 只返餐饮/酒店/景点/影院四类——
理发店没有评分。所以"几家店"走高德 POI，"哪家好"走搜索聚合 + chat 总结。

## 动作层（新增，autoglm 路线）

- 采用 zai-org/Open-AutoGLM（★26k，Apache-2.0，官方开源手机 agent 模型+框架）为动作层参考：
  截图/UI 树 → 模型决策 → 无障碍服务执行
- 这才是"调用小红书评论"的合法解：不调 API（没有）、不爬虫（被封），
  而是让端侧 agent 像用户一样打开 App 读屏。无障碍权限正是为此拿的
- 双层架构：知识层（RAG 搜索聚合，现有 `rag_loop.py`）+ 动作层（AutoGLM 模式读屏操作）
- Ruto-GLM（纯端侧后台自动化）做备选参考；注意它无 license 声明，代码只借鉴不引入

## 权限清单

见 `docs/PERMISSIONS.md`。原则：侧载优先（SMS/通话记录类权限上架会被拒）。

## 复用资产

见 `core/README.md`。模型（`lyco42/*-0.6b` GGUF）、`rag_loop.py`、lyco-ip 角色资产。

## 范围决议（已确认）

- 手机端先安卓（侧载，权限全开）；iOS 后续再议
- 口碑走站内搜索聚合，不直爬小红书/贴吧/快手/QQ墙（无公开 API + 反爬）
- 桌面端 Tauri 为二期（暂定）

## 路线图

1. RN 空壳 + 端侧模型跑通（PocketPal 抄作业）+ 聊天页
2. 定位权限 + 高德周边搜索（1km 洗发店列表）
3. 口碑聚合（site: 搜索 → chat 总结 → 哪家好）
4. 相机/麦克风/通知权限接入
5. Tauri 桌面端
