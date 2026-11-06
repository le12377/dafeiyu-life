# 安装

按顺序来。每一步都写了本机实际装的是什么版本、什么路径、踩过什么坑。

**文档分工**：视频教程那十章在 [../setup.md](../setup.md)；视频之外自己扩展的部分在 [../../README.md](../../README.md)；这里放的是**每一步的详细命令、参数与踩坑**，视频内的和视频外的都在这一份里。

| 步骤 | 文档 | 装什么 | 本机版本 | 官方地址 |
|---|---|---|---|---|
| 1 | [astrbot.md](astrbot.md) | AstrBot Launcher + 三个组件 + 实例 | 4.29.4 | [AstrBotDevs/AstrBot](https://github.com/AstrBotDevs/AstrBot/releases) |
| 2 | [napcat.md](napcat.md) | NapCat 一键包 + 小号 QQ | 9.9.33-52230 | [NapNeko/NapCatQQ](https://github.com/NapNeko/NapCatQQ/releases) |
| 3 | [tts.md](tts.md) | Breeze-TTS-2 本地语音 | 2 · v0.1.3 | [HoppouAI/Breeze-TTS-2.cpp](https://github.com/HoppouAI/Breeze-TTS-2.cpp/releases) |
| 4 | [image.md](image.md) | ComfyUI + MOSS-Image 生图 | 12.1 GB 模型 | [Comfy-Org/Comfy-Desktop](https://github.com/Comfy-Org/Comfy-Desktop/releases) |
| 5 | [ollama.md](ollama.md) | Ollama + bge-m3 嵌入模型 | 0.40.14 | [ollama.com/download](https://ollama.com/download/windows) |
| 6 | [obsidian.md](obsidian.md) | Obsidian + Local REST API | 5.5.2 | [Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api) |

## 要下的文件对照

发布页里资产很多，这里直接说下哪个：

| 组件 | 下载文件名 | 大小 |
|---|---|---|
| AstrBot | `AstrBot Launcher ... .exe` | ~12 MB |
| NapCat | `NapCat.Shell.Windows.OneKey.zip` | 内置 QQ |
| Breeze TTS 程序 | `breeze-tts-2-v0.1.3-windows-x64-vulkan.zip` | ~74 MB |
| **Breeze TTS 模型** | `breeze-tts-2-q8_0.gguf`（**去 HuggingFace 下**，不在 GitHub） | 3.32 GB |
| ComfyUI | 官网 `comfy.org/download` 的 Windows 安装包 | — |
| Ollama | `OllamaSetup.exe` | ~700 MB |
| bge-m3 | `ollama pull bge-m3`（不是下文件，是拉模型） | 1.2 GB |
| Obsidian | 官网安装包 | — |
| Local REST API | **在 Obsidian 里搜插件名装，不下文件** | — |

**程序和模型分开下**：Breeze 的程序在 GitHub Releases，模型在 HuggingFace（https://huggingface.co/HoppouAI/Breeze-TTS-2.cpp）。很多人只下了程序，启动时找不到模型——这是最常见的卡点，详见 [tts.md](tts.md) 第 3 节。

**别下错**：

- AstrBot 别下 `dashboard.zip`（那是 Docker / Linux 用的源码包）
- NapCat 别下 `NapCat.Shell.zip`（那个要你自己先装 QQ）
- ComfyUI 别下已归档的 `Comfy-Org/desktop`


## 装配顺序

```
① AstrBot          ← 大脑，先有它
      ↓
② NapCat           ← 让它的消息能进出 QQ
      ↓
③ 接上模型          ← 填 API key，能聊天了
      ↓
④ Breeze TTS       ← 让它有声音
      ↓
⑤ ComfyUI + anima  ← 让它能画图
      ↓
⑥ Ollama + bge-m3  ← 让记忆能按语义检索（可选）
```

**关键顺序**：一定要先做完 ① ② ③，确认能在 QQ 里正常收发文字，再去搞 ④ ⑤ ⑥ ⑦。本地语音、生图、向量记忆都是独立的大件，先上它们会让排查变得很混乱——你没法判断问题出在网络、配置、还是模型。

**⑥ 是可选的**：不装 Ollama，她的记忆照样能存能查（走 FTS 全文 + 图谱），只是少了"意思相近"这一层。详见 [ollama.md](ollama.md) 第 5 节的实测说明。


## 硬件要求

| 项 | 最低 | 本机 |
|---|---|---|
| 系统 | Windows 10 x64 | Windows 10.0.26200 |
| 一直开机 | 是 | 是 |
| 磁盘 | 20 GB（不含模型） | — |
| 磁盘（全装） | 35 GB | — |
| 显存 | 8 GB 可跑生图 | — |

**必须一直开着机**。电脑一关她就下线，教程里也提过这个前提。想 24 小时在线就得走云服务器。

## 磁盘占用明细

| 组件 | 大小 |
|---|---|
| AstrBot Launcher + 组件 | ~1.5 GB（含 Python/Node/uv） |
| NapCat + QQ | ~2 GB |
| Breeze TTS 模型 | 3.32 GB |
| ComfyUI 模型 | 12.1 GB |
| Ollama 程序 + bge-m3 | ~1.9 GB（程序 ~700 MB + 模型 1.2 GB） |
| 表情包素材 | 700 MB |
| 运行数据（数据库、图） | 逐步增长 |

## 端口占用

装完这些，本机会占这些端口：

| 端口 | 谁 |
|---|---|
| 6185 | AstrBot 后台 |
| 6199 | 反向 WS（AstrBot 做服务端） |
| 8188 | ComfyUI |
| 8137 | Breeze TTS |
| 11434 | Ollama（记忆嵌入） |
| 27124 | Obsidian REST API |
| 7833 | self_learning 的 webui |
| 6190 | private_companion 的 webui |
| 4100 | proactive_chat 的 webui |

**端口冲突是常见故障源**。装之前先确认这些端口没被别的东西占着：

```powershell
Get-NetTCPConnection -LocalPort 6185,6199,8137,8188,11434 -State Listen
```

## 三个加速手段

国内网络下这几步容易卡，对应关系：

| 卡在哪 | 办法 |
|---|---|
| Launcher 装组件 | 开「中国大陆一键加速」 |
| 部署实例装 Python 依赖 | 同上；或设 `pypi_index_url` 走国内镜像 |
| 模型下载 | 用国内 HF 镜像（`hf-mirror.com`） |

本机的 `pypi_index_url` 走的是阿里云镜像：

```json
"pypi_index_url": "https://mirrors.aliyun.com/pypi/simple/"
```

## 装完之后

五件都装好后，回到 [setup.md](../setup.md) 走配置流程：建机器人、绑模型、设白名单、导人格、装记忆。

[setup.md](../setup.md) 开头有一张**全仓库文档地图**，所有 md 文件都能从那儿找到。也可以直接跳到最想看的那份：

- 插件都是干什么的 → [plugins/README.md](../plugins/README.md)
- 语音架构与三个已知故障 → [tts/README.md](../tts/README.md)
- NapCat 连接细节与常见坑 → [napcat/README.md](../napcat/README.md)
- 生图链路与参数理由 → [image/README.md](../image/README.md)
- 记忆怎么长的 → [memory.md](../memory.md)
- 她的人设全文 → [config/personas/大肥鱼.system_prompt.md](../../config/personas/大肥鱼.system_prompt.md)
- 那张自画像的生成参数 → [media/README.md](../../media/README.md)
- 三个脚本怎么跑 → [tools/README.md](../../tools/README.md)
