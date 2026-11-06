# tools · 脚本说明

脚本从当前生效的配置机械导出，不手抄。改完本机配置后重跑一遍即可。

```powershell
# 用 AstrBot 实例自带的 Python
$py = '<ASTRBOT_ROOT>\venv\Scripts\python.exe'

& $py tools\stats.py              # 重算 stats/
& $py tools\sanitize_export.py    # 重新导出 config/
& $py tools\secret_scan.py        # 发布前扫描
```

| 脚本 | 读什么 | 写什么 |
|---|---|---|
| `stats.py` | 4 个 SQLite 库 | `stats/` 三个文件 |
| `sanitize_export.py` | cmd_config、插件配置、personas、自写插件源码、NapCat/Breeze 配置 | `config/` |
| `secret_scan.py` | 整个仓库 | 无（只扫不改） |

## 真实值放哪

`secrets.local.json`（**已被 gitignore 排除，不要提交**）存着：

- 你的 QQ 号、机器人小号、访客号
- 反向 WS token、Obsidian token
- 中转站域名与地址
- 本机路径映射表

新环境照抄 `secrets.local.example.json` 填自己的值。

## 接入地址的处理口径

凡是 `api_base` / `base_url` / `*_endpoint` / `*_url` 这类字段：

| 类型 | 处理 |
|---|---|
| 本机回环（127.0.0.1） | 保留 |
| 私有网段（10. / 192.168. / 172.16-31.） | 保留 |
| 纯路径（`/generate`、`/v1/images/generations`） | 保留 |
| 公共镜像（PyPI、npm、B站、danbooru 等） | 保留 |
| 自建中转的域名/地址 | 换成 `<YOUR_API_BASE>`，一个字符不留 |

## 转公开仓库

```powershell
& $py tools\sanitize_export.py --owner-alias   # 连主人 QQ 号也匿名
& $py tools\secret_scan.py --strict            # 必须输出 CLEAN
```

`_staging/` 是本机中间产物（含聊天原文），不入库，已 gitignore。
