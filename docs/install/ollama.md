# 本地模型（Ollama）

她的记忆层面要一个**嵌入模型**（embedding），作用是把一句话变成一串数字坐标，让意思相近的句子在向量空间里离得近，检索时才能顺藤摸瓜找到对应的记忆。

三种做法：

| 做法 | 成本 | 隐私 | 本机选择 |
|---|---|---|---|
| **Ollama 本地跑** | 免费，占 1.2GB 内存 | 全留在这台机器 | ✅ 选的就是这个 |
| 云端 API（硅基流动等） | 免费额度后按量计费 | 文本要发出去 | — |
| 不开向量检索 | 0 | — | —（见第 5 节的实测说明） |

---

## 0. 官方地址

| 用途 | 地址 |
|---|---|
| **下载页** | https://ollama.com/download/windows |
| 模型库（搜模型） | https://ollama.com/search |
| bge-m3 模型页 | https://ollama.com/library/bge-m3 |
| Windows 安装文档 | https://docs.ollama.com/windows |
| GitHub | https://github.com/ollama/ollama |

---

## 1. 下载安装

打开 https://ollama.com/download/windows ，下 **`OllamaSetup.exe`**。

特点：

- **装到当前用户目录，不需要管理员权限**
- 装完自动在后台跑一个服务，监听 `127.0.0.1:11434`
- 模型默认存在 `%USERPROFILE%\.ollama\models`

**改安装位置**（不想装到 C 盘）：

```powershell
OllamaSetup.exe /DIR="D:\Ollama"
```

**改模型存放位置**（模型很占地方，一般都要改）：

```powershell
# 设成用户环境变量，装完后重开终端生效
[Environment]::SetEnvironmentVariable('OLLAMA_MODELS', 'D:\OllamaModels', 'User')
```

> 官方说明：用 `OLLAMA_MODELS` 换了位置之后，再跑安装器不会删你已经下过的模型。

**如果是服务器 / 不想用安装器**：官方还提供 `ollama-windows-amd64.zip` 独立包，只有 CLI 和 N 卡的 GPU 库依赖，解压即用。

---

## 2. 下模型

装完打开一个新终端（让 PATH 生效），先确认版本：

```powershell
ollama --version
```

本机是 **0.40.14**。

### 2.1 拉 bge-m3

```powershell
ollama pull bge-m3
```

- 大小 **1.2 GB**（f16 精度，567M 参数）
- 上下文窗口 8K
- 支持多语言（中英日韩等），这正是要它的原因
- 输出 **1024 维**向量，和 AstrBot 里填的维度一致

**拉完确认**：

```powershell
ollama list
```

应该看到 `bge-m3:latest  1.2GB`。

### 2.2 替代模型（一般不需要）

| 模型 | 大小 | 特点 | 什么时候用 |
|---|---|---|---|
| `bge-m3` ✅ | 1.2GB | 多语言、1024 维 | 本机用的 |
| `nomic-embed-text` | ~275MB | 更小，英文强 | 硬盘紧、只聊英文 |
| `mxbai-embed-large` | ~670MB | 英文语料强 | 纯英文场景 |
| `qllama/bge-m3` | 438MB–1.2GB | 社区量化版 | 想省内存用 `q4_k_m` |

**换成别的模型要同步改维度**。`bge-m3` 是 1024 维，`nomic-embed-text` 是 768 维。AstrBot 里那个 `embedding_dimensions` 填错了检索会失效。

```powershell
# 举例：用更小的量化版 bge-m3
ollama pull qllama/bge-m3:q4_k_m
```

### 2.3 验证模型能用

```powershell
curl http://127.0.0.1:11434/v1/embeddings `
  -H "Content-Type: application/json" `
  -d '{"model":"bge-m3","input":"今天天气真好"}'
```

返回里会有一个 `embedding` 数组，长度应该是 **1024**。长度对了就说明维度没错。

Ollama 0.40+ 原生提供 OpenAI 兼容的 `/v1/embeddings`，所以 AstrBot 里可以直接把它当 OpenAI 类型接。

---

## 3. 接进 AstrBot

后台 →「配置」→「模型提供商」→「新增」→ 类型选 **嵌入（Embedding）**：

| 字段 | 填什么 | 本机值 |
|---|---|---|
| ID | 自定 | `大肥鱼记忆-本机` |
| 类型 | `openai_embedding` | — |
| API Base | `http://127.0.0.1:11434/v1` | — |
| API Key | `ollama`（Ollama 不校验，但必填） | — |
| 模型 | `bge-m3` | — |
| 维度 | `1024` | — |
| 维度模式 | `auto` | — |
| 超时 | `20` | — |

对应 JSON（本机 `config/astrbot/cmd_config.json` 实际结构）：

```json
{
  "id": "大肥鱼记忆-本机",
  "embedding_api_key": "ollama",
  "embedding_api_base": "http://127.0.0.1:11434/v1",
  "embedding_model": "bge-m3",
  "type": "openai_embedding",
  "provider": "openai",
  "provider_type": "embedding",
  "enable": true,
  "embedding_dimensions": 1024,
  "embedding_dimensions_mode": "auto",
  "timeout": 20,
  "proxy": ""
}
```

**几个必填项的理由**：

| 字段 | 要求 | 填错会怎样 |
|---|---|---|
| `api_base` | **必须带 `/v1`** | 少了 → 404 |
| `api_key` | 填 `ollama`，不能空 | 留空 → 保存失败。Ollama 不校验这个值 |
| `embedding_dimensions` | 必须和模型的输出维度一致 | 填错 → 检索结果全乱 |
| `proxy` | **留空** | 填了代理 → 连本地 11434 反而被转发走，连不上 |

> `proxy` 这条很容易踩：本机全局有 `http://127.0.0.1:7890` 的 git 代理，但 AstrBot 这个字段是独立的，必须留空才能直连 localhost。

然后在记忆插件里选这个供应商：

```json
"provider_settings": {
  "embedding_provider_id": "大肥鱼记忆-本机",
  "llm_provider_id": "deepseek-responses/deepseek-v4.1-flash"
}
```

配置见 [`../../config/plugins/astrbot_plugin_livingmemory.json`](../../config/plugins/astrbot_plugin_livingmemory.json)。

---

## 4. 服务怎么保持运行

**安装器装完会注册开机自启**，登录后 `ollama app.exe` 自动在托盘跑，服务就在 11434。

**检查**：

```powershell
Get-NetTCPConnection -LocalPort 11434 -State Listen
```

有输出就是活着。

**手动启动**（自启被关掉、或想临时跑）：

```powershell
# 带 GUI 托盘
& "$env:LOCALAPPDATA\Programs\Ollama\ollama app.exe"

# 只要服务（无界面，适合脚本）
ollama serve
```

**`ollama serve` 会占住那个终端**，关掉终端服务就停。想后台跑：

```powershell
Start-Process -FilePath "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" `
  -ArgumentList 'serve' -WindowStyle Hidden
```

**停掉**：

```powershell
Get-Process -Name 'ollama*' -ErrorAction SilentlyContinue | Stop-Process -Force
```

---

## 5. 它在记忆链路里的位置

`bge-m3` 提供 `/v1/embeddings`，是记忆写入链路的第 5 步：

```
一句话 → 攒 20 轮 → 总结成情景记忆 → documents 表
                                        │
                                        ├─► POST /v1/embeddings（就是这里）
                                        │      bge-m3 → 1024 维
                                        ├─► 写 FAISS: livingmemory.index
                                        ├─► 抽原子 → memory_atoms
                                        └─► 抽实体关系 → graph_* → FAISS: livingmemory_graph.index
```

**它属于常驻服务**，和 AstrBot、NapCat、ComfyUI 一样，是后台基础设施之一。

本机索引文件的实际状态：

| 索引 | 大小 | 维度 | 向量数 |
|---|---|---|---|
| `livingmemory.index` | 280.6 KB | 1024 | 70 |
| `livingmemory_graph.index` | 248.6 KB | 1024 | 62 |

维度 1024、条数分别对得上 `documents` 71 篇和图谱文档 63 篇。`document_vector_provider_fingerprint` 反解出来就是 `大肥鱼记忆-本机` + `bge-m3` + 1024，链路完整。

### 5.1 服务要常驻

安装器会注册开机自启，登录后 `ollama app.exe` 自动在托盘跑，服务就在 11434。

想确认在跑：

```powershell
Get-NetTCPConnection -LocalPort 11434 -State Listen
```

忘了开或托盘退了，起一下就行：

```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama app.exe"
```

**服务没起会怎样**：读已有的 70 条向量不受影响（读的是磁盘索引），但新记忆进来时第 5 步算不了，只能落到 BM25 关键词召回。所以它应该跟 AstrBot 一起保持常驻。

### 5.2 模型要拉到本地

```powershell
ollama pull bge-m3
```

1.2 GB，拉一次就行，之后离线可用。`ollama list` 能看到它。

容量参考：模型 1.2GB + 检索时约 1.4GB 内存。九天 71 篇的规模，索引文件才 280KB，存储完全不是瓶颈。

---

## 6. 换云端嵌入

不想在本地装 1.2GB 模型，可以用云端 embedding，改三处即可：

```json
{
  "embedding_api_base": "<服务商的 OpenAI 兼容地址>",
  "embedding_model": "<模型名>",
  "embedding_dimensions": "<该模型的输出维度，必须查准>"
}
```

常见选择：

| 服务 | 模型 | 维度 | 备注 |
|---|---|---|---|
| 硅基流动 | `BAAI/bge-m3` | 1024 | 有免费额度 |
| OpenAI | `text-embedding-3-small` | 1536 | 按 token 计费 |
| OpenAI | `text-embedding-3-large` | 3072 | 更贵 |

**换供应商或换模型之后必须重建索引**——两个不同模型产出的向量在同一个空间里没有可比性，混着用检索会退化。

> 记忆库里有个 `document_vector_provider_fingerprint` 字段，就是用来记录"这批向量是哪个供应商产的"。换供应商时它会变，这也是判断有没有干净重建的一个标记。

---

## 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| `could not connect to a running Ollama instance` | 服务没起 | `ollama serve` 或启动 `ollama app.exe` |
| `ollama pull` 卡住 | 网络拉不下模型 | 挂代理；或用 `qllama/bge-m3` 量化版更小 |
| AstrBot 报 404 | `api_base` 少了 `/v1` | 改成 `http://127.0.0.1:11434/v1` |
| AstrBot 报连接失败但端口在监听 | 供应商里填了代理 | `proxy` 字段留空 |
| 检索结果很乱 | 维度填错，或换过模型没重建索引 | 核对 `embedding_dimensions`；重建 |
| 模型下到 C 盘爆了 | 默认存 `~\.ollama\models` | 设 `OLLAMA_MODELS` 后重下 |
| 装完 `ollama` 命令找不到 | PATH 没刷新 | 重开终端，或直接用全路径 |
| 内存吃紧 | bge-m3 检索时约 1.4GB | 换 `qllama/bge-m3:q4_k_m` |
