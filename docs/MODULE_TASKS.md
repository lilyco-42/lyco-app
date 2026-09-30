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
| mobile/ui | 中 | me | 中 | ✅ 已交付（RN 0.87 脚手架 + 聊天/地图双屏 + API 桩，tsc 干净，jest 2/2；Cline 余额耗尽） |
| plugins/dsh-lyco-chat | 中 | me | 中 | 先读官方 DSH 插件 API 再定 |
| mobile/inference | 高 | me | 中 | JNI/.so，真机验证跑不掉 |
| core/action | 高 | 后期 | 高 | 无障碍 + AutoGLM，门控，默认关闭 |

派单规则：低难度低耦合先行；cline 单子必须带验收标准（测试通过）；
高难度/高耦合不派，攒到主控手里。
