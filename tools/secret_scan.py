# -*- coding: utf-8 -*-
"""
公开发布前的最后一道闸：扫描仓库里（除 tools/ 外）是否残留真实密钥或账号。
真实值从 tools/secrets.local.json 读取；tools/ 目录本身不入库。
退出码 0 = 干净，1 = 有命中（必须人工确认后才能 push）。
"""
import os, io, re, sys, json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SEC = json.load(io.open(os.path.join(HERE, 'secrets.local.json'), encoding='utf-8'))
OWNER = SEC['owner_qq']
STRICT = '--strict' in sys.argv   # 严格模式：连主人号、本机绝对路径也算命中

PATTERNS = [
    ('sk-api-key', re.compile(r'\bsk-[A-Za-z0-9]{20,}')),
    ('nvapi-key', re.compile(r'\bnvapi-[A-Za-z0-9]{20,}')),
    ('bearer-token', re.compile(r'Bearer\s+(?!<REDACTED)[A-Za-z0-9]{20,}')),
    ('pbkdf2-hash', re.compile(r'pbkdf2_sha256\$(?!<)[\w$]{10,}')),
    ('hex-secret', re.compile(r'\b[0-9a-f]{32,}\b')),
    ('sessdata-cookie', re.compile(r'sessdata["\']?\s*[:=]\s*["\']?(?!<REDACTED)[A-Za-z0-9%*_\-]{12,}', re.I)),
    ('relay-domain', re.compile('|'.join(re.escape(d) for d in SEC['relay_domains']))),
    ('quoted-secret-field', re.compile(
        r'"(?:api_key|apikey|token|password|secret|refresh_token|access_key|secret_access_key|jwt_secret|ws_reverse_token)"'
        r'\s*:\s*"(?!<REDACTED|%|unused|ollama|auto|local|)[A-Za-z0-9$+/=_\-]{16,}"', re.I)),
    ('ws-token', re.compile(re.escape(SEC['ws_reverse_token']))),
    ('obsidian-token', re.compile(SEC['obsidian_token'][:12])),
    ('guest-qq', re.compile(r'\b(%s)\b' % '|'.join(SEC['guest_qq']))),
    ('bot-qq', re.compile(r'\b%s\b' % SEC['bot_qq'])),
    ('astrbot-instance-guid', re.compile(r'\b' + re.escape(os.path.basename(SEC['astrbot_root'])) + r'\b')),
    # 接入地址字段里，除了白名单（本机/内网/公共镜像/纯路径），不允许出现任何真实域名
    ('unredacted-endpoint', re.compile(
        r'"(?:api_base|base_url|api_url|embedding_api_base|nai_endpoint|openai_base_url|'
        r'openai_image_endpoint|openai_edit_endpoint|nodejs_base_url|remote_repo_url|'
        r'newapi_base_url|balance_api_url|WEB_EXPLORATION_API_BASE_URL|EXTERNAL_IMAGE_API_BASE_URL)"'
        r'\s*:\s*"(?!<YOUR_API_BASE>|<REDACTED|)(?:https?://)?(?!127\.0\.0\.1|localhost|10\.|192\.168\.|'
        r'172\.(?:1[6-9]|2\d|3[01])\.|/)[^"]{4,}"', re.I)),
]
# 主人号按用户决定公开，不再作为违规项检查
if STRICT:
    PATTERNS.append(('abs-path', re.compile(r'\b[A-Za-z]:[\\/]{1,2}(Users|AstrBot|Comfy|breeze|Program)', re.I)))

hits = {}
for root, dirs, files in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in ('.git', '_staging')]
    for f in files:
        p = os.path.join(root, f)
        rel_now = os.path.relpath(p, ROOT).replace('\\', '/')
        if rel_now == 'tools/secrets.local.json':
            continue  # 本机真值，已被 .gitignore 排除
        if STRICT and rel_now.startswith('tools/'):
            continue  # 脚本里必然出现本机路径，strict 模式只看发布目录
        if os.path.getsize(p) > 20 * 1024 * 1024:
            continue
        if f.endswith(('.jpg', '.png', '.wav', '.m4a', '.gif')):
            continue
        try:
            txt = io.open(p, encoding='utf-8', errors='replace').read()
        except Exception:
            continue
        for name, pat in PATTERNS:
            for m in pat.finditer(txt):
                ln = txt[:m.start()].count('\n') + 1
                hits.setdefault((os.path.relpath(p, ROOT).replace('\\', '/'), name), []).append(
                    (ln, m.group(0)[:70]))

if not hits:
    print('CLEAN — 可以 push。(%s 模式)' % ('strict' if STRICT else 'default'))
    sys.exit(0)
print('=== 命中 %d 类，必须处理 ===' % len(hits))
for (rel, name), occ in sorted(hits.items()):
    print('%-62s %-20s x%d' % (rel, name, len(occ)))
    for ln, frag in occ[:2]:
        print('        L%-6d %s' % (ln, frag))
sys.exit(1)
