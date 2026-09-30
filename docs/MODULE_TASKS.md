# 模块分工：难度 / 负责人 / 耦合度

负责人：`cline` = Cline CLI（`z-ai/glm-5.3-flash` 免费模型）；
`me` = 主控（Sisyphus）。耦合度指该模块对外的依赖面。

| 模块 | 难度 | 负责人 | 耦合度 | 说明 |
|------|------|--------|--------|------|
| core/router | 低 | cline | 低 | ✅ 已交付（test_core 通过） |
| core/retrievers | 低 | cline | 低 | ✅ 已交付 |
| core/summarizer+verify | 低 | cline | 低 | ✅ 已交付 |
| services/poi | 低 | cline+me | 低 | ✅ 已交付（cline 写架子，me 补完测试，7/7 通过） |
| services/reviews | 中 | cline | 中 | ✅ 已交付（5/5 通过，answer_fn 可注入） |
| mobile/sensors | 中 | me | 低 | ✅ 已交付（bridge 可注入，node:test 6/6，无 RN 依赖） |
| mobile/ui | 中 | me | 中 | ✅ 已交付（RN 0.87 脚手架 + 聊天/地图双屏 + API 桩，tsc 干净，jest 2 suites / 3 tests；Cline 余额耗尽） |
| plugins/dsh-lyco-chat | 中 | me | 中 | ✅ 最小交付（`lyco_ask` + `lyco_nearby_shops` 两个工具走 `python -m core.cli`，用真 `defineTool` 构造，`npm test` 13/13；**真在 Harness 里加载未验证**，本机没有 dsh 仓库检出，见 plugins/dsh-lyco-chat/README.md） |
| mobile/inference | 高 | me | 中 | JNI/.so，真机验证跑不掉。端侧 Python 可行性已审计完 → `docs/ON_DEVICE_PYTHON.md`（唯一阻塞点是 `core/summarizer.py` 那一处 `subprocess`；建议 Chaquopy 装解释器 + 自带 llama.cpp `.so`） |
| core/action | 高 | 后期 | 高 | 无障碍 + AutoGLM，门控，默认关闭 |

派单规则：低难度低耦合先行；cline 单子必须带验收标准（测试通过）；
高难度/高耦合不派，攒到主控手里。

---

## 复核记录（2026-09-30，本机逐条实跑）

| 模块 | 表里的声明 | 命令 | 实测结果 |
|------|-----------|------|----------|
| core/router / retrievers / summarizer / verify | ✅ test_core 通过 | `python test_core.py` | 2 题 ALL PASSED；Q1 verify `overlap=2, on_topic=True`，Q2 `direct` |
| core（新增，无模型无网络） | 本次补 | `python test_core_offline.py` | 12 组 PASS |
| services/poi | ✅ 7/7 | `python services/poi/test_poi.py` | 7 PASS，ALL PASSED |
| services/reviews | ✅ 5/5 | `python services/reviews/test_reviews.py` | 5 PASS |
| mobile/sensors | ✅ node:test 6/6 | `node --test mobile/sensors/test_permissions.mjs` | 6 pass / 0 fail |
| mobile/ui | ✅ tsc + jest | `npx tsc --noEmit`；`npx jest` | tsc 无输出；jest 2 suites / 3 tests |

没有假声明，但两条必须说清：

1. `test_core.py` 依赖 `llama-cli` 和 `D:/gal/AliceInCradle/kb` 的本地文件，换机器必红。
   因此新增 `test_core_offline.py`（检索 stub、`summarize_fn` 注入），CI 跑这份；
   前者留作本机 smoke。
2. 环境里没装 pytest，services 的测试是脚本自带入口直接跑，不是 pytest 收集。

## 今日从 lyco-model 同步进 core 的（依据见 lyco-model/DEMO_100rounds.md §10-12）

- **Wikipedia 判死**：`core/retrievers/wiki.py` 删除，`source_order()` 不再含 wiki。
  7 种出口（项目 UA / 浏览器 UA / 空 UA / REST summary / `action=query` / 英文站）
  全 403，绕开代理直连超时 —— `lyco-model/results/source_probe.json`。
- **verify 从"关键词交集"升级**：带精度含义的数字（小数 / 百分比 / ≥3 位 /
  **任何粘着单位的数字**）必须在证据里以 token 形式出现，`UINT8` 不再能背书 "8-bit"，
  `400MB` 能支持 "400 MB"，`12.5` 不因 `112.55` 蒙混；无证据时接受 DECLINE 短语族而不是
  字面"不知道"；direct 轮也查发明数字；`hits` sorted 以保证记录可重放。
- **router 补洞**：`needs_evidence()` 增加 PREDICTION_CUES（缺点/影响/会不会…）、
  REFERENTIAL 指代、以及"有 topic 时带 吗 的问句"三类触发；"量化有什么缺点？"不再走
  direct 免检，而"给我讲个笑话"必须仍是 direct（测试锁住）。
- **DeepWiki 限流**：只重试限流（确定性 2s→4s 退避，无随机抖动），真错误一次即返回；
  HTTP 200 body 里的上游报错文本不再被当成证据。
- **summarizer 可迁移**：`LYCO_LLAMA_CLI` / `LYCO_CHAT_MODEL` 环境变量覆盖；docstring 记了
  `-np` 会把 `-c` 按槽位拆分这件事（`-np 4 -c 8192` → 每槽 2048，长 prompt 直接 HTTP 400）。

**还没同步的**：证据缓存与多轮记忆仍在 lyco-model 一侧（`Conversation`、
`results/evidence_cache.json`）。移动端接的时候先读 §10（回显解析整段删掉、改用
`llama-server` 的 messages 才是正解），别在 `llama-cli --single-turn` 上加记忆。

## CI

`.github/workflows/ci.yml`：`python`（离线 core + 两个 services）→
`mobile`（tsc / jest / sensors）→ `plugin`（DSH 插件测试，node 24 + `LYCO_PY=python3`）
→ `android`（`./gradlew assembleDebug` + APK 产物）。
按铁律 1，本机不构建，Android 只在 CI 出。`gradlew` 从 Windows 提交时丢了执行位，
已在 git 索引里补成 `100755`，workflow 里另留一次 `chmod +x` 兜底。

首次推送 0 秒失败：step 名字里写了 `offline: no model` 这个冒号，YAML 直接解析失败，
GitHub 连 job 都没建（`gh run view --log` 只会说 log not found）。现在本地先
`python -c "import yaml; yaml.safe_load(...)"` 验一遍再推。
修好后两次全绿：run 36729302532（python / mobile / android，APK 产物 `lycoapp-debug`
39,614,181 字节）、run 36730689189（加上 plugin job，Linux + `LYCO_PY=python3` + node 24，
13 项插件测试同样通过）。

## 关于 deepseek-harness 的一个坑

它默认分支是 **`master`**。上一轮 AI 用 `main` 去请求 `contents/docs/development.md`
和 `contents/apps/desktop`，一直 404，然后重复发同一条命令直到卡死循环。
本次先 `GET /repos/...` 读 `default_branch` 再取路径，一次就拿到了插件契约。
