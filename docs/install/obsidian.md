# Obsidian 接入

她不只是聊天——还管着一个 Obsidian 知识库，在里面写日记、记要紧的事、整理资料。这台机器上她**真的在写**，不是演示。

这一节讲怎么把 Obsidian 接到 AstrBot，让她能读能写。

---

## 0. 官方地址

| 用途 | 地址 |
|---|---|
| **Local REST API 插件** | https://github.com/coddingtonbear/obsidian-local-rest-api |
| 插件文档 | https://coddingtonbear.github.io/obsidian-local-rest-api/ |
| MCP 桥接工具 | https://github.com/geelen/mcp-remote |
| Obsidian 官网 | https://obsidian.md |

本机装的插件 **`obsidian-local-rest-api` 5.5.2**，显示名是「**Local REST API with MCP**」——**5.x 版本自带 MCP 服务**，不需要额外装别的。

> 名字里那个 `with MCP` 很关键。老版本只有 REST API，要自己拿 `mcp-remote` 去桥接；5.x 直接暴露 `/mcp/` 端点。本机两种都用上了。

---

## 1. 装插件

### 1.1 先在 Obsidian 里装

1. 打开 Obsidian，进入你的库（本机是 `<OBSIDIAN_VAULT>`）
2. **设置 → 第三方插件 → 关闭安全模式**（Only Safe Mode 那个开关要关掉）
3. 点「**浏览**」，搜 `Local REST API`
4. 装好后点「**启用**」

**作者是 `coddingtonbear`**，别装错同名插件。

启用后会生成一张自签证书，服务默认开在：

| 端口 | 协议 | 说明 |
|---|---|---|
| **27124** | **HTTPS** | 默认开，本机用的这个 |
| 27123 | HTTP | 默认**关着**（`enableInsecureServer: false`） |

### 1.2 拿 API Key

**设置 → Local REST API → API Key**，复制那串字符。

本机这串是 **64 位**的。这就是后面 AstrBot 里填的 Bearer token。

### 1.3 本机插件的实际配置

`<OBSIDIAN_VAULT>\.obsidian\plugins\obsidian-local-rest-api\data.json`（**这个文件含私钥，不要提交**）：

| 项 | 本机值 |
|---|---|
| `port` | `27124` |
| `insecurePort` | `27123` |
| `enableInsecureServer` | `false`（HTTP 端口关着） |
| `enableSignedUrls` | `true` |
| `apiKey` | 64 位随机串（已脱敏） |
| `crypto` | 自签证书 + 私钥（插件自动生成） |

---

## 2. 验证 API 通不通

**直接用浏览器**不行（自签证书会被拦）。用 PowerShell：

```powershell
# 忽略证书校验，只看通不通
curl -k -H "Authorization: Bearer <你的key>" https://127.0.0.1:27124/
```

返回 JSON：

```json
{
  "status": "OK",
  "manifest": {
    "id": "obsidian-local-rest-api",
    "name": "Local REST API with MCP",
    "version": "5.5.2"
  },
  "authenticated": true,
  ...
}
```

`authenticated: true` 就说明 key 对、服务活。

### 2.1 常用接口

| 方法 | 路径 | 作用 |
|---|---|---|
| `GET` | `/` | 状态 + manifest |
| `GET` | `/vault/` | **列出根目录文件**（含子目录名） |
| `GET` | `/vault/<路径>` | 读一个文件 |
| `PUT` | `/vault/<路径>` | 写入/覆盖 |
| `POST` | `/vault/<路径>` | 追加到文件末尾 |
| `PATCH` | `/vault/<路径>` | 局部修改（需用 heading/block 定位） |
| `DELETE` | `/vault/<路径>` | 删除 |
| `POST` | `/search/simple/` | 全文搜索 |

**实测坑**：`GET /vault/子目录/` 会返回 **404**，只有根目录能列。要列子目录内容就自己按前缀过滤根清单：

```powershell
# 根清单里带 '鲸鱼日记' 的都列出来
curl -k -H "Authorization: Bearer <key>" https://127.0.0.1:27124/vault/
# 返回 ["鲸鱼日记/", "要紧的事.md", "知识库 wiki/", ...]
```

### 2.2 本机的库结构

```
<OBSIDIAN_VAULT>\
├── 原始资料 raw\            ← 待摄入的资料
├── 知识库 wiki\             ← 编译好的知识（目录/日志/综述/摘要/实体/概念/分析）
├── 报告 reports\            ← 摄入报告、体检报告
├── 鲸鱼日记\                ← 她自己的日记（她开的）
│   └── 2026-11-04.md
├── 要紧的事.md              ← 她给你记的大事
├── AGENTS.md                ← 库的维护规则
└── README.md
```

「鲸鱼日记」和「要紧的事」**不是配置**，是她自己写的私人内容。本档案的 `config/` 里没有它们。

---

## 3. 接进 AstrBot（两种方式）

### 方式 A：MCP（本机用的这个）

AstrBot 支持 MCP。在 `data/mcp_server.json` 里加：

```json
{
  "mcpServers": {
    "obsidian": {
      "active": true,
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote@latest",
        "https://127.0.0.1:27124/mcp/",
        "--header",
        "Authorization: Bearer <你的 API Key>"
      ],
      "env": {
        "NODE_TLS_REJECT_UNAUTHORIZED": "0"
      }
    }
  }
}
```

**三处必须对**：

| 项 | 要求 | 填错会怎样 |
|---|---|---|
| `command` | `npx` | 用 Launcher 内置的 Node，PATH 里有就行 |
| URL | **必须带 `/mcp/` 结尾的斜杠** | 少了斜杠 → 400 Bad Request |
| `--header` | `Authorization: Bearer <key>` | 少了 → 406 Not Acceptable |

**`NODE_TLS_REJECT_UNAUTHORIZED: "0"` 是必须的**：Obsidian 用的是自签证书，不关校验就会报证书错误。副作用是**那个 node 子进程对任何 TLS 证书都不校验**，所以只该用来连本机。

**这就是本机踩过的那个坑**：文件里藏了一个看不见的 BOM 字符，JSON 解析失败，MCP 页面一直不显示 obsidian。去掉 BOM 才好。如果你改完配置 MCP 列表里没有它，先查文件开头有没有 BOM。

配置见 [`../../config/astrbot/mcp_server.json`](../../config/astrbot/mcp_server.json)。

### 方式 B：直接用 REST（不经 MCP）

不想用 MCP 的话，让她用 HTTP 工具直接调 REST 接口：

```
读取：GET https://127.0.0.1:27124/vault/<路径>
      Header: Authorization: Bearer <key>
写入：PUT https://127.0.0.1:27124/vault/<路径>
      Header: Authorization: Bearer <key>
      Body:   文件内容（纯文本 md）
```

好处是链路短、好排查；坏处是她得手拼请求，不如 MCP 自然。

### 3.1 MCP 手握手测试

想确认 `/mcp/` 真的活着（而不只是"配置写对了"）：

```powershell
curl -k -X POST "https://127.0.0.1:27124/mcp/" `
  -H "Authorization: Bearer <key>" `
  -H "Content-Type: application/json" `
  -H "Accept: application/json, text/event-stream" `
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"probe","version":"1.0"}}}'
```

返回 `serverInfo` 就说明 MCP 端点通。

**注意**：`Accept` 头**必须同时包含** `application/json` 和 `text/event-stream`，只写前者会 406，只写后者会 400。这是 MCP 协议的规定。本机实测验证过。

---

## 4. 她拿这个库干什么

接上之后她有三个能力：

### 4.1 读写文件

你说「把这段记到库里」，她就能写进去。

本机 11-04 那天她自己开了两个文件：

| 文件 | 用途 |
|---|---|
| `鲸鱼日记/` 目录 | 她自己的日记本，按日期分文件 |
| `要紧的事.md` | 主人的大事记，到日子由她提醒 |

这两页的内容是她的私人记录，不收录在本档案里。

### 4.2 全文搜索

`POST /search/simple/?query=<关键词>`，她能搜到库里任意内容。

### 4.3 管知识库

配合 `AGENTS.md` 的规则，她能做「摄入」「体检」这类操作——读资料、写摘要、更新索引、维护交叉引用。这是另一条产品线（LLM Wiki），跟 QQ 聊天是分开用的。

---

## 5. 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| 连不上 27124 | Obsidian 没开 / 插件没启用 | 先确认 Obsidian 在跑，再看插件开关 |
| 证书错误 | 自签证书 | curl 加 `-k`；node 设 `NODE_TLS_REJECT_UNAUTHORIZED=0` |
| 401 Unauthorized | key 不对 | 重新从插件设置里复制 |
| 406 Not Acceptable | 少了 `Authorization` 头或 `Accept` 头 | 两个都要带 |
| 400 Bad Request | `/mcp` 少了结尾斜杠，或 `Accept` 缺 `text/event-stream` | 改成 `/mcp/`，补齐 Accept |
| MCP 列表里没有 obsidian | `mcp_server.json` 开头有 BOM | 用记事本「另存为 UTF-8 无 BOM」，或用脚本去掉 |
| `GET /vault/子目录/` 404 | 插件只支持列根目录 | 列根目录再按前缀过滤 |
| 改了 `data.json` 没生效 | 插件没重载 | Obsidian 里关掉插件再开 |

---

## 6. 安全提醒

本机这套配置有几处值得注意：

1. **`data.json` 里躺着完整私钥**（`crypto` 字段），它同时含证书、私钥和 CA 私钥。这个文件在 `.obsidian/plugins/` 下，**已经被本档案的 `.gitignore` 排除**，不要提交，也别截图外发。

2. **`NODE_TLS_REJECT_UNAUTHORIZED=0`** 让那个 node 子进程对所有 TLS 放行。更稳妥的做法是把 Obsidian 的自签 CA 导进系统信任列表，然后去掉这个变量。

3. **API Key 是 64 位随机串**，一旦泄漏别人就能读写整个库。换了 key 记得同步改 `mcp_server.json`。

4. **端口只绑 127.0.0.1**，局域网访问不到，这是对的。别改成 `0.0.0.0`。
