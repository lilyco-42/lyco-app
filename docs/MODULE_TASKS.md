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
| mobile/ui | 中 | me | 中 | ✅ 已交付（RN 0.87 脚手架 + 聊天/地图双屏 + API 桩，tsc 干净，jest 2 suites / 5 tests 且切换有真断言；**但仍没上真机**，见复核记录 3；Cline 余额耗尽） |
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
| core（新增，无模型无网络） | 本次补 | `python test_core_offline.py` | 15 组 PASS（`python -m core.cli` 输出契约、rss 检索组、summarizer 组均为本次补，见记录 4、5） |
| services/poi | ✅ 7/7 | `python services/poi/test_poi.py` | 7 条 PASS，ALL PASSED |
| services/reviews | ✅ 5/5 | `python services/reviews/test_reviews.py` | 5 条 PASS，ALL PASSED |
| mobile/sensors | ✅ node:test 6/6 | `node --test mobile/sensors/test_permissions.mjs` | 6 pass / 0 fail |
| mobile/ui | ✅ tsc + jest | `npx tsc --noEmit`；`npx jest --ci` | tsc 退出码 0 无输出；jest 2 suites / 5 tests（复核时把模板那条空断言换成了真的双屏切换断言，见记录 3） |
| plugins/dsh-lyco-chat | 本次新增 | `node --test test_plugin.mjs` | 13 pass / 0 fail（含走真 python + stub CLI 的端到端两条） |

没有假声明，但五条必须说清：

1. `test_core.py` 依赖 `llama-cli` 和 `D:/gal/AliceInCradle/kb` 的本地文件，换机器必红。
   因此新增 `test_core_offline.py`（检索 stub、`summarize_fn` 注入），CI 跑这份；
   前者留作本机 smoke。
2. 环境里没装 pytest，services 的测试是脚本自带入口直接跑，不是 pytest 收集。
3. **mobile/ui 原来那条 jest 测试是空的，而且空得看不见。** 复核时把它当成
   "浅渲染一次、没断言" 就准备记完缺口，试着加一条断言才发现树里根本没东西：
   `App.test.tsx` 挂载后整棵树只有 `RNCSafeAreaProvider` 一个节点，`Text`、
   `Button`、两个屏的组件**一个都没渲染**。原因是
   `react-native-safe-area-context` 的 provider 要读 `RNSSafeAreaContext`
   原生模块，react-test-renderer 下没有，于是它把 children 整个吞掉；
   RN 0.87 模板自带的 `renders correctly` 因此在任何内容缺失下都绿。
   修法与验证：
   - 加 `mobile/app/__mocks__/react-native-safe-area-context.js`（node_modules 包的
     自动 mock，`SafeAreaProvider` 直接透传 children）；
   - `App.test.tsx` 换成三条真断言：默认停在聊天（`TextInput` 恰 1 个、地图屏的
     `搜身边 1km` 按钮不存在、当前 tab 按钮 disabled），按 `身边` 后地图屏挂载且
     聊天输入框消失，再按回 `聊天` 输入框回来；
   - 每条挂载前先过 `expectRealTree()`（≥2 个 Button、≥1 个 Text），这样
     "provider 又吞了 children" 以后会直接红而不是静默空过；
   - **反向对照**：把 mock 临时挪走，三条全红；放回后 `2 suites / 5 tests` 全绿。
     断言确实是承重的，不是装饰。

   仍未证明的：真机/模拟器上没人看过一眼。CI 的 android job 只证明 APK 建得出来，
   装过没有 = 没有。所以"双屏可用"现在是组件树级别的正确，不是视觉级别的正确。

4. **`core/retrievers` 那条 ✅ 原来漏了一半。** 三个检索出口里 deepwiki 有离线组，
   local 靠 `test_core.py` 的 `assert kb_hits`，而 **`rss.py` 在补测试之前整个仓库里
   一处都没有**（`grep -rn "rss" test_core.py test_core_offline.py` 当时为空）。
   表里的声明因此是过度声称。
   本次补了第 14 组 `rss: cache write/read/TTL, title weighting, html strip, anchor
   filter, error note`：假 client 注入 XML，验首取写盘、新鲜缓存不再走网、
   `RSS_TTL` 过期后重取、`score>=2 且必须命中锚点`（周报项被筛掉）、
   description 里的 `<p>` 被剥、`【RustCC:标题】… 来源:链接` 格式、
   以及失败路径返回 `([], ["rss-err: ..."])` 而不是抛异常。
   两条变异测试证明确实承重：删掉 `re.sub` 剥标签 → 红；把 `score_text(title) * 3`
   的权重去掉 → 排序断言红（fixture 特意让两条 item 的原始命中数相等，
   只有标题加权才分出先后）。
   仍未覆盖的：`rss_search` 从没真访问过 `https://rustcc.cn/rss`（CI 也不联网），
   所以真 feed 的命名空间/编码意外情况只有线上才知道；`local.py` 的测试仍只在
   本机那份需要 kb 目录的 smoke 里。
5. **`core/summarizer` 同样是 CI 完全没碰过的模块。** 离线套件过去用注入的
   `fake_summarize_fn` 把它整个绕过，`test_core.py` 那条又只在装了 `llama-cli`
   的本机跑。本次补第 15 组（假 `subprocess.run`）锁住它的实际行为：argv 里
   `-m <model>`、`-n 256`、`--single-turn`、`--no-display-prompt`、`timeout=180`；
   三种 prompt 分支（有证据 / 搜过但空 / 纯 direct 原样透传）；回显解析
   （`> prompt` 标记、`(truncated)` 尾切、`[Prompt:` 与 `Exiting...` 截尾）；
   `Generation: 24.9 t/s` → `gen_ts`；gbk 回显能解码；非零 `rc` 如实透传；
   `LYCO_LLAMA_CLI` / `LYCO_CHAT_MODEL` 覆盖生效。
   两次变异各红一次：`-n 256`→`128` 断言红；关掉 `(truncated)` 分支后
   `response` 里混进 banner 与 `...(truncated)` 也红。

   **但这组锁的是现状不是理想形态。** 期望值是我按现有解析写的，真实
   `llama-cli` 的回显格式只有本机 `test_core.py` 证明过；而 lyco-model §10 的
   结论恰恰是"回显解析整段应当删掉，改用 `llama-server` 的 messages"。迁到
   server 时要连这组解析断言一起删，别把它当成要长期守的契约。

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
修好的五次全绿（HEAD 与产物都从 API 反查，每个 run 都从 job log 里取实际输出行，不看绿勾）：

| run | HEAD | job 数 | log 里的证据 |
|-----|------|--------|-------------|
| 36729302532 | `c28deae` | 3（还没有 plugin） | python + mobile + android 全 success，APK 39,614,181 字节 |
| 36730689189 | `c5b6805` | 4 | 加上 plugin job（Linux + `LYCO_PY=python3` + node 24），13 项插件测试通过，APK 39,614,176 字节 |
| 36732136945 | `d3ae4f1` | 4 | `13 groups PASSED`、poi/reviews `ALL PASSED`、jest 3、sensors `# pass 6`，APK 39,614,174 字节 |
| 36732927196 | `1cbe70d` | 4 | 四 job 全 success，APK 39,614,173 字节 |
| 36733562274 | `4cb84e7` | 4 | `13 groups PASSED`、poi/reviews `ALL PASSED`、**jest `Tests: 5 passed`**（safe-area 自动 mock 在 Linux 上同样生效）、sensors `# pass 6 / # fail 0`、插件 `ℹ tests 13 / pass 13 / fail 0`、APK 39,614,178 字节（Artifact ID 11106012318） |

**APK 字节数不是 pin**：五次构建落在 39,614,173 ~ 39,614,181 这 9 字节区间里，
而中间几次只改了 markdown 或测试（zip 里的时间戳/顺序不进内容哈希）。这个数只证明
"产物真的建出来并上传了"，不要拿它当回归基线。

CI 从没证明的事：APK 只构建、没安装。整个仓库目前没有任何一层跑过真机或模拟器。

## 关于 deepseek-harness 的一个坑

它默认分支是 **`master`**。上一轮 AI 用 `main` 去请求 `contents/docs/development.md`
和 `contents/apps/desktop`，一直 404，然后重复发同一条命令直到卡死循环。
本次先 `GET /repos/...` 读 `default_branch` 再取路径，一次就拿到了插件契约。
