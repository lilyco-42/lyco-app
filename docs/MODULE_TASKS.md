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
| mobile/ui | 中 | me | 中 | ✅ 已交付（RN 0.87 脚手架 + 聊天/地图双屏 + API 桩，tsc 干净，jest 2 suites / 6 tests 且切换有真断言；已在 Android 36 模拟器上装跑并截图核对（见「B 段」），物理手机仍未跑；Cline 余额耗尽） |
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
| core（新增，无模型无网络） | 本次补 | `python test_core_offline.py` | 17 组 PASS（`python -m core.cli` 输出契约、rss 检索组、local kb 组、summarizer 组、`http()` 组均为本次补，见记录 4-6） |
| services/poi | ✅ 7/7 | `python services/poi/test_poi.py` | 7 条 PASS，ALL PASSED |
| services/reviews | ✅ 5/5 | `python services/reviews/test_reviews.py` | 5 条 PASS，ALL PASSED |
| mobile/sensors | ✅ node:test 6/6 | `node --test mobile/sensors/test_permissions.mjs` | 6 pass / 0 fail |
| mobile/ui | ✅ tsc + jest | `npx tsc --noEmit`；`npx jest --ci` | tsc 退出码 0 无输出；jest 2 suites / 6 tests（复核时把模板那条空断言换成了真的双屏切换断言，见记录 3；第 6 条是 B 段发现的 root inset，见「B 段」） |
| plugins/dsh-lyco-chat | 本次新增 | `node --test test_plugin.mjs` | 13 pass / 0 fail（含走真 python + stub CLI 的端到端两条） |

没有假声明，但六条必须说清：

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
   本次补了 rss 组：`rss: cache write/read/TTL, title weighting, html strip, anchor
   filter, error note`：假 client 注入 XML，验首取写盘、新鲜缓存不再走网、
   `RSS_TTL` 过期后重取、`score>=2 且必须命中锚点`（周报项被筛掉）、
   description 里的 `<p>` 被剥、`【RustCC:标题】… 来源:链接` 格式、
   以及失败路径返回 `([], ["rss-err: ..."])` 而不是抛异常。
   两条变异测试证明确实承重：删掉 `re.sub` 剥标签 → 红；把 `score_text(title) * 3`
   的权重去掉 → 排序断言红（fixture 特意让两条 item 的原始命中数相等，
   只有标题加权才分出先后）。
   仍未覆盖的：`rss_search` 从没真访问过 `https://rustcc.cn/rss`（CI 也不联网），
   所以真 feed 的命名空间/编码意外情况只有线上才知道。
   同一条口径接着把 `local.py` 也补成了离线组（local kb 组，临时 kb 目录）：扩展名只收
   md/markdown/txt/toml（一份同样命中的 `.py` 必须被排除）、`.git`/`node_modules`/
   `target` 被剪、`score>=2` 且必须有锚点、标签是相对路径 `【本地库:子目录+文件】`、
   命中片段 ≤500 字、`topn` 生效、kb 目录不存在时返回 `[]` 而不是抛异常。
   两次变异各红一次：把剪枝条件改成恒真 → `.git/hidden.md` 混进结果；
   扩展名白名单里加 `.py` → `c/tool.py` 混进结果。
   `local.py` 因此在 CI 里也有覆盖了，剩下的只是它在**真 kb 目录**上的表现
   仍只有本机 `test_core.py` 那份 smoke 证明过。
5. **`core/summarizer` 同样是 CI 完全没碰过的模块。** 离线套件过去用注入的
   `fake_summarize_fn` 把它整个绕过，`test_core.py` 那条又只在装了 `llama-cli`
   的本机跑。本次补了 summarizer 组（假 `subprocess.run`）锁住它的实际行为：argv 里
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
6. **给 `core/retrievers/__init__.py` 的 `http()` 补测试时抓到一个真的 Windows-only bug，
   已修。** 原顺序是先 `os.environ["NO_PROXY"] = "127.0.0.1,localhost"`
   再 `os.environ.pop("no_proxy", None)`。Windows 的 `os.environ` 大小写不敏感，
   第二行删掉的正是第一行刚写进去的那个键 —— 结果在本机上 `http()` 之后
   `NO_PROXY` 直接为空，绕开本地地址的意图完全没生效；Linux 上两个键不同，
   所以**这段代码在 CI 里永远是对的，只有本机测得出来**。
   修法就是把顺序反过来（先清小写，再写大写），两个平台都得到同一个结果。
   新增的 `http()` 组因此断言"环境里所有大小写形式的 no-proxy 合并后恰好等于
   `127.0.0.1,localhost`"，在 Windows 和 Linux 上都成立、都有效：
   把两行顺序还原回去，本机断言变成 `[]` 立即红；修正后 17 组绿。
   这条同时是对"只在 CI 上验证"的一次警告 —— 铁律 1 让构建走 CI，
   但平台差异只有本机这一份能暴露。
   **同一个 bug 在 `lyco-model/rag_loop.py` 里也存在，已一并修掉（`ecf31a6`）**，
   那边影响更实际：它每次都往本机的 `llama-server 127.0.0.1:8079` 发请求，
   在 Windows 上这些请求其实会走系统代理。修法相同（先 pop 再 set），
   本机验后 `test_retry` 7/7、`test_claims` 12/12 仍全过，
   且 `http()` 之后环境变量确实剩 `['127.0.0.1,localhost']`（修前是 `[]`）。

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
全绿记录（按提交顺序追加，**别在标题里写次数** —— 每次推送都会多一行，写死就是下一个
stale pin；核对方法：`gh run list --branch main` 取 id，`gh run view <id> --log` 取实际输出行）：

| run | HEAD | job | log 里的证据 |
|-----|------|-----|-------------|
| 36729302532 | `c28deae` | 3（还没有 plugin） | python + mobile + android 全 success，APK 39,614,181 字节 |
| 36730689189 | `c5b6805` | 4 | 加上 plugin job（Linux + `LYCO_PY=python3` + node 24），13 项插件测试通过，APK 39,614,176 字节 |
| 36732136945 | `d3ae4f1` | 4 | `13 groups PASSED`、poi/reviews `ALL PASSED`、jest 3、sensors `# pass 6`，APK 39,614,174 字节 |
| 36732927196 | `1cbe70d` | 4 | 四 job 全 success，APK 39,614,173 字节 |
| 36733562274 | `4cb84e7` | 4 | `13 groups PASSED`、poi/reviews `ALL PASSED`、**jest `Tests: 5 passed`**（safe-area 自动 mock 在 Linux 上同样生效）、sensors `# pass 6 / # fail 0`、插件 `ℹ tests 13 / pass 13 / fail 0`、APK 39,614,178 字节（Artifact ID 11106012318） |
| 36734675159 | `c6203a6` | 4 | 四 job 全 success（`N groups PASSED` 这个数会随补充的组一直变，各行只记当时值），APK 39,614,176 字节 |
| 36735218413 | `c0b955b` | 4 | 四 job 全 success，rss 检索组已进入 CI 跑的离线套件，APK 39,614,177 字节 |
| 36735766801 | `690dbcb` | 4 | `15 groups PASSED`（summarizer 组上 CI）、jest `Tests: 5 passed`、sensors `# pass 6`、插件 `ℹ tests 13`，APK 39,614,181 字节（ID 11107198666） |
| 36736149701 | `aad8a54` | 4 | `15 groups PASSED`、jest 5、sensors 6、插件 13、APK 39,614,174 字节（ID 11107540923） |
| 36737214110 | `dd1be42` | 4 | `16 groups PASSED`（local kb 组上 CI）、jest 5、sensors `# pass 6`、插件 `ℹ tests 13`、APK 39,614,180 字节（ID 11107269215） |

**APK 字节数不是 pin**：表里这几行落在 39,614,173 ~ 39,614,181 这 9 字节区间里，
而中间几次只改了 markdown 或测试（zip 里的时间戳/顺序不进内容哈希）。这个数只证明
"产物真的建出来并上传了"，不要拿它当回归基线。

CI 从没证明的事：APK 在 CI 里只构建、不安装。安装并运行发生在**本机 Android 模拟器**上，
见下面「B 段：模拟器像素真相」那节。

### `device` job（模拟器像素真相）三次尝试都红了，原因已定位

| 尝试 | run | 触发 | runner / 参数 | 结果 | 日志里的原话 |
|------|-----|------|--------------|------|-------------|
| 1 | 36752926806 | push | ubuntu-latest, API 33 x86_64 | 红（模拟器步骤超时） | `You're running a Linux VM where hardware acceleration is not available` → x86_64 AVD 软件模拟，600s 启动窗口内起不来 |
| 2 | 36757097391 | dispatch | macos-14, `arch: aarch64` | 红（0.6 秒，参数校验） | `Value for input.arch 'aarch64' is unknown. Supported options: x86,x86_64,arm64-v8a` |
| 3 | 36758175867 | dispatch | macos-14, `arm64-v8a` / API 30 | 红（约 20 分钟后） | `adb: device 'emulator-5554' not found` 刷屏 → `Timeout waiting for emulator to boot`，模拟器进程始终没注册到 adb |

已排除的：前面每一步都绿（npm ci / 装 Maestro / 下载 APK / 起 Metro / 传产物），
所以不是脚本或 JS 层的问题；本机 `react-native bundle --platform android` 也能出
900,847 字节的 bundle，Metro 喂包没问题。

**上一轮写的"larger runner 只要挂支付方式"这句是错的，现在更正。** GitHub 文档
"Who can use this feature?" 原文：larger runners *"only available for organizations and
enterprises using the GitHub Team or GitHub Enterprise Cloud plans"*
（<https://docs.github.com/en/actions/how-tos/manage-runners/larger-runners/use-larger-runners>）。
而本仓库属于**个人账号**：`gh api repos/lilyco-42/lyco-app --jq .owner.type` → `User`。
所以这不是钱的问题 —— 个人账号挂不挂支付方式都不在资格范围内，
`runs-on: ubuntu-24.04-16core` 在这种账号下不会有 runner 来接
（排队行为我没实测，实测到的只是上面这条资格限制）。

结论：`device` job 保留成"哪天仓库搬进 Team/Enterprise org 就能直接用"的现成配置
（Linux larger runner + `Enable KVM group perms` + x86_64 AVD + 带 bundle 的 release APK），
workflow 文件里已写明**它在当前账号下不可调度、因此从未运行验证过**。
真机像素改由本机模拟器出，见下一节。

**要让 CI 真的出像素，只有这三条路，都要你点头：**

| 路 | 代价 | 谁动手 |
|----|------|--------|
| 仓库搬进 org 并升 Team 计划（按人月计费） | 唯一"官方"解，`device` job 现成可用 | 你建 org + 挂卡 + transfer |
| 第三方带安卓模拟器的 CI（Codemagic / Cirrus RUNS-On 等） | 另开账号、另一套配额与日志 | 你注册并授权 |
| 本机挂一个 self-hosted runner | 免费，但要常驻第三方进程 + 注册 token，且吃你这台机器的资源 | 你确认后我再装 |

标准 `ubuntu-latest` 与 macOS runner 都不行（前者无 `/dev/kvm`，后者实测起不来），
软件模拟（TCG）在 45 分钟窗口内也起不来，所以不是"再调调参数"能解决的。

## 界面预览（A 段：react-native-web，采用现成方案）

之前唯一能"看"的手段是我手搓的 HTML：把 `react-test-renderer` 的组件树翻成 CSS。
它**看着对但会骗人**，所以换成了 Storybook 的 `@storybook/react-native-web-vite`
（10.6.0）+ `react-native-web`（0.21.3），peer 核对过我们这套：
RN ≥ 0.74.5 ✓、react ^19 ✓、vite ^7 ✓。GitHub 上先例充分（22k★、MIT、本月还在推），
没有自研理由。

命令与产物：

```bash
cd mobile/app && npm run storybook:build   # -> storybook-static/（已 gitignore）
cd mobile/app && npm run storybook         # 本机 http://localhost:6006 边改边看
```

CI 的 `preview` job 跑同一条 build，并**断言三条 story id 都在**
（`app-root--chat-tab` / `screens--chat` / `screens--nearby`），产物整站上传成
`storybook-preview`。第一次 CI 绿是 run 36752926806；把该 run 的产物下回来解包核过：
`index.json` 里正是那三条 id，`assets/*.js` 里能搜到 `地图占位`、`问 Lyco 点什么`、
`搜身边` 和 `react-native-web`，说明 Linux 上构建出来的确实是这两屏。

本机实测（chrome headless 出图 + `getBoundingClientRect` / `getComputedStyle` 量 DOM，
量的是 `app-root--chat-tab` 与 `screens--nearby` 两条 story）：

| 量到的东西 | 真渲染的值 |
|-----------|-----------|
| 地图占位块 | h=**180** w=366 bg=`rgb(229,231,235)` radius=8 |
| 启用 tab「身边」 | `<button disabled=false>` bg=`rgb(33,150,243)`，白字，h=36 w=44，radius=2 |
| 禁用 tab「聊天」 | `<button disabled=true>` bg=`rgb(223,223,223)`，文字层 `rgb(161,161,161)`（外层写的是 `rgba(16,16,16,.3)`，合成后是 #a1a1a1） |
| 聊天输入框 | `<input>` 本体 h=**40** w=328（borderTop 0.8px、radius 8、paddingBottom 10），composer 行 h=48 w=366，屏幕容器 h=844 + padding 12 |
| 两屏内容 | 底边都在 390×844 框内（overflow −1px） |

（这一行原来写的是"外层盒 h=46"，那个数**是错的**：A/B 重测（把 `ChatScreen.tsx` 退回加
`KeyboardAvoidingView` 之前重建一次 preview）显示新旧两版都是 input 40 / 行 48 / 容器 844，
加 KAV 只多了一个 div（37→38），**没有任何几何变化**。）

注意 goal 里写的"禁用态 `#cdcdcd`"是**手搓 HTML 那版**的说法（我照抄了 RN 默认的
`color: '#cdcdcd'` 猜测），真渲染下 RNW 走的是 Material 配色 `#dfdfdf`/`#a1a1a1`。
这正是要用真组件而不是近似图的理由。

它立刻抓到两件手搓 HTML 永远看不出来的事：

1. **`RN <Button>` 的文案会被强制大写**：真图上是「搜身边 1**K**M」。
   RNW 和 Android 原生都做 textAllCaps，所以**真机也一样** —— 我之前的假图画成了
   蓝色纯文本，这就是"感觉有点歪"的直接来源。要不要改文案（比如写"1 公里"）是产品决定，
   我只把它记在这里，不擅自改用户可见文案。
2. **Windows 上 `import App from './App'` 解析到的是 `app.json`，不是 `App.tsx`**
   （文件系统大小写不敏感 + vite 的扩展名解析）。Storybook 于是把一个 JSON 对象当组件挂载，
   报 `Element type is invalid ... got: object`，而报错里那句
   `hookified` 是 Storybook preview runtime 的内部函数名，**完全指不到真凶**。
   定位方法：把 App 的 JSX 一件件拆开各写一条 story 逐个 dump DOM 比对，
   再直接打印 `Object.keys(App)` —— 得到 `[name, displayName]`，正是 app.json 的两个键。
   修法：写全扩展名 `./App.tsx`。

边界（照写）：`react-native-safe-area-context` 没有 web 入口，`.storybook/main.ts`
用 `enforce: 'pre'` 的 vite 插件把它别名到一个零 inset 的透传 shim，
**只有预览 lane 用得到**，RN 应用和 jest lane 仍走真包。
另外别在 `main.ts` 里找 `react-native → react-native-web` 那条别名 —— **它不在我们仓库里**，
是框架自带的 `vite-plugin-rnw` 提供的（`node_modules/@storybook/react-native-web-vite/node_modules/vite-plugin-rnw/dist/index.mjs`
里就是 `alias: { "react-native": "react-native-web" }`）。自己再写 `resolve.alias` 会被它覆盖，
所以 shim 只能用 `enforce: 'pre'` 的插件（当时验证过：普通 alias 下运行时探针是 `shim=NO`）。
RNW 给的是布局真相，不是 Android 皮肤真相：按钮、字体度量、滚动条仍是浏览器样式；
真机像素由下面「B 段：模拟器像素真相」负责。

## B 段：模拟器像素真相（本机 AVD 跑 CI 出的 APK）

**回答"android ok?"：现在 ok —— 但它是带着两条真 bug 被发现的，而且两条都是 web 预览原理上看不见的。**

CI 出不了像素（上一节），所以这条路换成本机：APK 仍然由 GitHub Actions 构建（铁律 1 不动），
本机只**运行**、不编译。机器上本来就装着 Android SDK
（`%LOCALAPPDATA%\Android\Sdk`，`emulator -accel-check` → `WHPX(10.0.26200) is installed and usable`），
新建了专用 AVD `lyco-preview`（android-36 / google_apis_playstore / x86_64 / pixel_7），
没动用户原有的 AVD。顺带发现原有 AVD `susong35` 在 `avdmanager list avd` 里是
"could not be loaded" 状态 —— 与本项目无关，我没碰它。

命令（本机，从零到截图）：

```powershell
$SDK = "$env:LOCALAPPDATA\Android\Sdk"
echo no | & $SDK\cmdline-tools\latest\bin\avdmanager.bat create avd -n lyco-preview `
  -k "system-images;android-36;google_apis_playstore;x86_64" -d pixel_7
& $SDK\emulator\emulator.exe -avd lyco-preview -no-window -no-audio -no-boot-anim `
  -no-snapshot-save -gpu swiftshader_indirect          # WHPX 下实测约 80s 起机
cd mobile/app; npx react-native start                  # debug APK 不带 bundle，必须有 Metro
gh run download -n lycoapp-debug -D <tmp>              # 取 CI 产物，不在本机 gradle
python scripts/device_ui_check.py <tmp>\app-debug.apk <out>
```

`scripts/device_ui_check.py` 是**门禁**不是截图脚本：它把 uiautomator 量到的真实坐标
和窗口管理器自己报的 system bar 区域对起来，7 条断言（tab 数量、tab 顶边 ≥ 状态栏下沿、
点第二个 tab 真能换屏、地图屏内容、点回第一个 tab、输入框底边 ≤ 导航条上沿、
键盘弹起时 composer 底边 ≤ IME 上沿）。
实测（1080×2400 @420dpi，density 2.625）：

| 量到的东西 | 修 bug 前 | 修 bug 后 |
|-----------|----------|----------|
| 状态栏占的带 | y=0..136 | 同 |
| 导航条占的带 | y=2337..2400 | 同 |
| 两个 tab Button 顶边 | **y=21**（整条在状态栏底下） | y=157 |
| 点 tab 中心 (216,69) | 没反应（触摸被状态栏窗口吃掉） | 换屏成功 |
| 聊天输入框底边 | **y=2370**（压进导航条带 33px） | y=2307 |
| 地图占位块高 | — | 472px = **179.8dp**（源码写 180） |
| 启用按钮底色 | — | `#2196f3`，与 A 段 RNW 量到的 `rgb(33,150,243)` **一致** |
| 禁用按钮底色 | — | `#dfdfdf`，与 A 段 RNW 量到的 `rgb(223,223,223)` **一致** |

**它抓到的 bug 是 web 预览原理上看不见的**：RN 0.87 模板默认 `edgeToEdgeEnabled=true`，
而 `App.tsx` 根节点是普通 `<View>`，没有任何 inset，于是整条 tab 栏画进状态栏底下 ——
不只是难看，是**点不动**（那块区域的触摸归状态栏窗口）。Storybook / RNW 那条 lane
没有状态栏，A 段全绿也照不出它。修法：根容器换成 `react-native-safe-area-context` 的
`SafeAreaView edges={['top','bottom']}`（`SafeAreaProvider` 早就包着了，只是没人用它的视图）。

**这条门禁真能挡吗 —— 反向验过。** 把 `App.tsx` 退回改前版本再跑，6 条红 4 条，
且红在正确的原因上：`tab bar is under the status bar: tabs top y=21/21 < status bar bottom
y=136`、`tapping the second tab did not switch screens`、`chat input is under the nav bar:
bottom y=2370 >= 2337`；改回来 6/6 绿。**过程中还修掉门禁自己的一个假绿**：第一版脚本在
`force-stop` 之后立刻 dump，读到的是**正在死掉的旧窗口**那棵树，于是旧坐标被当成新渲染，
pre-fix 源码上它居然报"tabs start at y=157 正常"。现在先等 `mCurrentFocus` 不再是本 app，
再等连续两次 dump 完全一致才判 —— 才拿到上面那条正确的红。

**第二条设备级缺陷：键盘一弹出来，输入框整个被埋掉。** 点输入框后 IME 占 y=1517..2400，
而 composer 还停在 y=2197..2307，全在键盘底下 —— 真图上看就是打字打盲了（候选栏显示 "hello"，
app 的输入行已经看不见了）。清单里 `windowSoftInputMode="adjustResize"` **本来就有**，
但 edge-to-edge 之后 IME 变成 overlay inset，窗口不再 resize；RN 自己只负责把
`keyboardDidShow` 发出来（`ReactRootView.checkForKeyboardEvents` 读 `Type.ime()` 的 insets），
**不代替 app 挪布局**。修法：ChatScreen 外面包一层 `KeyboardAvoidingView behavior="padding"`。

这里还有第二个坑，是加了 KAV 之后门禁**又红了一次**才暴露的：KAV 收起键盘时把自己的
`paddingBottom` 动画到 **0**，于是 `container` 上原本的 `padding: 12` 被抹掉，
输入框底边从 2307 变成 2337 —— 正好贴到导航条带上。所以屏幕 padding 必须放内层 View：
现在是 `avoid:{flex:1}` + `container:{flex:1,padding:12}`。修好后键盘弹起时 composer 在
y=1487（离键盘顶 30px，正是那 12dp），收起时回到 2307，7/7 绿。
反向对照也做了：只把 `ChatScreen.tsx` 退回旧版，红的恰好只有键盘那条
（`the keyboard covers the composer: its bottom y=2307 is under ime top y=1517`），
其余 6 条照绿 —— 说明这条断言是单独扛得住的，不是搭便车。

只有真跑才量到的另外几件：

1. debug APK 装得上也跑得起来，但它**不含 `assets/index.android.bundle`**（`zipfile` 里连
   `assets/` 目录都没有；gradle 插件只给 non-debuggable 变体建 bundle 任务），所以本机必须连 Metro。
   CI 的 `android` job 在 dispatch 时多出一个 `lycoapp-release`，构建后由一步 python 断言 bundle 真在里面。
   **已实测**：release 包里 `assets/index.android.bundle` = 1,005,956 字节（另有
   `assets/dexopt/baseline.prof`），APK 54,125,997 字节（debug 是 122,861,213）；
   **杀掉 Metro**（8081 端口确认无响应，node 进程要单独 kill，`TaskStop` 只杀掉外层 shell）
   并 `adb reverse --remove-all` 之后，同一个 `device_ui_check.py` 跑 release 包仍然 6/6 绿，
   两张图的地图块都在 y=306..777 = 472px = 179.8dp，与 debug+Metro 那轮**逐像素一致**
   —— 所以这个包真的自带 JS，可以脱离 dev server 装。
   （`device` job 现在还要显式 `--input run_emulator=true` 才排队，否则普通 dispatch 会留一个
   永远等不到 runner 的 job；不带这个 input 的 dispatch 里它是 skipped。）
2. `src/api/core.ts` 的 `DEFAULT_BASE_URL='http://127.0.0.1:8080'` 在模拟器里指的是**模拟器自己**，
   所以发一条消息必然失败：真图上气泡是 `出错了：TypeError: Network request failed`。
   用户气泡右对齐、错误气泡左对齐，这两件是看图才知道的。这条 TODO 本来就在代码里
   （等 on-device core server），我**没有**擅自改 baseURL。
3. 键盘弹得出来也收得回去（`input tap` 落在输入框上 → `mInputShown=true`）；
   `哪家好` 在 0 POI 时确实 disabled，和源码判断一致。
4. 「搜身边 1km」显示成「搜身边 1KM」：RNW 源码里就有 `textTransform:'uppercase'`，
   两边一致，所以这不是设备差异，是文案本身要不要改（产品决定，记着不动）。

**没验到的（不许顺嘴上抬）**：内嵌 Python。模拟器上跑的是 CI 那个 RN APK，
设备里没有任何一处执行过 `core/` 的 Python；物理手机也没跑过；CI 侧仍然没有安装环节。
`docs/ON_DEVICE_PYTHON.md` 的口径因此只从"从没看过一眼真机"改成
"RN 外壳已在 Android 36 模拟器跑通并截图核对，Python 侧仍未上设备验证"。

## 关于 deepseek-harness 的一个坑

它默认分支是 **`master`**。上一轮 AI 用 `main` 去请求 `contents/docs/development.md`
和 `contents/apps/desktop`，一直 404，然后重复发同一条命令直到卡死循环。
本次先 `GET /repos/...` 读 `default_branch` 再取路径，一次就拿到了插件契约。
