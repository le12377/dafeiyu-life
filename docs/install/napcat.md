# 安装 NapCat

NapCat 负责把 QQ 变成 OneBot 接口。教程里说的「找带 OneKey 的 Windows 一键包」就是这个。

## 0. 官方地址

| 用途 | 地址 |
|---|---|
| **发布页（下载在这）** | https://github.com/NapNeko/NapCatQQ/releases |
| 仓库主页 | https://github.com/NapNeko/NapCatQQ |
| 使用文档 | https://napneko.github.io/guide/boot/Shell |
| 桌面管理工具 | https://github.com/NapNeko/NapCatQQ-Desktop |

组织名是 **NapNeko**，仓库名 **NapCatQQ**。搜的时候注意别搜到同名的加密钱包项目（那个也叫 OneKey）。

## 1. 下载

打开发布页 https://github.com/NapNeko/NapCatQQ/releases ，在最新一版的 **Assets** 里找这个文件：

```
NapCat.Shell.Windows.OneKey.zip
```

这就是**一键包**。它的特点：

- 内置了 QQ 本体，**不需要你事先装 QQ**
- 下载 QQ 时会依次尝试官方 CDN 和 GitHub 镜像，并校验 SHA256
- 适用于 Windows **amd64**

**别下这些**：

| 文件名 | 是什么 | 为什么不要 |
|---|---|---|
| `NapCat.Shell.zip` | 普通 Shell 版 | 需要你自己先装 QQ，还要配 `launcher.bat` |
| `NapCat.Shell.Windows.OneKey.zip` ✅ | **一键包，要的就是它** | 内置 QQ，装完直接能用 |
| Linux / AppImage / Docker 相关 | 其他平台 | 你是 Windows 就用不上 |

**版本说明**：官方提示推荐 QQ **40768+** 版本，最低 40768。本机一键包里内置的是 QQ **9.9.33-52230**（比 40768 新），没问题。

**官方文档里的标准流程**（和我下面写的一致）：

1. 下载并解压 `NapCat.Shell.Windows.OneKey.zip`
2. 运行 `NapCatInstaller.exe`，完成后进入 `NapCat.XXXX.Shell` 目录
3. 双击 `napcat.bat` 启动

## 2. 解压

右键压缩包 → 全部解压缩 → 目标目录改成 **纯英文路径**，比如：

```
D:\NapCat
```

本机是解压在桌面的 `NapCat.52230.Shell`。

**为什么不能放中文路径**：NapCat 内部会拉起 QQ 的进程，路径里有中文或空格时，注入 hook 那一步容易失败。

## 3. 装 QQ

解压后双击里面的 **`NapCatInstaller.exe`**（安装器）。

装完后目录会变成 `NapCat.XXXX.Shell`（XXXX 是 QQ 版本号，本机是 `NapCat.52230.Shell`）。

这个安装器会：

1. 自动去下载 QQ 本体（官方 CDN 失败时走 GitHub 镜像）
2. 校验 SHA256
3. 把 NapCat 环境配齐（注入 dll、写配置）
4. 完事后显示「安装完成」

**它装的是一个独立的 QQ**，会自带一套用户数据目录，**不影响你平时电脑上挂的大号 QQ**。本机装的是 QQ **9.9.33-52230**。

**Windows Server 用户注意**：需要先装「媒体基础」组件，否则启动时报 `The specified module could not be found`。在服务器管理器「添加角色和功能」里勾「媒体基础」，或用管理员 PowerShell：

```powershell
Install-WindowsFeature Server-Media-Foundation
```

装完重启再启动。

## 4. 解压后的目录结构

安装前只有 `NapCatInstaller.exe`，装完后才是这样：

```
NapCat.52230.Shell/
├── NapCatInstaller.exe       ← 安装器（装完后还在，可以重跑）
├── NapCatWinBootMain.exe     ← 启动器
├── NapCatWinBootHook.dll     ← 注入用的 hook
├── QQ.exe                    ← 小号专用 QQ（1.7MB，是个 loader）
├── napcat.bat                ← 普通启动（每次要扫码）
├── napcat.quick.bat          ← 免扫码快登
├── napcat.kill.qq.bat        ← 强杀 QQ 进程
├── versions/9.9.33-52230/
│   └── resources/app/napcat/
│       ├── config/
│       │   ├── napcat_<QQ号>.json            ← 全局行为配置
│       │   └── napcat_protocol_<QQ号>.json   ← 网络配置
│       └── ...
├── quick-login.log           ← 收发消息日志
└── ReadMe.txt
```

**目录名里的数字**（`NapCat.52230` 的 `52230`）是 QQ 版本后缀，和 `versions/` 下的目录名 `9.9.33-52230` 对得上。

**两个 QQ 配置文件是按 QQ 号命名的**。所以同一个 NapCat 目录可以存多个号的配置，切换号时会自动读对应的那份。

## 5. 首次登录

双击 `napcat.bat`（不是 quick 那个，第一次还没有登录数据）：

1. 弹出一个黑框
2. 黑框里出现一个**二维码**
3. 用手机上的 QQ 小号扫它
4. 扫码成功后它会刷登录数据
5. 黑框不能关，最小化就行

**关掉黑框 = 掉线**。QQ 和 NapCat 是父子进程，父进程没了子进程跟着走。

扫码成功后，目录里会多出 `napcat_protocol_<QQ号>.json` 和登录缓存。

## 6. 配免扫码快登

扫过一次码之后，就可以做免扫码了。新建或改 `napcat.quick.bat`：

```bat
@echo off
chcp 65001 >nul
setlocal
set "NAPCAT_QUICK_ACCOUNT=<BOT_QQ>"
set "NAPCAT_QUICK_PASSWORD=<QQ密码>"
.\NapCatWinBootMain.exe <BOT_QQ>
pause
```

两个变量的意思：

- `NAPCAT_QUICK_ACCOUNT`：小号 QQ 号
- `NAPCAT_QUICK_PASSWORD`：小号 QQ 的密码

**注意 `chcp 65001`**：这是把控制台代码页切成 UTF-8，不然中文日志会变乱码。

**注意 `pause`**：留着它，出错时黑框不会一闪就消失，能看到错误信息。

本机的真实值已经脱敏，见 [`../../config/napcat/quick-login.bat.redacted`](../../config/napcat/quick-login.bat.redacted)。

## 7. 配置反连

NapCat 有两种连 AstrBot 的方向，**二选一**。

### 方式 A：AstrBot 做服务端（本机用的这个）

AstrBot 侧：

```json
{
  "id": "大肥鱼",
  "type": "aiocqhttp",
  "enable": true,
  "ws_reverse_host": "127.0.0.1",
  "ws_reverse_port": 6199,
  "ws_reverse_token": "<自定>"
}
```

NapCat 侧什么都不用配。启动后它会自己连过来。

### 方式 B：NapCat 主动连

NapCat 的黑框里会打出自己的后台地址，浏览器打开它，左侧「网络配置」→「新建」→ 选 **WebSocket 客户端**：

| 字段 | 填什么 |
|---|---|
| 启用 | 打开 |
| 名称 | 随便，比如 `astrbot` |
| URL | `ws://127.0.0.1:6199/ws` |
| 密码/token | 和 AstrBot 里那个一模一样 |
| 心跳间隔 | `1000` |
| 重连间隔 | `1000` |

对应的配置文件是 `napcat_protocol_<QQ号>.json`：

```json
{
  "enable": true,
  "network": {
    "websocketClients": [{
      "enable": true,
      "name": "astrbot",
      "url": "ws://127.0.0.1:6199/ws",
      "token": "<同上>",
      "heartbeatInterval": 1000,
      "reconnectInterval": 1000
    }]
  }
}
```

### 本机实际是什么状态

本机的 `napcat_protocol_<QQ号>.json` 是**全关的**：

```json
{ "enable": false, "network": { "httpServers": [], "websocketServers": [], "websocketClients": [] } }
```

因为用的是方式 A，连接由 AstrBot 主动建立，NapCat 侧不需要任何客户端配置。如果你照抄本机配置却发现连不上，先确认你的 AstrBot 是不是也在做服务端。

## 8. 验证

连上之后，两处都能看到证据：

**AstrBot 侧**：后台「数据与日志」里搜「适配器已连接」或 `aiocqhttp`。

**NapCat 侧**：`quick-login.log` 里会有这样的行：

```
大肥鱼 | 接收 <- 私聊 (###) 再发一张
大肥鱼 | 发送 -> 私聊 (###) 来啦，最后一张给你。
```

前缀那个「大肥鱼」是机器人昵称，说明连接是通的、消息是双向的。

**最终验证**：拿你的大号给小号发一条消息，能收到回复就全通了。

## 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| 二维码刷不出来 | 网络 / QQ 版本不对 | 换 `napcat.kill.qq.bat` 杀干净再启 |
| 扫码后一直不跳转 | 登录数据没写入 | 清 `versions/.../config` 下的缓存目录，重扫 |
| 连不上 AstrBot | URL 冒号打成中文冒号 | 检查 `：` vs `:` |
| 连不上 AstrBot | 末尾少斜杠 | 试 `ws://127.0.0.1:6199/ws/` |
| 连不上 AstrBot | 两边 token 不一样 | 逐字符对 |
| 端口被占 | 上次没退干净 | `Get-NetTCPConnection -LocalPort 6199` 查出进程再杀 |
| 消息重复 | 方向配了两次 | 方式 A 和 B 只能选一个 |
| 时间漂移导致登录失败 | 系统时间不准 | 保持 `autoTimeSync: true` |
