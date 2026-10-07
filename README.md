# lyco-app

Lyco AI 随身助手：手机端 + 桌面端，端侧 GGUF 推理，用系统权限扩展 AI 能力（定�?�?POI �?口碑），触及真实生活�?

## 一句话需�?

�?`lyco-model`（端侧小模型 + RAG 闭环）和 `lyco-ip`（角色资产）装进一个手�?App�?
尽可能多拿系统权限，�?AI 能回�?我身�?1km 有几家洗发店，哪家理发好"这类问题�?

## 架构

```
mobile native (React Native, 首期) ── PocketPal 模式：端�?GGUF + 系统权限
desktop (官方 DSH desktop, 二期) ── deepseek-ai/deepseek-harness 自带 apps/desktop（★240k，MIT，第一方插�?API），lyco_chat 以官方插件形态接入；不再用第三方 dsh-desktop
bridge (参�? ── dsh-pocket 手机扫码同步（GPL-2.0，只借鉴不引入）
core (Python/Rust) ── rag_loop.py：router �?检�?�?chat 总结 �?verify
```

## 技术决策（lyco 预研结论�?

| 候�?| fit | 结论 |
|------|-----|------|
| RN + 端侧 GGUF（a-ghorbani/pocketpal-ai 模式�?| 手机+端侧+权限，一套代�?| ADOPT（手机端�?|
| 原生 Android Java（weaktogeek�?| 单端，维�?×2 | 参考实�?|
| Tauri mobile | 移动端生态不成熟 | 不用；桌面端再用 Tauri |
| �?API 克隆�?RN App | 与端侧定位冲�?| 不用，只�?UI |
| 高德 Web Service（周边搜�?详情�?| 官方 POI，免�?15 万次/�?| ADOPT（POI 数据源） |
| 小红�?贴吧/快手/QQ墙直�?| 无公开 API + 反爬 + 登录�?| 不做；用 site: 搜索聚合（已�?rag_loop 模式�?|

关键限制（实测得出）：高�?`rating` 只返餐饮/酒店/景点/影院四类—�?
理发店没有评分。所�?几家�?走高�?POI�?哪家�?走搜索聚�?+ chat 总结�?

## 动作层（新增，autoglm 路线�?

- 采用 zai-org/Open-AutoGLM（★26k，Apache-2.0，官方开源手�?agent 模型+框架）为动作层参考：
  截图/UI �?�?模型决策 �?无障碍服务执�?
- 这才�?调用小红书评�?的合法解：不�?API（没有）、不爬虫（被封）�?
  而是让端�?agent 像用户一样打开 App 读屏。无障碍权限正是为此拿的
- 双层架构：知识层（RAG 搜索聚合，现�?`rag_loop.py`�? 动作层（AutoGLM 模式读屏操作�?
- Ruto-GLM（纯端侧后台自动化）做备选参考；注意它无 license 声明，代码只借鉴不引�?

## 权限清单

�?`docs/PERMISSIONS.md`。原则：侧载优先（SMS/通话记录类权限上架会被拒）�?

## 怎么看界面（两条 lane，都不用等真机）

- **设计态（浏览器，react-native-web�?*：`cd mobile/app && npm run storybook`
  �?http://localhost:6006 ，三�?story �?`App Root / ChatTab`、`Screens / Chat`�?
  `Screens / Nearby`；CI 每次 push 也构建整站并传成 `storybook-preview` 产物�?
- **Android 真像素（本机模拟器跑 CI 出的 APK�?*�?
  `gh run download -n lycoapp-release -D <tmp>` �?起模拟器 �?
  `python scripts/device_ui_check.py <tmp>/app-release.apk <out>`�? 条断言 + 三张 PNG）�?
  release 包自�?JS，不用起 Metro。命令与实测数字�?`docs/MODULE_TASKS.md`「B 段」，
  三张实测截图已在 `docs/screens/android/`�?

两条 lane 各自的坑与已抓到的两个设备级 bug（tab 栏被状态栏吃掉、键盘埋掉输入框）都记在那里�?

## 复用资产

�?`core/README.md`。模型（`lyco42/*-0.6b` GGUF）、`rag_loop.py`、lyco-ip 角色资产�?

## 范围决议（已确认�?

- 手机端先安卓（侧载，权限全开）；iOS 后续再议
- 口碑走站内搜索聚合，不直爬小红书/贴吧/快手/QQ墙（无公开 API + 反爬�?
- 桌面�?Tauri 为二期（暂定�?

## 路线�?

1. RN 空壳 + 端侧模型跑通（PocketPal 抄作业）+ 聊天�?
2. 定位权限 + 高德周边搜索�?km 洗发店列表）
3. 口碑聚合（site: 搜索 �?chat 总结 �?哪家好）
4. 相机/麦克�?通知权限接入
5. 桌面端以官方 DSH 插件形态接入（deepseek-ai/deepseek-harness/apps/desktop；dsh-pocket 只借鉴，GPL-2.0 不引入）
