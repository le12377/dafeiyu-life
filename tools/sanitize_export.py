# -*- coding: utf-8 -*-
"""
脱敏导出器：把本机大肥鱼的全部配置导出成可公开版本。

真实值一律从 tools/secrets.local.json 读取（该文件被 .gitignore 排除）。
原则：
  1. 密钥/令牌/密码/cookie/哈希 → <REDACTED:类型 len=N>（保留长度便于核对）
  2. 外部接入地址 → <YOUR_API_BASE>；本地回环与内网地址保留（教程必需）
  3. 第三方访客 QQ → <GUEST-A>/<GUEST-B>；机器人小号 → <BOT_QQ>；主人号默认保留
  4. 绝对路径 → <ASTRBOT_ROOT>/<HOME>/<COMFY_ROOT>/...（含 JSON 双反斜杠形态）
  5. 聊天原文一律不导出（只公开配置与统计）

用法：python sanitize_export.py [--owner-alias]
  主人 QQ 号保留原文，不做替换
"""
import json, os, io, re, sqlite3, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SEC = json.load(io.open(os.path.join(HERE, 'secrets.local.json'), encoding='utf-8'))

BASE = SEC['astrbot_root']
CORE = os.path.join(BASE, 'core')
DATA = os.path.join(CORE, 'data')
PUB = os.path.join(ROOT, 'config')

OWNER = SEC['owner_qq']
BOT_QQ = SEC['bot_qq']
GUESTS = {q: '<GUEST-%s>' % chr(ord('A') + i) for i, q in enumerate(SEC['guest_qq'])}
WS_TOKEN = SEC['ws_reverse_token']
OBSIDIAN_TOKEN = SEC['obsidian_token']
ENDPOINT_URLS = SEC['endpoint_urls']
ENDPOINT_DOMAINS = SEC['endpoint_domains']
PATH_MAP = [(a, b) for a, b in SEC['path_map']]

OWNER_ALIAS = '--owner-alias' in sys.argv

SECRET_FIELD = re.compile(
    r'(^|_)(api_?key|apikey|secret|access_key|secret_access_key|password|passwd|passphrase|'
    r'token|cookie|sessdata|bili_jct|dedeuserid|refresh_token|access_token|jwt|checksum|'
    r'hash|credential|totp|recovery|auth_key|ws_reverse_token|webui_initial_password|'
    r'password_hash|third_party_api_key|pixiv_refresh_token|newapi_base_url)(_|$)', re.I)

HEX_SECRET = re.compile(r'\b[0-9a-fA-F]{24,}\b')
PREFIXED_SECRET = re.compile(r'^(sk|nvapi|pk|whsec|ghp|gho|github_pat)-[A-Za-z0-9_\-]{10,}$')
ENTROPY_SECRET = re.compile(r'^(?=.*[a-z])(?=.*[A-Z0-9])[A-Za-z0-9+/]{20,}={0,2}$')

def _is_secret_value(s):
    if PREFIXED_SECRET.match(s) or HEX_SECRET.fullmatch(s):
        return True
    if ENTROPY_SECRET.match(s) and not re.search(r'[_\-.]', s):
        return True
    return False

def _kind_of(field):
    f = (field or '').lower()
    if 'password' in f or 'passwd' in f or 'passphrase' in f:
        return 'password'
    if 'token' in f:
        return 'token'
    if 'cookie' in f or 'sessdata' in f or 'jct' in f or 'userid' in f:
        return 'cookie'
    if 'hash' in f or 'checksum' in f:
        return 'hash'
    if 'key' in f:
        return 'api-key'
    if 'secret' in f:
        return 'secret'
    return 'credential'

def _is_local_endpoint(s):
    return bool(re.match(r'^(https?://)?(127\.0\.0\.1|localhost|::1|\[::1\])(:|/|$)', s.strip()))

# 公共/官方服务域名：保留，否则配置失去参考价值
PUBLIC_HOSTS = (
    'donmai.us', 'bilibili.com', 'bilibili.tv', 'lolicon.app', 'hitokoto.cn',
    'qq.com', 'qzone.qq.com', 'music.163.com', 'novelai.net', 'huggingface.co',
    'github.com', 'githubusercontent.com', 'astrbot.cn', 'astrbot.app', 'pypi.org',
    'pythonhosted.org', 'deepseek.com', 'siliconflow.cn', 'openai.com', 'ollama.com',
    'modelscope.cn', 'hf-mirror.com', 'my.feishu.cn', 'kdocs.cn', 'qq.com.cn',
    # PyPI / npm 国内镜像：公共基础设施，不属于接入凭据
    'aliyun.com', 'tsinghua.edu.cn', 'ustc.edu.cn', 'douban.com', 'npmmirror.com',
    'tencentcloud.com', 'huaweicloud.com', 'azure.com', 'cloudflare.com',
)

# 私有网段 / 容器内网：不带凭据，保留结构更有参考价值
def _is_private_net(s):
    return bool(re.match(
        r'^(https?://)?(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|169\.254\.)', s.strip()))

# 纯路径/相对端点（如 /generate、/v1/images/generations）：不是接入凭据
def _is_bare_path(s):
    return bool(re.match(r'^(/|\./|\.\./)[\w\-./]*$', s.strip()))

def _host_of(s):
    m = re.search(r'^(?:https?://)?([^/:\s]+)', s.strip())
    return (m.group(1).lower() if m else '')

def _is_public_endpoint(s):
    h = _host_of(s)
    if not h:
        return True
    return any(h == p or h.endswith('.' + p) or p in h for p in PUBLIC_HOSTS)

def _is_endpoint_field(field):
    f = (field or '').lower()
    return bool(re.search(r'(api_base|base_url|endpoint|_url$|url_list|proxy_url)', f))

def redact(obj, field=''):
    if isinstance(obj, dict):
        return {k: redact(v, k) for k, v in obj.items()}
    if isinstance(obj, list):
        if SECRET_FIELD.search(field or ''):
            return ['<REDACTED:%s len=%d>' % (_kind_of(field), len(str(x))) for x in obj]
        if _is_endpoint_field(field):
            return [x if (isinstance(x, str) and _endpoint_ok(x)) else redact(x, field) for x in obj]
        return [redact(x, field) for x in obj]
    if isinstance(obj, str):
        s = obj.strip()
        # 接入地址：本机/内网/公共服务/纯路径保留，其余换成占位符
        if _is_endpoint_field(field) and s and not s.startswith('<'):
            return obj if _endpoint_ok(s) else '<YOUR_API_BASE>'
        if s and (SECRET_FIELD.search(field or '') or _is_secret_value(s)):
            kind = _kind_of(field) if SECRET_FIELD.search(field or '') else 'secret'
            return '<REDACTED:%s len=%d>' % (kind, len(s))
        return obj
    return obj

def _endpoint_ok(s):
    return (_is_local_endpoint(s) or _is_private_net(s) or _is_bare_path(s)
            or _is_public_endpoint(s))

def scrub_text(s):
    s = s.replace(os.path.basename(BASE), '<INSTANCE_ID>')
    s = s.replace(WS_TOKEN, '<REDACTED:account-password>')
    s = s.replace(OBSIDIAN_TOKEN, '<REDACTED:obsidian-token>')
    s = re.sub(r'sk-[A-Za-z0-9]{20,}', '<REDACTED:api-key>', s)
    s = re.sub(r'nvapi-[A-Za-z0-9]{20,}', '<REDACTED:api-key>', s)
    s = re.sub(r'Bearer\s+(?!<REDACTED)[A-Za-z0-9]{20,}', 'Bearer <REDACTED:token>', s)
    s = re.sub(r'pbkdf2_sha256\$(?!<)[\w$]{10,}', '<REDACTED:password-hash>', s)
    s = re.sub(r'(?i)(sessdata|bili_jct|dedeuserid)(["\']?\s*[:=]\s*["\']?)(?!<REDACTED)[A-Za-z0-9%*_\-]{12,}',
               r'\1\2<REDACTED:cookie>', s)
    for u in ENDPOINT_URLS:
        s = s.replace(u, '<YOUR_API_BASE>')
    for d in ENDPOINT_DOMAINS:
        s = s.replace(d, '<YOUR_API_BASE>')
    s = re.sub(r'https?://<YOUR_API_BASE>([\w.\-/]*)', '<YOUR_API_BASE>', s)
    s = s.replace(BOT_QQ, '<BOT_QQ>')
    for q, alias in GUESTS.items():
        s = s.replace(q, alias)
    # 主人号按用户要求保留原文（公开档案里作为锚点）
    for path, alias in PATH_MAP:
        s = s.replace(path.replace('\\', '\\\\'), alias)
        s = s.replace(path, alias)
    s = re.sub(r'[A-Za-z]:\\\\\\\\[\w\\\\.\-() ]+', '<REDACTED:abs-path>', s)
    s = re.sub(r'[A-Za-z]:\\[\w\\. \-()]+', '<REDACTED:abs-path>', s)
    # 作者名匿名（本机用户名不出现在插件元数据里）
    _uname = os.environ.get('USERNAME', '')
    if _uname:
        s = s.replace('author: ' + _uname, 'author: <SELF>')
        s = re.sub(r'"author":\s*"' + re.escape(_uname) + r'"',
                   '"author": "<SELF>"', s)
        # register() 调用等裸用户名形式："<用户名>", → "<SELF>",
        s = re.sub(r'"' + re.escape(_uname) + r'"', '"<SELF>"', s)
    # 文本级替换规则写在 secrets.local.json，避免把敏感字面量带进公开脚本
    for old, new in SEC.get('text_replacements', {}).items():
        s = s.replace(old, new)
    return s

def out(name, text):
    p = os.path.join(PUB, name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, 'w', encoding='utf-8', newline='\n').write(scrub_text(text))
    print('PUB', name, os.path.getsize(p))

def jdump(o):
    return json.dumps(o, ensure_ascii=False, indent=2)

def jread(p):
    return json.load(io.open(p, encoding='utf-8-sig'))

cfg_raw = jread(os.path.join(DATA, 'cmd_config.json'))
out('astrbot/cmd_config.json', jdump(redact(cfg_raw)))
out('astrbot/provider_sources.redacted.json', jdump(redact(cfg_raw.get('provider_sources', []))))
out('astrbot/platform.json', jdump(redact(cfg_raw.get('platform', {}))))
out('astrbot/mcp_server.json', jdump(redact(jread(os.path.join(DATA, 'mcp_server.json')))))
out('astrbot/skills.json', jdump(jread(os.path.join(DATA, 'skills.json'))))
out('astrbot/persona_pool_note.json', jdump({
    'note': 'persona 见 personas/ 目录；default persona 未定制',
    'wake_prefix': cfg_raw.get('wake_prefix'),
    'admins_id': [OWNER]}))

cfgdir = os.path.join(DATA, 'config')
for f in sorted(os.listdir(cfgdir)):
    if f.endswith('.json') and '.bak' not in f:
        try:
            j = jread(os.path.join(cfgdir, f))
        except Exception as e:
            print('skip', f, e); continue
        out('plugins/' + f.replace('_config.json', '.json'), jdump(redact(j)))

con = sqlite3.connect('file:' + os.path.join(DATA, 'data_v4.db').replace('\\', '/') + '?mode=ro', uri=True)
pers = list(con.execute('select persona_id, system_prompt, begin_dialogs, tools, skills, created_at from personas order by created_at'))
for pid, sp, bd, tools, skills, ca in pers:
    if pid in ('大肥鱼', '爱弥斯'):
        out('personas/%s.system_prompt.md' % pid, sp or '')
        out('personas/%s.begin_dialogs.json' % pid, jdump(json.loads(bd or '[]')))
        out('personas/%s.meta.json' % pid, jdump({
            'persona_id': pid, 'created_at': str(ca),
            'system_prompt_chars': len(sp or ''),
            'begin_dialogs_count': len(json.loads(bd or '[]')),
            'tools': tools, 'skills': skills}))
    else:
        out('personas/default.system_prompt.md', sp or '')
con.close()

for d in ('astrbot_plugin_dafeiyu_clean', 'astrbot_plugin_dafeiyu_signature',
          'astrbot_plugin_meme_marker_fix', 'astrbot_plugin_tts_wav_fix', 'astrbot_plugin_local_media_uri'):
    pdir = os.path.join(DATA, 'plugins', d)
    for root, dirs, files in os.walk(pdir):
        dirs[:] = [x for x in dirs if x != '__pycache__']
        for f in files:
            if f.endswith(('.py', '.yaml', '.json')) and '.bak' not in f:
                txt = io.open(os.path.join(root, f), encoding='utf-8', errors='replace').read()
                rel = os.path.relpath(os.path.join(root, f), pdir).replace('\\', '/')
                out('custom-plugins/%s/%s' % (d, rel), txt)

NAPDIR = os.path.join(os.path.expandvars(r'%USERPROFILE%'), 'Desktop', 'NapCat.52230.Shell',
                      'versions', '9.9.33-52230', 'resources', 'app', 'napcat', 'config')
nap = {}
if os.path.isdir(NAPDIR):
    for f in sorted(os.listdir(NAPDIR)):
        fp = os.path.join(NAPDIR, f)
        if os.path.isfile(fp) and f.endswith('.json'):
            try:
                nap[f] = jread(fp)
            except Exception as e:
                print('napcat skip', f, e)
    out('napcat/config.redacted.json', jdump({'version': '9.9.33-52230', 'configs': redact(nap)}))
    # 安装根目录：从 ...\versions\<ver>\resources\app\napcat\config 上推 6 层
    qb = NAPDIR
    for _ in range(6):
        qb = os.path.dirname(qb)
    qb = os.path.join(qb, 'napcat.quick.bat')
    if os.path.exists(qb):
        out('napcat/quick-login.bat.redacted', io.open(qb, encoding='gbk', errors='replace').read())
    else:
        print('napcat quick-login not found:', qb)

BREEZE = SEC.get('breeze_root') or r'<BREEZE_ROOT>'
sb = os.path.join(BREEZE, 'start-breeze.cmd')
if os.path.exists(sb):
    out('environment/start-breeze.cmd', io.open(sb, encoding='gbk', errors='replace').read())

env = {
    'os': 'Windows (x64)',
    'astrbot_launcher': os.path.join(BASE, '..', '..', 'astrbot-launcher.exe'),
    'astrbot_core_version': '4.29.4',
    'astrbot_instances': [os.path.basename(BASE)],
    'python': '3.12.16（launcher 内置 py312 + 实例 venv）',
    'node': 'launcher 内置 components/nodejs',
    'uv': 'launcher 内置 components/uv',
    'napcat': 'NapCat.52230.Shell（OneBot v11，反向 WebSocket），登录的是小号',
    'comfyui': r'<COMFY_ROOT>\ComfyUI-Installs\ComfyUI (1) standalone-env，端口 8188',
    'breeze_tts': 'breeze-tts-2 v0.1.3 windows-x64-vulkan，端口 8137，模型 breeze-tts-2-q8_0.gguf（3.57GB），音色 dafeiyu.breeze',
    'embedding': 'Ollama bge-m3 1024 维（本机 127.0.0.1:11434）',
    'obsidian_vault': '<OBSIDIAN_VAULT>（Local REST API + mcp-remote）',
    'ports': {'astrbot_dashboard': 6185, 'astrbot_ws_reverse': 6199, 'comfyui': 8188,
              'breeze_tts': 8137, 'ollama': 11434, 'obsidian_rest': 27124,
              'self_learning_webui': 7833, 'pc_webui': 6190, 'proactive_webui': 4100},
    'qq_accounts': {'owner': OWNER, 'bot': BOT_QQ, 'guests_seen': list(GUESTS)},
}
out('environment/runtime.json', jdump(env))

meta = jread(os.path.join(ROOT, '_staging', 'installed_plugins_meta.json'))
out('plugins/PLUGIN_LIST.json', jdump(meta))
print('DONE ->', PUB)
