# 本地语音合成

本机没有用豆包、也没用 Edge TTS，而是跑了一个**本地 TTS 服务**：Breeze-TTS-2。好处是完全离线、不按字数计费、音色是自己的；代价是第一次要下 3.5GB 模型。

## 组件

| 组件 | 版本 / 大小 | 位置 |
|---|---|---|
| `breeze-server.exe` | 2.7 | `<BREEZE_ROOT>\bin\` |
| `breeze-tts-2-q8_0.gguf` | 3.57 GB | `<BREEZE_ROOT>\models\` |
| 音色 `dafeiyu.breeze` | 52 帧 / 4.16 秒 | `<BREEZE_ROOT>\voices\` |

服务监听 **127.0.0.1:8137**，对外提供 OpenAI 兼容接口。启动脚本：

```bat
@echo off
cd /d "<BREEZE_ROOT>\bin"
"<BREEZE_ROOT>\bin\breeze-server.exe" "<BREEZE_ROOT>\models\breeze-tts-2-q8_0.gguf" --host 127.0.0.1 --port 8137 --voices-dir "<BREEZE_ROOT>\voices" --ws-port -1 --webui
pause
```

参数说明：

| 参数 | 值 | 作用 |
|---|---|---|
| `--host` | `127.0.0.1` | 只监听本机，不暴露到局域网 |
| `--port` | `8137` | HTTP 端口 |
| `--voices-dir` | `voices` | 启动时加载所有 `.breeze` 音色 |
| `--ws-port` | `-1` | 关掉流式 WebSocket 端口 |
| `--webui` | — | 开一个网页试听界面 |

完整启动脚本见 [`../../config/environment/start-breeze.cmd`](../../config/environment/start-breeze.cmd)。

## 音色是怎么做的

她这个音色是**声音克隆**，不是凭空设计的。做法是给一段参考录音 + 那段录音的准确文字：

参考录音内容：

> 你好呀，今天天气真好。我们一起出去走走吧？

音色描述（写在 `.breeze` 里）：

> 清纯自然的少女声音，像日常聊天那样说话，语气放松，不念稿。

本机目前有三个音色，都基于同一段参考音频：

| 音色 id | 帧数 | 时长 | 用途 |
|---|---|---|---|
| `dafeiyu` | 52 | 4.16 s | **实际在用** |
| `test1` | 63 | 5.04 s | 试验残留 |
| `test2` | 52 | 4.16 s | 试验残留 |

想验证当前加载了哪些音色：

```powershell
curl http://127.0.0.1:8137/v1/voices
```

## 接进 AstrBot

在 AstrBot 的模型供应商里加一个 **OpenAI 兼容的 TTS** 供应商：

```json
{
  "id": "大肥鱼语音-Breeze",
  "type": "openai_tts_api",
  "provider": "openai",
  "provider_type": "text_to_speech",
  "enable": true,
  "api_key": "unused",
  "api_base": "http://127.0.0.1:8137/v1",
  "model": "tts-1",
  "openai-tts-voice": "dafeiyu",
  "timeout": 180,
  "proxy": ""
}
```

几个关键点：

- `api_key` 填 `unused` 就行。Breeze 没有鉴权，但 AstrBot 这个表单项必填。
- `model` 必须是 `tts-1`。Breeze 的 `/v1/audio/speech` 兼容 OpenAI 协议，但会忽略 model 字段。
- `openai-tts-voice` 填音色 id，就是 `.breeze` 的文件名（不带后缀）。
- `timeout` 给到 180 秒。模型首次加载慢，给少了会超时。

## 两个必须修的病

Breeze 这类流式 TTS 有两个通病，本机用两个自写插件补掉了。

### 1. WAV 头长度字段是 0xFFFFFFFF

流式生成时不知道总长度，就把头里的长度写成 `0xFFFFFFFF`。结果是：

- QQ 里播放时长显示乱跳
- 放到一半就停
- 拖动进度条直接崩

**修法**：`astrbot_plugin_tts_wav_fix` 在生成完成后重写 WAV 头，把真实的 `RIFF` chunk size 和 `data` chunk size 填回去。源码在 [`../../config/custom-plugins/astrbot_plugin_tts_wav_fix/`](../../config/custom-plugins/astrbot_plugin_tts_wav_fix/)。

### 2. 句尾提前 EOS，最后一个字被吞

生成到最后一个字时模型可能提前判定结束，导致"你好呀"变成"你好"。

**修法**：同一个插件检测句尾是否完整，不完整就**换 seed 重生成**，而不是简单重试原参数。

### 3. 大语音把连接撑爆

3MB 以上的语音，AstrBot 默认会转成 base64 走反向 WS 发送。转完 60MB 左右，超过 NapCat 反向 WS 的 50MB 上限，直接断开。

**修法**：`astrbot_plugin_local_media_uri` 改成走本地文件路径发送，不再 base64。

## 频率控制

AstrBot 侧有个发送概率：

```json
"provider_tts_settings": { "enable": false, "trigger_probability": 0.5 }
```

注意 `enable` 是 `false`——本机实际是**关掉自动语音**的，她只在主动想发的时候发（由人格设定里的「你会发语音」那条走工具调用）。如果打开 `enable` 并设 `trigger_probability: 0.5`，那就是每条回复有一半概率带语音。

九天里她一共发了 **327** 条语音，10-30 那天最多（218 条），那是你在试语音功能。

## 换成免方案

不想跑本地模型的话，Breeze 的文档里还支持这些方式：

- **微软 Edge TTS**：免费，但声音机械
- **豆包语音**：像真人，按时长计费
- 任何 OpenAI 兼容的 `/v1/audio/speech` 服务

改法就是换 `api_base` 和 `openai-tts-voice`，插件配置不用动。
