# 安装 Breeze TTS

本机语音没用豆包，也没用 Edge TTS，而是跑了一个纯本地的 **Breeze-TTS-2**。

好处：完全离线、不按字数计费、音色是自己的（可以克隆）。
代价：第一次要下 3.5GB 模型，且必须有一块能跑 Vulkan 的显卡（没有也能退回 CPU，但会慢）。

本文从下载一路写到「一键启动」，再到音色的完整配置。

---

## 0. 官方地址

| 用途 | 地址 |
|---|---|
| **发布页（下载程序）** | https://github.com/HoppouAI/Breeze-TTS-2.cpp/releases |
| 仓库主页 | https://github.com/HoppouAI/Breeze-TTS-2.cpp |
| **预编译 GGUF 模型** | https://huggingface.co/HoppouAI/Breeze-TTS-2.cpp |
| **上游原始权重（6.5 GB）** | https://huggingface.co/BreezeBlue/Breeze-TTS-2 |
| 上游 GitHub | https://github.com/BreezeBlue/Breeze-TTS-2 |

本机用的是 **HoppouAI/Breeze-TTS-2.cpp** 这个 C++/GGUF 重实现版，因为它直接提供 **Windows Vulkan 预编译包**，解压就能跑，不用自己 cmake 编译。

**程序和模型是分开下的**：

- 程序（`breeze-server.exe` 等）→ GitHub Releases 的 zip
- 模型（`.gguf`）→ HuggingFace

很多人只下了程序，启动时找不到模型，就是漏了这一步。

---

## 1. 下载

打开发布页 https://github.com/HoppouAI/Breeze-TTS-2.cpp/releases ，在 Assets 里找：

```
breeze-tts-2-v0.1.3-windows-x64-vulkan.zip      约 74 MB
```

**文件命名规律**：`breeze-tts-2-v<版本>-windows-x64-vulkan.zip`。版本号会变，认准 `windows-x64-vulkan` 这一段。

**为什么选 Vulkan 版**：

- 同一份二进制同时支持 **NVIDIA / AMD / Intel** 显卡，集显也吃
- 不用装 CUDA，只要显卡驱动是新的
- 找不到可用 GPU 时**自动退回 CPU**（CPU 需要 AVX2，2013 年后的 x64 CPU 都有）

Linux 对应文件是 `breeze-tts-2-v<版本>-linux-x64-vulkan.tar.gz`（要求 glibc 2.35+，即 Ubuntu 22.04 / Debian 12 / Fedora 36 以上）。

---

## 2. 解压

解压到**纯英文路径**，本机是：

```
<BREEZE_ROOT>\
```

包内是**分卷**结构（`part00.bin` 到 `partxx.bin`），解压后应得到：

```
<BREEZE_ROOT>\
├── bin\                    ← 可执行文件
│   ├── breeze-server.exe       服务端（常驻）
│   ├── breeze-cli.exe          命令行（一次性生成，做音色用这个）
│   ├── breeze-convert.exe      换声/变声
│   ├── breeze-quantize.exe     模型量化
│   └── libbreeze.dll
├── models\                 ← 模型放这
├── voices\                 ← 音色放这
└── start-breeze.cmd        ← 一键启动脚本（第 5 节创建）
```

**路径不能带中文或空格**。`breeze-server.exe` 会按相对路径找资源和模型，中文路径容易在 DLL 加载阶段就失败。

---

## 3. 下模型

模型是 GGUF 文件，本机用的是 **q8_0**：

```
breeze-tts-2-q8_0.gguf    实测 3.32 GB（官方标注 3.3 GB）
```

放到 `<BREEZE_ROOT>\models\`。

### 3.1 下载渠道（三种，任选一种）

**方式 A：直接下预编译 GGUF（推荐，最省事）**

官方预编译好的 GGUF 挂在 HuggingFace：

```
https://huggingface.co/HoppouAI/Breeze-TTS-2.cpp
```

进去点 **Files**，下对应量化的那个 `.gguf`（比如 `breeze-tts-2-q8_0.gguf`），放到 `models\` 就完事。

命令行下（装了 `huggingface-cli` 的话）：

```powershell
pip install -U "huggingface_hub[cli]"
huggingface-cli download HoppouAI/Breeze-TTS-2.cpp breeze-tts-2-q8_0.gguf --local-dir <BREEZE_ROOT>\models
```

国内网络下不动的话，加镜像：

```powershell
$env:HF_ENDPOINT = "https://hf-mirror.com"
huggingface-cli download HoppouAI/Breeze-TTS-2.cpp breeze-tts-2-q8_0.gguf --local-dir <BREEZE_ROOT>\models
```

**方式 B：下上游原始权重，自己转 GGUF**

上游（模型原作者）在 HuggingFace：

```
https://huggingface.co/BreezeBlue/Breeze-TTS-2
```

**约 6.5 GB**，而且——

> ⚠️ **必须包含 `audio_tokenizer/` 子目录**（里面是 vocoder）。转换脚本缺了它会直接拒绝运行。

```powershell
huggingface-cli download BreezeBlue/Breeze-TTS-2 --local-dir <BREEZE_ROOT>\Breeze-TTS-2
```

下完的目录结构必须是这样，缺一个文件就转不了：

```
Breeze-TTS-2/
  config.json
  model-*.safetensors
  tokenizer.json
  audio_tokenizer/
    config.json
    model.safetensors
```

然后转换（需要仓库源码里的 `scripts/convert_hf_to_gguf.py`，发布页的预编译包里**没有**这个脚本，要去 GitHub 仓库下源码）：

```powershell
pip install -r scripts\requirements.txt
python scripts\convert_hf_to_gguf.py <BREEZE_ROOT>\Breeze-TTS-2 `
  -o <BREEZE_ROOT>\models\breeze-tts-2-f16.gguf --dtype f16
```

转换只依赖 `numpy` 和 `gguf`，**不需要 torch**，内存占用也低。

**方式 C：从 f16 自己量化**

拿到 f16 之后，用包里的 `breeze-quantize.exe` 压成 q8_0 / q4_k：

```powershell
cd <BREEZE_ROOT>\bin
.\breeze-quantize.exe "<BREEZE_ROOT>\models\breeze-tts-2-f16.gguf" `
                     "<BREEZE_ROOT>\models\breeze-tts-2-q8_0.gguf" `
                     q8_0
```

支持的量化类型：`f16`、`q8_0`、`q6_k`、`q4_k`、`q3_k`、`q2_k`。

> **注意**：`breeze-quantize` 的量化类型是**位置参数**（直接跟在输入输出后面），不是 `--type`。这个和 llama.cpp 的习惯不一样。

### 3.2 量化怎么选

官方给的表（显存按官方估算）：

| 量化 | 大小 | 显存约 | 说明 |
|---|---|---|---|
| `f16` | 5.9 GB | ~7 GB | 参考质量，最慢 |
| **`q8_0`** | **3.3 GB** | **~4 GB** | **官方推荐，本机用的这个** |
| `q6_k` | 2.9 GB | ~3.5 GB | |
| `q4_k` | 2.4 GB | ~3 GB | 最小的"安全"选择 |
| `q8_0-dd4` / `q8_0-dd2` / `q4_k-dd2` | 2.3–3.4 GB | — | 实验性，见下 |

**`-dd` 系列是什么**：它们把 depth decoder 也量化了，其他量化会保留较高精度。好处是在"depth decoder 是瓶颈"的机器上明显更快（它每帧要跑 15 个串行步骤）。

**但有代价**：depth 的码字会逐帧反馈进 backbone，误差随长度累积——**45 秒以内还行，超过就开始发闷、变薄**。官方原话是 "Fine for short lines, not for narration."。

她平时说的话就一两句，`-dd` 其实可用；但如果要读长段文字，别用。

**实时率参考**（RTX 3060 实测，官方数据）：

- `q4_k`：约 1.8x 实时
- `q8_0`：约 1.5x 实时
- 带 guidance（`cfg_scale` > 1）时降到 1.44x / 1.31x

> 「1.5x 实时」= 生成 1 秒音频用 0.67 秒。低于 1.0 就没法流畅播放，只能降量化或换显卡。

### 3.3 验证模型能用

```powershell
cd <BREEZE_ROOT>\bin
.\breeze-cli.exe "<BREEZE_ROOT>\models\breeze-tts-2-q8_0.gguf" --text "hello" --output "<BREEZE_ROOT>\check.wav"
```

正常输出：

```
loading <BREEZE_ROOT>\models\breeze-tts-2-q8_0.gguf ...
backend: Vulkan0, sample rate: 24000
generated 0.32 s
...
wrote <BREEZE_ROOT>\check.wav (2.64 s)
```

- `backend: Vulkan0` = 走显卡（本机实测是 RTX 4070 Laptop）
- `backend: CPU` = Vulkan 没生效，会慢很多
- 模型加载失败会直接报错退出，不会静默降级

### 3.4 模型文件放哪、叫什么

- 位置：`<BREEZE_ROOT>\models\`
- 文件名：保持原样（`breeze-tts-2-q8_0.gguf`）
- 启动脚本里的模型路径必须和实际文件名**一字不差**

如果想放别处（比如 D 盘），改启动脚本里的路径就行，不强制放 `models\`：

```bat
"<BREEZE_ROOT>\bin\breeze-server.exe" "D:\MyModels\breeze-tts-2-q8_0.gguf" ...
```

### 3.5 全部就位后的目录长这样

对照检查一遍，**这一步能省掉后面 80% 的"启动报错"**：

```
<BREEZE_ROOT>\
├── bin\
│   ├── breeze-server.exe
│   ├── breeze-cli.exe
│   ├── breeze-convert.exe
│   ├── breeze-quantize.exe
│   ├── libbreeze.dll
│   └── docs\                      ← 官方文档，出问题先翻这里
├── models\
│   └── breeze-tts-2-q8_0.gguf     ← 3.3 GB，必须有
├── voices\
│   ├── dafeiyu_ref.wav            ← 你的参考录音
│   └── dafeiyu.breeze             ← 第 4 节生成
└── start-breeze.cmd               ← 第 5 节创建
```

**检查清单**：

| 项 | 检查方法 |
|---|---|
| 程序齐了 | `bin\` 下有 4 个 exe + 1 个 dll |
| 模型在 | `models\*.gguf` 存在且大小对得上 |
| 参考录音在 | `voices\` 下有 wav |
| 音色做好 | `voices\` 下有 `.breeze` |
| 启动脚本在 | `start-breeze.cmd` 路径写的是绝对路径 |

**只下程序的典型症状**：启动时报找不到模型、或者 `model file not found`，因为模型得单独去 HuggingFace 下。

---

## 4. 做音色（第一次必须先做这一步）

Breeze 的音色有两种，**先搞懂区别再动手**：

| 类型 | 存哪 | 会不会丢 | 什么时候用 |
|---|---|---|---|
| **cached**（缓存音色） | 内存 | 服务重启就没了 | 临时试音、一次性克隆 |
| **saved**（保存音色） | `voices\<名字>.breeze` 文件 | 永久，启动自动加载 | **正式用，就是这种** |

要做正式音色，得先有 **saved voice**。

### 4.1 准备参考录音

- 格式：任意 WAV（会自动转单声道、重采样到模型采样率）
- 时长：**5–15 秒**最合适，本机用的是 4.16 秒
- 内容：干净的说话声，**不能有背景音乐、风扇声、回声**

> 官方原话：克隆会把听到的一切都复制进去。带噪声的参考音，噪声会跟着进每一次生成，调 `--cfg-scale` 也救不回来。

本机参考录音：`<BREEZE_ROOT>\voices\dafeiyu_ref.wav`

### 4.2 准备逐字文本

必须准备参考录音的**逐字稿**，包括标点：

```
你好呀，今天天气真好。我们一起出去走走吧？
```

> **这是最容易翻车的一步**。`--ref-text` 和录音内容差一个字、差一个标点，克隆音色就会明显变差。官方原话是 "or the clone degrades badly"。

### 4.3 生成 .breeze 音色文件

用 `breeze-cli` 的 `--save-voice`（不是 `--out`，那是输出音频）：

```powershell
cd <BREEZE_ROOT>\bin
.\breeze-cli.exe "<BREEZE_ROOT>\models\breeze-tts-2-q8_0.gguf" `
  --ref-audio "<BREEZE_ROOT>\voices\dafeiyu_ref.wav" `
  --ref-text "你好呀，今天天气真好。我们一起出去走走吧？" `
  --save-voice dafeiyu `
  --description "清纯自然的少女声音，像日常聊天那样说话，语气放松，不念稿。"
```

成功输出：

```
wrote voices/dafeiyu.breeze (52 frames, 4.16 s)
```

**参数逐个说**：

| 参数 | 值 | 说明 |
|---|---|---|
| 模型路径 | 第一个位置参数，**必须给** | 做音色也要加载模型 |
| `--ref-audio` | 参考录音 WAV | |
| `--ref-text` | 逐字稿 | 必须和录音完全一致 |
| `--save-voice` | 音色名 | **生成 `.breeze` 文件**。名只能是字母、数字、`-`、`_`，最长 64 字符 |
| `--description` | 一句话描述 | 可选。最长 4096 字节，不影响生成，只用于辨认 |

**音色名就是文件名**，也决定后面 AstrBot 里填什么。取名规则：

- ✅ `dafeiyu`、`young_woman`、`narrator-2`
- ❌ `大肥鱼`（中文）、`my voice`（空格）、`a/b`（斜杠）

### 4.4 本机现有音色

| 音色 id | 帧数 | 时长 | 说明 |
|---|---|---|---|
| `dafeiyu` | 52 | 4.16 s | **正式在用的那个** |
| `test1` | 63 | 5.04 s | 试验残留（另一段切分） |
| `test2` | 52 | 4.16 s | 试验残留 |

`test1` / `test2` 是调参时留下的，不影响使用。想清掉就删文件：

```powershell
Remove-Item <BREEZE_ROOT>\voices\test1.breeze, <BREEZE_ROOT>\voices\test2.breeze
```

### 4.5 验证音色

列出现有音色：

```powershell
cd <BREEZE_ROOT>\bin
.\breeze-cli.exe "<BREEZE_ROOT>\models\breeze-tts-2-q8_0.gguf" --list-voices --voices-dir "<BREEZE_ROOT>\voices"
```

输出（本机实测）：

```
dafeiyu                    4.16 s  你好呀，今天天气真好。我们一起出去走走吧？
                                   清纯自然的少女声音，像日常聊天那样说话，语气放松，不念稿。
test1                      5.04 s  你好呀，今天天气真好。我们一起出去走走吧？
                                   清纯自然的少女声音，像日常聊天那样说话，语气放松，不念稿。
test2                      4.16 s  你好呀，今天天气真好。我们一起出去走走吧？
                                   清纯自然的少女声音，像日常聊天那样说话，语气放松，不念稿。
```

有描述的会显示在第二行。

> **踩坑记录**：官方文档说 `--list-voices` 不加载模型、"returns immediately"，但**参数列表里模型路径是第一个位置参数**。实测只给 `--list-voices` 会报 `--text is required` 并退出。**必须带上模型路径**才正常输出（文件名而已，不会真的加载权重，所以仍然很快）。

服务起来之后也可以用 HTTP：

```powershell
curl http://127.0.0.1:8137/v1/voices
```

```json
[{
  "id": "dafeiyu",
  "frames": 52,
  "seconds": 4.16,
  "encode_ms": 0,
  "saved": true,
  "ref_text": "你好呀，今天天气真好。我们一起出去走走吧？",
  "description": "清纯自然的少女声音，像日常聊天那样说话，语气放松，不念稿。",
  "metadata": {}
}]
```

### 4.6 先用 CLI 试听一句

**在接进 AstrBot 之前，务必先用 CLI 生成一句听听**：

```powershell
.\breeze-cli.exe "<BREEZE_ROOT>\models\breeze-tts-2-q8_0.gguf" `
  --voice dafeiyu `
  --text "爸，该吃饭了，别又随便塞两口。" `
  --output "<BREEZE_ROOT>\test.wav"
```

- 用了 `--voice` 就不需要 `--ref-audio` 和 `--ref-text`（逐字稿跟着音色文件走）
- 不加 `--output` 会写到**当前工作目录**的 `output.wav`
- `--voices-dir` 默认是**当前目录**下的 `voices`。不在 `bin` 里跑就会找不到音色

听 `test.wav`。音色不像、吞字、杂音，都在这步解决，别等到接进 QQ 再查。

> **实测踩坑**：这里的路径我全写成了绝对路径，不是偷懒。`breeze-cli` 的 `--voices-dir` 默认相对**当前工作目录**，不是相对 exe 所在目录。我在别的工作目录下用 `..\voices` 跑过一次，直接报 `no voice called dafeiyu in ..\voices`；换成 `<BREEZE_ROOT>\voices` 立刻正常。所以要么先 `cd /d <BREEZE_ROOT>\bin`，要么全用绝对路径——**两条都做最保险**。

正常输出是这样的：

```
loading <BREEZE_ROOT>\models\breeze-tts-2-q8_0.gguf ...
backend: Vulkan0, sample rate: 24000
generated 0.32 s
generated 1.52 s
generated 2.56 s
wrote <BREEZE_ROOT>\test.wav (3.28 s)
```

`Vulkan0` 说明走的是显卡；如果显示 `CPU`，说明 Vulkan 没生效，速度会慢很多。

**常用调参**：

| 参数 | 默认 | 什么时候调 |
|---|---|---|
| `--seed` | `42` | 换一个 seed 就是换一种"发挥"。觉得这句念得不对，换 seed 重生成 |
| `--cfg-scale` | `1.0` | 想让她更贴描述/更用力时调到 1.2–1.5。**超过 2 会明显发刺** |
| `--split-chars` | `600` | 长文本按句切。**升高→分段少但可能跑题；降低→更稳但接不上** |
| `--max-new` | 模型默认 750 帧 | 只是防止跑飞的安全阀，不是长度控制。1 帧 = 80ms |

> `cfg-scale` 高于 1 会多跑一次前向，但实测只多 23% 开销（depth decoder 把两路合成一张图），不是翻倍。所以需要时放心开。

### 4.7 音色的描述和元数据（可选）

音色可以带一段描述和最多 32 个自定义字段。**不影响生成**，纯粹为了辨认和给别的工具筛选。

保存时加：

```powershell
.\breeze-cli.exe "<BREEZE_ROOT>\models\breeze-tts-2-q8_0.gguf" `
  --ref-audio "<BREEZE_ROOT>\voices\dafeiyu_ref.wav" `
  --ref-text "你好呀，今天天气真好。我们一起出去走走吧？" `
  --save-voice dafeiyu `
  --description "清纯自然的少女声音，像日常聊天那样说话，语气放松，不念稿。"
```

事后改（服务运行中，`PATCH` 直接重写 `.breeze` 文件）：

```powershell
curl -X PATCH http://127.0.0.1:8137/v1/voices/dafeiyu `
  -H "Content-Type: application/json" `
  -d '{"description":"清纯少女音，日常聊天语气，放松不念稿。","metadata":{"lang":"zh","use":"chat"}}'
```

规则：

- 只改你发过去的字段
- `metadata` 是**合并**，不是覆盖
- 字段设成 `null` 或空串 = 删除
- `"description": null` 或 `""` = 清空描述

### 4.8 `.breeze` 文件是什么

一个很小的二进制容器，**约 800 字节/秒参考音频**，所以 4 秒的音色就 3.5KB。

| 偏移 | 大小 | 内容 |
|---|---|---|
| 0 | 4 | 魔数 `BRZV` |
| 4 | 4 | 格式版本（1 或 2） |
| 8 | 4 | 编码采样率 |
| 12 | 4 | codebook 数量 |
| 16 | 4 | 帧数 |
| 20 | 4 | 逐字稿字节数 |
| 24 | n | 逐字稿（UTF-8） |
| 24+n | | 版本 2 才有：描述 + 自定义字段 |
| … | | 编码码字（int32 小端，按帧） |

**它存的是编码后的码字，不是音频**，不能直接播放。绑定在模型所用的 codec 上，所以：

> 把它当成"可以从原始 WAV 重建的缓存"，**别当归档格式**。原始 WAV 一定要留着。

版本 1 = 无描述无字段（老版本也能读）；版本 2 = 带描述或字段，需要当前这个版本才能读。

---

## 5. 一键启动

音色做好后，把它跑成常驻服务。

### 5.1 创建启动脚本

新建 `<BREEZE_ROOT>\start-breeze.cmd`：

```bat
@echo off
cd /d "<BREEZE_ROOT>\bin"
"<BREEZE_ROOT>\bin\breeze-server.exe" "<BREEZE_ROOT>\models\breeze-tts-2-q8_0.gguf" --host 127.0.0.1 --port 8137 --voices-dir "<BREEZE_ROOT>\voices" --ws-port -1 --webui
pause
```

**逐行说**：

| 行 | 为什么这么写 |
|---|---|
| `cd /d "<BREEZE_ROOT>\bin"` | **不能省**。程序按相对路径找资源，不在 `bin` 下启动会报错 |
| `breeze-server.exe` + 模型路径 | 第一个位置参数必须是 gguf |
| `--host 127.0.0.1` | **只监听本机**。别人扫不到你这个端口 |
| `--port 8137` | HTTP 端口（默认 8080，本机改成 8137） |
| `--voices-dir "<BREEZE_ROOT>\voices"` | 启动时把这里所有 `.breeze` 加载进来 |
| `--ws-port -1` | **关掉流式 WS 端口**。默认会占「HTTP端口+1」，AstrBot 用不着 |
| `--webui` | 开网页试听界面 |
| `pause` | 出错时黑框不闪退，能看到错误 |

### 5.2 双击启动

双击 `start-breeze.cmd`，会弹出一个黑框。

正常输出大概是这样：

```
... loading model ...
... warmup ...
listening on http://127.0.0.1:8137
```

**启动会用大约 2 秒做一次"热身"**——跑一次带指导和不带指导的空生成、解码几种尺寸的音频块，把 GPU 管线提前建好。官方实测：这一步把首次请求的「首包时间」从 640ms 降到 300ms，之后每次请求都是这个速度。不想热身就加 `--no-warmup`。

**黑框不能关**。关了服务就停了，AstrBot 那边发语音会全部失败。

### 5.3 开机自启（可选）

不想每次手动双击，就做个快捷方式放进启动目录：

```powershell
$startup = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut("$startup\Breeze TTS.lnk")
$lnk.TargetPath = "<BREEZE_ROOT>\start-breeze.cmd"
$lnk.WorkingDirectory = "<BREEZE_ROOT>"
$lnk.WindowStyle = 7          # 7 = 最小化启动
$lnk.Save()
```

`WindowStyle = 7` 让它最小化启动，不挡桌面。

### 5.4 后台运行（不弹黑框）

不想要黑框就用 `pythonw` 那套思路——用 `start /b` 或注册成计划任务：

```powershell
# 后台起，不留窗口
Start-Process -FilePath "<BREEZE_ROOT>\bin\breeze-server.exe" `
  -ArgumentList '"<BREEZE_ROOT>\models\breeze-tts-2-q8_0.gguf"','--host','127.0.0.1','--port','8137','--voices-dir','<BREEZE_ROOT>\voices','--ws-port','-1','--webui' `
  -WorkingDirectory "<BREEZE_ROOT>\bin" `
  -WindowStyle Hidden
```

**代价**：看不到控制台日志，出问题不好查。建议先用黑框跑通，稳定了再改隐藏。

### 5.5 验证服务起来了

```powershell
curl http://127.0.0.1:8137/health
```

返回：

```json
{"status":"ok","sample_rate":24000,"ws_port":0}
```

- `status: ok` = 服务在跑，模型已加载
- `ws_port: 0` = WS 端口已按 `--ws-port -1` 关闭
- 服务**在模型加载完之前不接受连接**，所以能返回就是热好了，不用猜延迟

再确认音色加载进来了：

```powershell
curl http://127.0.0.1:8137/v1/voices
```

浏览器直接开 `http://127.0.0.1:8137`，能看到 WebUI，三个标签页对应三种模式（设计音色 / 克隆音色 / 指导语气），可以直接试听和调参。

### 5.6 停止服务

```powershell
# 按端口找进程
Get-NetTCPConnection -LocalPort 8137 -State Listen | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }

# 或按名字
Stop-Process -Name breeze-server -Force
```

---

## 6. 接进 AstrBot

服务跑起来后，回到 AstrBot 后台配供应商。

### 6.1 新增供应商

后台 →「配置」→「模型提供商」→「新增」→ 类型选 **OpenAI 兼容 / TTS**：

| 字段 | 填什么 | 本机值 |
|---|---|---|
| ID | 自定，后面要引用 | `大肥鱼语音-Breeze` |
| 启用 | 打开 | ✅ |
| 类型 | `openai_tts_api` | — |
| API Base | `http://127.0.0.1:8137/v1` | — |
| API Key | `unused` | — |
| 模型 | `tts-1` | — |
| 音色 | **你做的音色名** | `dafeiyu` |
| 超时 | `180` | — |
| 代理 | 留空 | — |

对应的 JSON（本机 `config/astrbot/cmd_config.json` 里的实际结构）：

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

### 6.2 这几个值为什么这么填

每一个都有理由，填错就是不出声：

| 字段 | 要求 | 填错会怎样 |
|---|---|---|
| `api_base` | **必须带 `/v1`** | 少了 `/v1` → 404，因为真实接口是 `/v1/audio/speech` |
| `api_key` | 填 `unused`，**不能留空** | 留空 → 保存失败。Breeze 根本没鉴权，这个值会被忽略 |
| `model` | 必须是 `tts-1` | Breeze 会忽略，但 AstrBot 侧要做协议校验 |
| 音色 | **`.breeze` 文件名去掉后缀** | 填错 → Breeze 返回 404 `unknown voice_id`，**不会悄悄退回默认音色** |
| `timeout` | ≥ 180 | 给少了 → 首次请求超时（模型刚加载完还在热身） |

> 音色名错了一定是 404，这是 Breeze 故意设计的——否则打错一个字就会得到完全不同的音色，看起来像模型坏了。

### 6.3 设为当前 TTS

在「配置文件 → AI → 语音合成」里选中这个供应商，或者直接在 `cmd_config.json` 里改：

```json
"provider_tts_settings": {
  "enable": false,
  "provider_id": "大肥鱼语音-Breeze",
  "dual_output": false,
  "use_file_service": false,
  "trigger_probability": 0.5
}
```

**`enable` 的含义**：

| 值 | 行为 |
|---|---|
| `false`（本机） | 关掉自动语音。她只在想发的时候发（由人格走工具调用） |
| `true` | 每条回复按 `trigger_probability` 概率自动带语音 |

本机是 `false`。12 天里她发了 329 条，10-30 那天 218 条（在调功能），11-01 有 44 条，其余日均 2–17 条。

### 6.4 在 QQ 里实测

配好后跟她说一句话，或者直接让她发语音。

**验证顺序**（哪一步不通就停在哪一步查）：

1. `curl http://127.0.0.1:8137/health` → 服务活着吗
2. `curl http://127.0.0.1:8137/v1/voices` → 音色在不在
3. CLI 生成一句 → 音色本身对不对（第 4.6 节）
4. AstrBot 后台把供应商的「测试」按钮点一下 → 接口通不通
5. QQ 里发消息 → 全链路通不通

---

## 7. 三个必须打的补丁

Breeze 这类流式 TTS 有三个已知问题，本机全用插件补掉了。**不装这三个，语音在 QQ 里就是残的**。

### 补丁一：WAV 头长度是 `0xFFFFFFFF`

**症状**：QQ 里播放时长乱跳、放一半就停、拖进度条直接崩。

**原因**：流式生成时不知道总长度，WAV 头的 `RIFF` 和 `data` chunk size 被写成 `0xFFFFFFFF`。官方文档也承认这点：「WAV header goes out first with its length fields set to the maximum, because the length is not known yet」。

**解决**：装 `astrbot_plugin_tts_wav_fix`，生成完成后重写 WAV 头，把真实长度填回去。

### 补丁二：句尾提前 EOS，吞最后一个字

**症状**：「你好呀」变成「你好」，最后一个字没了。

**解决**：同一个插件检测句尾完整性，不完整就**换 seed 重生成**。

> 注意是**换 seed**，不是拿原参数重试。Breeze 的 seed 完全决定输出，原参数重试大概率得到一模一样的结果。

### 补丁三：大语音撑爆连接

**症状**：3MB 以上的语音发出去，QQ 掉线。

**原因**：AstrBot 默认把语音转成 base64 走反向 WS 发送，3MB 转完约 60MB，超过 NapCat 反向 WS 的 **50MB** 上限。

**解决**：装 `astrbot_plugin_local_media_uri`，改走本地文件路径发送，不转 base64。

三个插件源码都在 [`../../config/custom-plugins/`](../../config/custom-plugins/)。

---

## 8. 进阶调参

### 8.1 实时率不够就卡

实时率 = 每秒生成几秒音频。低于 1.0 时**任何客户端缓冲都救不了**，因为播放比生成快。

先自己测（别信别人的数字）：

```powershell
curl -s -o out.pcm -w "%{time_total}`n" `
  --form-string "text=这是一句足够长、能生成好几秒音频的话。" `
  http://127.0.0.1:8137/v1/audio/speech
```

音频秒数 = `文件字节数 / 2 / 24000`，再除以 `time_total` 就是实时率。

低于 1.0 的三个办法：

1. 降量化（q8_0 → q4_k）
2. 调大 `--chunk-max`
3. 换更快的显卡

### 8.2 卡顿不一定怪实时率

真正更常见的原因是**队列深度**。音频是按块送出的，客户端队列必须比"生成一整块的时间"更深。

官方给的建议：

- `--chunk-max 40` 是甜点。再大收益就没了，还要求更深的队列
- 服务端会在一块的音频快放完时提前补发，所以客户端缓冲 **1 秒左右**就够
- 要"预缓冲"而不是"延迟"。延迟半秒不会产生缓冲，只是把开始时间往后挪

```bat
REM 想要更快出声：降低首块
--chunk-first 2

REM 想要更稳：调大块上限
--chunk-max 40
```

### 8.3 并发

服务端**一次只跑一个请求**，第二个并发请求直接返回 `409 busy`，不排队。所以：

- 单条语音场景没问题
- 如果要多路并发，得跑多个 server 实例

---

## 9. 换方案

不想跑 3.5GB 模型的话：

| 方案 | 成本 | 音质 | 接法 |
|---|---|---|---|
| Edge TTS | 免费 | 机械 | AstrBot 内置，选 Edge 类型 |
| 豆包语音 | 按时长，几分钱/条 | 像真人 | 填 app id + access token |
| Breeze 本地 | 一次性 3.5GB | 可克隆 | 本文 |

换方案只改供应商配置（`api_base` + 音色），**三个补丁不用动**——它们修的是协议层问题，跟音源无关。

---

## 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| 双击黑框闪退 | 不在 `bin` 目录启动 | 检查 `cd /d` 那行 |
| `no voice called xxx in voices` | `--voices-dir` 相对当前工作目录，不是相对 exe | 先 `cd /d <BREEZE_ROOT>\bin`，或全用绝对路径 |
| 启动报 DLL 相关错误 | 路径含中文/空格，或没装 VC++ 运行库 | 换纯英文路径；装 [VC++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) |
| `health` 连不上 | 服务没起来 / 端口被占 | `Get-NetTCPConnection -LocalPort 8137` |
| 首句超时 | 模型首次加载 + 热身慢 | `timeout` 调到 180+，或等 3 秒再发 |
| 音色不像 | `--ref-text` 跟录音不一致 | 逐字核对标点，重新 `--save-voice` |
| 音色带杂音 | 参考录音有背景噪声 | 重录一段安静环境的，**调参救不了** |
| 音色 404 | AstrBot 里填的音色名拼错 | 名字必须和 `.breeze` 文件名一致（不带后缀） |
| 显示 `backend: CPU` | Vulkan 没生效 | 更新显卡驱动；或用 `--cpu` 明确接受降速 |
| 声音断续卡顿 | 实时率低于 1.0，或队列太浅 | 降量化 / 调 `--chunk-max` |
| 吞字 | 句尾提前 EOS | 装 `tts_wav_fix` |
| 时长乱跳 | WAV 头 `0xFFFFFFFF` | 同上 |
| 大语音发不出 / 掉线 | base64 撑爆 50MB | 装 `local_media_uri` |
| 什么参数都不管用 | 参考录音质量差 | 重录，官方明确说调参救不回 |

---

## 附：一句话速查

```
下载 → 解压到 <BREEZE_ROOT> → 模型放 models\ → 
录音+逐字稿 → breeze-cli --save-voice 出音色 → 
双击 start-breeze.cmd → curl /health 验证 → 
AstrBot 填 8137 + 音色名 → 装三个补丁 → 发一条试
```

