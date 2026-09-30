# core 复用清单

从现有仓库直接复用，不重写：

| 资产 | 来源 | 用途 |
|------|------|------|
| `rag_loop.py`（router→检索→总结→verify） | `lyco-model` | 口碑聚合引擎：site: 搜索小红书/贴吧/地图评论 → chat 总结 |
| `lyco42/chat-slm-qwen3-0.6b-zh` GGUF | HuggingFace | 端侧总结模型 |
| `lyco42/lyco-agent-qwen3-0.6b-ondevice` GGUF | HuggingFace | OODA 结构化任务模型 |
| 三视图/配色/表情差分 | `lyco-ip/design` | App 内角色形象、头像、壁纸 |
| DeepWiki 官方 MCP | `https://mcp.deepwiki.com/mcp` | 仓库知识问答（已注册进全局 opencode.json） |

移动端推理：llama.cpp（Android .so 参考 huzpsb/llama_cpp_android_ci；
RN 侧参考 a-ghorbani/pocketpal-ai 的接入方式）。
地图：高德 Web Service（周边搜索 place/around + 详情 place/detail），Key 放本地配置。
