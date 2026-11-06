# NapCat 配置

NapCat 负责把 QQ 小号变成 OneBot v11 接口。本机用的是 `NapCat.52230.Shell` 一键包，内置 QQ 9.9.33-52230。

## 文件位置

```
<NAPCAT_ROOT>/                        ← 解压出来的目录（本机在桌面）
├── NapCatWinBootMain.exe             ← 启动器
├── NapCatWinBootHook.dll
├── QQ.exe                            ← 小号专用的 QQ 本体
├── napcat.bat                        ← 普通启动（每次扫码）
├── napcat.quick.bat                  ← 免扫码快登
├── versions/9.9.33-52230/
│   └── resources/app/napcat/config/
│       ├── napcat_<BOT_QQ>.json          ← 全局行为配置
│       └── napcat_protocol_<BOT_QQ>.json ← 网络配置（WS/HTTP 客户端）
└── quick-login.log                   ← 消息收发日志
```

## 快速登录

免扫码靠 `napcat.quick.bat` 里的两个环境变量：

```bat
@echo off
chcp 65001 >nul
setlocal
set "NAPCAT_QUICK_ACCOUNT=<BOT_QQ>"
set "NAPCAT_QUICK_PASSWORD=<REDACTED:account-password>"
.\NapCatWinBootMain.exe <BOT_QQ>
pause
```

原文见 [`../../config/napcat/quick-login.bat.redacted`](../../config/napcat/quick-login.bat.redacted)。

## 全局配置

`napcat_<BOT_QQ>.json`（已脱敏，见 [`../../config/napcat/config.redacted.json`](../../config/napcat/config.redacted.json)）：

| 键 | 值 | 说明 |
|---|---|---|
| `fileLog` | `false` | 不写文件日志，只在控制台打 |
| `consoleLog` | `true` | 控制台输出开着 |
| `fileLogLevel` / `consoleLogLevel` | `debug` / `info` | |
| `packetBackend` | `auto` | 自动选封包后端 |
| `o3HookMode` | `1` | Hook 注入模式 |
| `bypass.*` | 全 `false` | 不做任何绕过 |
| `autoTimeSync` | `true` | 自动校时（很重要，时间偏了会导致登录失败） |

## 网络配置

`napcat_protocol_<BOT_QQ>.json` 在本机是**关闭状态**：

```json
{
  "enable": false,
  "network": { "httpServers": [], "websocketServers": [], "websocketClients": [] }
}
```

这不代表没连上。实际的反向连接由 AstrBot 侧主动发起（AstrBot 是 WS **服务端**，NapCat 作为**客户端**连过来）。所以真正定义连接的是 AstrBot 的 `config/astrbot/platform.json`：

```json
{
  "id": "大肥鱼",
  "type": "aiocqhttp",
  "enable": true,
  "ws_reverse_host": "127.0.0.1",
  "ws_reverse_port": 6199,
  "ws_reverse_token": "<REDACTED>"
}
```

如果要在 NapCat 侧改成主动连（教程里教的另一种做法），就在上面那个 `websocketClients` 数组里加一条：

```json
{
  "enable": true,
  "name": "astrbot",
  "url": "ws://127.0.0.1:6199/ws",
  "token": "<与 AstrBot 里填的一样>",
  "heartbeatInterval": 1000,
  "reconnectInterval": 1000
}
```

两种做法二选一，**不要同时开**，否则同一条消息会被处理两次。

## 常见坑

1. **URL 里的冒号打成中文冒号** —— `ws://127.0.0.1：6199` 连不上，报错还很含糊。
2. **末尾斜杠漏了** —— 部分版本要求 `ws://127.0.0.1:6199/ws/`。
3. **两边 token 不一致** —— 一边改了另一边忘了。
4. **端口被占** —— 检查 `Get-NetTCPConnection -LocalPort 6199`。
5. **登录数据没刷新** —— 换号后要清 `napcat` 缓存目录重扫一次。

## 验证连接

连上之后 AstrBot 日志会出现适配器已连接的记录。也可以直接看 NapCat 的 `quick-login.log`，里面有 `接收 <- 私聊` 和 `发送 -> 私聊` 的行。
