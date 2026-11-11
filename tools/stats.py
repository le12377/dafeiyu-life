# -*- coding: utf-8 -*-
"""
大肥鱼一生统计：从本机数据库聚合「配置+统计」层数据，产出脱敏统计 JSON。
不导出任何聊天原文——只出计数、日期、模型名、token 量。
真实账号从 tools/secrets.local.json 读取。
用法：python stats.py [--owner-alias]
"""
import json, os, io, sqlite3, datetime, re, csv, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SEC = json.load(io.open(os.path.join(HERE, 'secrets.local.json'), encoding='utf-8'))

BASE = SEC['astrbot_root']
DATA = os.path.join(BASE, 'core', 'data')
OUT = os.path.join(ROOT, 'stats')
OWNER = SEC['owner_qq']
OWNER_ALIAS = '--owner-alias' in sys.argv
os.makedirs(OUT, exist_ok=True)

def ro(db):
    return sqlite3.connect('file:' + db.replace('\\', '/') + '?mode=ro', uri=True)

def day(ts):
    return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')

# ---------- 每日活跃度（仅计数） ----------
sl = ro(os.path.join(DATA, r'plugin_data\astrbot_plugin_self_learning\messages.db'))
c = sl.cursor()
daymap = {}
for ts, sid in c.execute('select timestamp, sender_id from raw_messages'):
    d = day(ts)
    e = daymap.setdefault(d, {'owner_msgs': 0, 'guest_msgs': 0})
    if str(sid) == OWNER:
        e['owner_msgs'] += 1
    else:
        e['guest_msgs'] += 1
botday = {}
for (ts,) in c.execute('select timestamp from bot_messages'):
    d = day(ts)
    botday[d] = botday.get(d, 0) + 1
moodday = {}
for ts, mt, mi in c.execute('select timestamp, mood_type, mood_intensity from bot_mood'):
    d = day(ts)
    m = moodday.setdefault(d, {})
    m[mt] = m.get(mt, 0) + 1
expr = c.execute('select count(*) from expression_patterns').fetchone()[0]
jarg = c.execute('select count(*) from jargon').fetchone()[0]
raw_rng = c.execute('select min(timestamp), max(timestamp) from raw_messages').fetchone()
bot_total = c.execute('select count(*) from bot_messages').fetchone()[0]
owner_total = sum(v['owner_msgs'] for v in daymap.values())
guest_total = sum(v['guest_msgs'] for v in daymap.values())
sl.close()

# ---------- 记忆规模 ----------
lm = ro(os.path.join(DATA, r'plugin_data\astrbot_plugin_livingmemory\livingmemory.db'))
c = lm.cursor()
mem_docs = []
for ca, md in c.execute('select created_at, metadata from documents'):
    try:
        j = json.loads(md) if md else {}
    except Exception:
        j = {}
    mem_docs.append((str(ca)[:10], j.get('importance')))
memday = {}
for d, imp in mem_docs:
    e = memday.setdefault(d, {'n': 0, 'imp_sum': 0.0})
    e['n'] += 1
    try:
        e['imp_sum'] += float(imp or 0)
    except Exception:
        pass
atoms = c.execute('select count(*) from memory_atoms').fetchone()[0]
gnodes = c.execute('select count(*) from graph_nodes').fetchone()[0]
gedges = c.execute('select count(*) from graph_edges').fetchone()[0]
gentries = c.execute('select count(*) from graph_entries').fetchone()[0]
node_types = dict(c.execute('select node_type, count(*) from graph_nodes group by 1'))
rel_types = dict(c.execute('select relation_type, count(*) from graph_edges group by 1'))
lm.close()

# ---------- 会话窗口（仅别名+计数） ----------
cv = ro(os.path.join(DATA, r'plugin_data\astrbot_plugin_livingmemory\conversations.db'))
c = cv.cursor()
def alias(s):
    if OWNER in s:
        return 'OWNER'
    if 'webchat' in s:
        return 'WEBCHAT'
    return 'GUEST'
sessions = [{'session_alias': alias(s), 'messages': n, 'first': day(c1), 'last': day(c2)}
            for s, n, c1, c2 in c.execute(
                'select session_id, count(*), min(timestamp), max(timestamp) from messages group by session_id order by min(timestamp)')]
cv.close()

# ---------- token 用量 ----------
ab = ro(os.path.join(DATA, 'data_v4.db'))
c = ab.cursor()
tokday = {}
for ts, ti, tc, to in c.execute('select start_time, token_input_other, token_input_cached, token_output from provider_stats'):
    if ts is None:
        continue
    d = day(ts)
    e = tokday.setdefault(d, {'calls': 0, 'in': 0, 'cached': 0, 'out': 0})
    e['calls'] += 1
    e['in'] += ti or 0
    e['cached'] += tc or 0
    e['out'] += to or 0
bymodel = [dict(zip(['provider_model', 'calls', 'input', 'cached', 'output'], r))
           for r in c.execute('select provider_model, count(*), sum(token_input_other), sum(token_input_cached), sum(token_output) from provider_stats group by 1 order by 2 desc')]
conv_ab = [{'alias': alias(u or ''), 'created': (c1 or '')[:10], 'updated': (c2 or '')[:10], 'tokens': tk}
           for u, c1, c2, tk in c.execute('select user_id, created_at, updated_at, token_usage from conversations order by created_at')]
ab.close()

# ---------- 媒体计数 ----------
imgs_dir = os.path.join(BASE, 'core', 'workspace', 'outputs', 'images')
imgdays = {}
for f in os.listdir(imgs_dir):
    m = re.match(r'(\d{8})-', f)
    if m:
        d = datetime.datetime.strptime(m.group(1), '%Y%m%d').strftime('%Y-%m-%d')
        imgdays[d] = imgdays.get(d, 0) + 1
ttsh = {}
for f in os.listdir(os.path.join(DATA, 'temp')):
    m = re.match(r'openai_tts_api_(\d{8})', f)
    if m:
        d = datetime.datetime.strptime(m.group(1), '%Y%m%d').strftime('%Y-%m-%d')
        ttsh[d] = ttsh.get(d, 0) + 1
tts_total = sum(ttsh.values())

qz = ro(os.path.join(DATA, r'plugin_data\astrbot_plugin_qzone\posts_5.db'))
qz_recent = [{'day': day(tm), 'chars': len(t or '')}
             for t, tm in qz.execute('select text, create_time from posts where create_time > 1750000000 order by create_time')]
qz.close()

# ---------- 合并时间线 ----------
alldays = sorted(set(list(daymap) + list(botday) + list(memday) + list(tokday) + list(moodday)
                     + list(imgdays) + list(ttsh)))
timeline = []
for d in alldays:
    e = {
        'date': d,
        'owner_msgs': daymap.get(d, {}).get('owner_msgs', 0),
        'guest_msgs': daymap.get(d, {}).get('guest_msgs', 0),
        'bot_msgs': botday.get(d, 0),
        'memories_written': memday.get(d, {}).get('n', 0),
        'avg_memory_importance': round(memday[d]['imp_sum'] / memday[d]['n'], 3) if d in memday and memday[d]['n'] else None,
        'llm_calls': tokday.get(d, {}).get('calls', 0),
        'tokens_input': tokday.get(d, {}).get('in', 0),
        'tokens_cached': tokday.get(d, {}).get('cached', 0),
        'tokens_output': tokday.get(d, {}).get('out', 0),
        'images_generated': imgdays.get(d, 0),
        'tts_voices': ttsh.get(d, 0),
        'moods': moodday.get(d, {}),
    }
    timeline.append(e)

tot_in = sum(v['in'] for v in tokday.values())
tot_cached = sum(v['cached'] for v in tokday.values())
tot_out = sum(v['out'] for v in tokday.values())
tot_calls = sum(v['calls'] for v in tokday.values())

summary = {
    'generated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
    'note': '本文件只含计数与日期，不含任何聊天原文。',
    'lifespan': {'first_record': alldays[0], 'last_record': alldays[-1], 'days': len(alldays)},
    'messages': {'owner_to_bot': owner_total, 'guests_to_bot': guest_total, 'bot_replies': bot_total,
                 'capture_range': [day(raw_rng[0]), day(raw_rng[1])]},
    'memory': {'episodic_documents': len(mem_docs), 'memory_atoms': atoms,
               'graph_nodes': gnodes, 'graph_edges': gedges, 'graph_entries': gentries,
               'node_types': node_types, 'relation_types': rel_types},
    'learning': {'expression_patterns': expr, 'jargon_entries': jarg},
    'tokens': {'total_llm_calls': tot_calls, 'input': tot_in, 'cached_input': tot_cached, 'output': tot_out,
               'cache_hit_rate': round(tot_cached / (tot_in + tot_cached), 4) if (tot_in + tot_cached) else None},
    'by_model': bymodel,
    'sessions': sessions,
    'astrbot_conversations': conv_ab,
    'media': {'images_generated_total': sum(imgdays.values()), 'tts_wav_total': tts_total,
              'images_by_day': imgdays, 'tts_by_day': ttsh},
    'qzone_posts_recent': qz_recent,
}

def scrub(s):
    s = s.replace(OWNER, '<OWNER_QQ>') if OWNER_ALIAS else s
    for q in SEC['guest_qq']:
        s = s.replace(q, '<GUEST>')
    s = s.replace(SEC['bot_qq'], '<BOT_QQ>')
    for a, b in SEC['path_map']:
        s = s.replace(a, b)
    return s

def dump_json(obj, name):
    """先 scrub 再落盘，避免句柄未关就二次覆盖导致写空。"""
    text = scrub(json.dumps(obj, ensure_ascii=False, indent=2))
    with io.open(os.path.join(OUT, name), 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)

dump_json(summary, 'summary.json')
dump_json(timeline, 'daily_timeline.json')
with io.open(os.path.join(OUT, 'daily_timeline.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    wr = csv.writer(f)
    wr.writerow(['日期', '主人发言', '访客发言', '大肥鱼回复', '写入记忆', '记忆均重要度', 'LLM调用',
                 '输入token', '缓存命中token', '输出token', '生成图', '语音条', '心情分布'])
    for e in timeline:
        wr.writerow([e['date'], e['owner_msgs'], e['guest_msgs'], e['bot_msgs'], e['memories_written'],
                     e['avg_memory_importance'], e['llm_calls'], e['tokens_input'], e['tokens_cached'],
                     e['tokens_output'], e['images_generated'], e['tts_voices'],
                     ' '.join('%s×%d' % kv for kv in sorted(e['moods'].items()))])

print('STATS ->', OUT)
print('days:', len(alldays), '| llm calls:', tot_calls, '| in:', tot_in, '| cached:', tot_cached, '| out:', tot_out)
print('owner msgs:', owner_total, '| guest msgs:', guest_total, '| bot msgs:', bot_total)
print('images:', sum(imgdays.values()), '| tts:', tts_total, '| memories:', len(mem_docs))
