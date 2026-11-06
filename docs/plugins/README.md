# 插件清单

本机实际装的是 **20** 个插件，其中 **5** 个是为她手写的。

数据来源：插件目录下每个 `metadata.yaml` 的实测读取，不是从配置文件推的。

## 先说明一个坑

`config/plugins/` 下有 **22** 份配置，但只有 **20** 个插件真正装着。差的那 7 份是**插件被卸载后残留的历史配置**：

| 残留配置 | 状态 |
|---|---|
| `astrbot_plugin_emotionai_pro` | **已卸载**，只剩配置 |
| `astrbot_plugin_bili_downloader` | **已卸载** |
| `astrbot_plugin_gemini` | **已卸载** |
| `astrbot_plugin_knowledge_repo_sync` | **已卸载** |
| `astrbot_plugin_nai_brush` | **已卸载** |
| `astrbot_plugin_novelai_painter` | **已卸载** |
| `astrbot_plugin_get_px` | **已卸载** |

> **重要**：这 7 个**不在运行**，也不参与她的行为。本机有一个插件目录叫 `astrbot_plugin_get_px` 被删了但 `plugin_data/` 与 `config/` 都还留着。看到配置不代表在跑——判断「装没装」看 `core/data/plugins/` 下有没有那个目录。

另外 `plugin_data/` 里还有两个**空目录**（`astrbot_plugin_novelai_painter`、`astrbot_plugin_reality_companion_mihome`），也是卸载残留。

## 20 个在跑的插件

| 插件 | 显示名 | 版本 | 作者 | 做什么 |
|---|---|---|---|---|
| `astrbot_plugin_private_companion` | **我会永远陪着你** | 6.5.6 | menglimi | 陪伴核心。日程、心情、关系阶段、好感度、自拍、备忘、屏幕感知 |
| `astrbot_plugin_livingmemory` | LivingMemory | 2.8.2 | lxfight | 长期记忆。`documents` + `graph_*` + 原子过滤，双路召回 |
| `astrbot_plugin_self_learning` | self-learning | 4.4.5 | NickMo, EterUltimate | 风格学习。从聊天学「情境→表达」，学出 770 条 |
| `astrbot_plugin_proactive_chat` | 主动消息 | v1.2.6 | DBJD-CR | 主动搭话。30–600 分钟随机，凌晨 1–7 点不打扰 |
| `astrbot_plugin_anima_master` | **Anima 绘图大师** | 0.9.3 | YayiMiko | 生图。连本机 ComfyUI，含提示词优化 |
| `astrbot_plugin_image_companion` | **我会画给你看** | 0.4.5 | menglimi | 生图扩展。自拍、改图、参考图库 |
| `astrbot_plugin_irmia_vision` | **弥亚视觉工具** | 1.1.8 | 伊尔弥亚 | 主动读图。结果落库，避免重复调 VL 烧上下文 |
| `meme_manager` | **表情包管理器** | 5.2.10 | anka | 表情包。3 包共 763 张，WebUI 装包/选包/语义检索 |
| `astrbot_plugin_bilibili_shixun` | **B站拾讯** | v0.11.1 | yuease | B 站。免登录搜索、订阅、来源采集、个人简报 |
| `astrbot_plugin_biliread` | BiliRead | v1.2.0 | SodaCode & CodeBuddy & GLM-5 | 让 AI 理解 B 站视频 |
| `astrbot_plugin_qzone` | **QQ空间** | v3.2.0 | Zhalslar | 发说说、看动态、点赞评论、改签名 |
| `astrbot_plugin_matsuko_cover` | **AI点歌** | v2.13.0 | Matsuko | 翻唱。RVC / SVC-Fusion / SoulX-SVCVC |
| `astrbot_plugin_listen_music` | **我想听歌！** | 0.1.3 | 57Darling02 | 听歌。B 站单源搜索 + 语音送达 |
| `astrbot_plugin_web_search` | **网页搜索** | 1.0.0 | ayacyann | 联网搜索。7 条结果、抓 4 页正文 |
| `astrbot_plugin_llm_balance` | **大模型余额查询** | v1.4.3 | XTsat | 查余额，不查 key 明文 |
| `astrbot_plugin_dafeiyu_clean` | **大肥鱼回复防串台** | v0.1.0 | zexuan604 | **推送层**。删掉漏出的内部标签 |
| `astrbot_plugin_dafeiyu_signature` | **大肥鱼改签名** | v0.1.3 | zexuan604 | 让她自己改 QQ 个性签名 |
| `astrbot_plugin_meme_marker_fix` | **表情包标记补全** | v0.1.0 | `<SELF>` | **自写**。补全半截表情包标记 |
| `astrbot_plugin_tts_wav_fix` | **语音时长修正** | v0.2.0 | `<SELF>` | **自写**。修 WAV 头 + 防吞字 |
| `astrbot_plugin_local_media_uri` | **大语音本地发送** | v0.1.0 | local | **自写**。大语音走本地路径，绕 50MB 上限 |

## 5 个手写插件

这 5 个都是为解决具体故障写的，教程里没有。

### `astrbot_plugin_tts_wav_fix` v0.2.0（你写的）

**问题**：Breeze 这类流式 TTS 的 WAV 头长度字段是 `0xFFFFFFFF`，QQ 里播放时长乱跳、放一半就停；另外句尾经常提前 EOS，最后一个字被吞。

**做法**：重写 WAV 头（填回真实 chunk size），检测到句尾不完整就**换 seed 重生成**。

源码：[`../../config/custom-plugins/astrbot_plugin_tts_wav_fix/`](../../config/custom-plugins/astrbot_plugin_tts_wav_fix/)

### `astrbot_plugin_local_media_uri` v0.1.0

**问题**：3MB 以上语音转 base64 后约 60MB，超过 NapCat 反向 WS 的 50MB 上限，连接直接断。

**做法**：改走本地文件路径，不转 base64。

源码：[`../../config/custom-plugins/astrbot_plugin_local_media_uri/`](../../config/custom-plugins/astrbot_plugin_local_media_uri/)

### `astrbot_plugin_meme_marker_fix` v0.1.0（你写的）

**问题**：模型偶尔把表情包标记写成半截（`&&happy` 少了收尾 `&&`），QQ 里直接露出标记文字，表情包也发不出去。

**做法**：在历史、回复、发送前三处把标记补成对。

源码：[`../../config/custom-plugins/astrbot_plugin_meme_marker_fix/`](../../config/custom-plugins/astrbot_plugin_meme_marker_fix/)

### `astrbot_plugin_dafeiyu_clean` v0.1.0（原作者写的）

**问题**：模型漏出内部标签（`system_reminder`、DeepSeek 的 DSML 工具调用标记）。

**做法**：发出去之前删掉，聊天记录里也一起清。

源码：[`../../config/custom-plugins/astrbot_plugin_dafeiyu_clean/`](../../config/custom-plugins/astrbot_plugin_dafeiyu_clean/)

> 作者 **zexuan604**，就是原视频作者泽轩604。

### `astrbot_plugin_dafeiyu_signature` v0.1.3（原作者写的）

**做法**：主人用大白话叫她改签名，或者她自己心情变了自己改（一天最多两次）。

源码：[`../../config/custom-plugins/astrbot_plugin_dafeiyu_signature/`](../../config/custom-plugins/astrbot_plugin_dafeiyu_signature/)

> 作者同样 **zexuan604**。

## 插件怎么串起来

```
你发一条消息
   │
   ├─ platform.json 白名单   → 决定理不理你
   ├─ private_companion      → 注入日程/心情/关系阶段/好感度
   ├─ livingmemory           → 检索记忆，拼进上下文
   ├─ self_learning          → 注入「情境→表达」模式
   │
   ▼
大模型生成回复
   │
   ├─ dafeiyu_clean          → 清掉漏出的内部标签
   ├─ meme_marker_fix        → 补全表情包标记
   │
   ▼
发送
   ├─ tts_wav_fix            → 修 WAV 头、防吞字
   └─ local_media_uri        → 大文件走本地路径
```

**注意**：这张图里没有 `emotionai_pro`——它已卸载。好感度实际存在 `self_learning` 的 `user_affections` 表里，见 [setup.md 第 9.6 节](../setup.md#96-好感度她记得你是谁)。

## 配置怎么找

| 想看什么 | 文件 |
|---|---|
| 每个在跑插件的配置 | [`../../config/plugins/`](../../config/plugins/) 对应 `.json` |
| 插件版本/作者/描述 | [`../../config/plugins/PLUGIN_LIST.json`](../../config/plugins/PLUGIN_LIST.json) |
| 自写插件源码 | [`../../config/custom-plugins/`](../../config/custom-plugins/) |
| 表情包实际装了什么 | `config/plugins/meme_manager.json` |

## 表情包实测

`meme_manager` 的 `packs/` 下实际有 **748 张图**，分成 3 个包：

| 包 | 张数 | 装于 |
|---|---|---|
| `official-001`（官方表情包1号） | 410 | 10-30 08:59 |
| `deepseek-fanart-meme-pack`（DeepSeek 二创） | 186 | 10-29 14:33 |
| `blue-fat-fish-meme-pack`（蓝色大肥鱼） | 167 | 10-29 14:57 |

三个包合计 **763**，`packs/` 里能扫到 748 张图（差额是包内的非图片文件，如索引和配置）。

此外 `auto_collect_inbox/` 还有 3 张待审核的自动收集图。

她那 3451 字人格里专门写了一条规矩：

> 图片只能靠回复末尾那句 `&&分类键&&` 发出去。不要调 `send_message_to_user` 发网上的图，也不要自己编图片网址——你手上没有真实存在的图片链接，编出来的域名根本打不开。

这条规矩配的就是 `meme_manager` + `meme_marker_fix` 这一对。

图片素材本身（约 685MB）没进仓库，是第三方版权内容。
