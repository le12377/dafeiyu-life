# 记忆系统

「清空聊天记录也还记得你」靠的是**持久化存储 + 双路向量召回**，不是靠模型上下文。

本文所有数字与结论都来自本机实测（数据库、FAISS 索引文件、插件源码、配置文件交叉核对），不是照抄文档。

---

## 一、先把「三层记忆」这个说法纠正掉

网上流传的「三层记忆」在本机**不成立**。LivingMemory 官方 `docs/architecture.md` 的原文：

> 长期记忆写入共享的 `documents` 表，细粒度事实写入 `memory_atoms`，图结构写入 `graph_*` 表，所有检索都经过 `MemoryEngine` 的公共 API。

所以真实结构是：

```
一份主存储（documents）
      +
一份细粒度事实（memory_atoms，只用来过滤）
      +
一套图结构（graph_nodes / edges / entries）
      ↓
两路并行召回：文档路 + 图谱路
```

`memory_atoms` **不是第三层**，它挂在记忆上做「原子过滤」，见第五节。

另外 `astrbot_plugin_self_learning` 是完全独立的插件，有自己的库和表达模式，不属于 LivingMemory —— 见第七节。


---

## 二、本机各表实测量

| 表 | 存什么 | 量 |
|---|---|---|
| `documents` | 长期记忆正文 + 元数据（情景小结） | **71 篇** |
| `memory_atoms` | 细粒度事实单元（带 TTL / 过期 / 衰减） | **295 条**（active 249 + expired 46） |
| `graph_nodes` | 实体节点 | **572** 个 |
| `graph_edges` | 实体关系 | **2065** 条 |
| `graph_entries` | 图条目（摘要 + 关系 + 来源） | **2360** 条 |
| `graph_entry_nodes` | 条目与节点映射 | 4425 条 |
| `memory_sources` | 记忆对应的原始消息 | 独立表，**不进检索、不做 embedding** |
| `decay_state.json` | 衰减游标 | `last_decay_date: 2026-11-06` |

`documents` 全部 `status = active`，没有一条被归档或删除。

---

## 三、两路检索到底怎么走（含 FAISS 实测）

| 检索路 | 数据来源 | 关键词检索 | 语义检索 | 本机索引文件 |
|---|---|---|---|---|
| **文档路** | `documents` | BM25（jieba 分词 + 中文连续段二元组） | **FAISS** | `livingmemory.index` |
| **图谱路** | `graph_*` | FTS5 trigram（短词回退普通匹配） | **FAISS** | `livingmemory_graph.index` |

### 3.1 FAISS 索引：向量确实落盘了

两个 FAISS 索引都在磁盘上：

| 索引文件 | 大小 | 维度 | 向量数 |
|---|---|---|---|
| `livingmemory.index` | 284.6 KB | **1024** | **71** |
| `livingmemory_graph.index` | 252.6 KB | **1024** | **63** |

直接解析文件头（`d=1024`、`ntotal=71/63`）得到的，和 `documents` 的 71 篇、图谱文档的 63 篇一一对应。**维度 1024 也对得上 bge-m3**。

### 3.2 向量是谁生成的——指纹反解

`migration_status` 里存着一个：

```
document_vector_provider_fingerprint =
<PROVIDER_FINGERPRINT:sha256>
```

这个值不是随机串。查 `index_validator.py` 的 `get_provider_fingerprint()`，它对 7 个字段做 `sha256`：

```python
payload = {
  "schema": "document-vector-v2",
  "provider_class": type(provider).__module__ + "." + type(provider).__qualname__,
  "provider_id": provider_config.get("id"),
  "provider_type": provider_config.get("type"),
  "model": ...,
  "dimension": ...,
  "dimensions_mode": provider_config.get("embedding_dimensions_mode"),
  "input_type": ...,
}
return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
```

我按这个算法**反向计算**，唯一命中的组合是：

| 字段 | 值 |
|---|---|
| provider_class | `OpenAIEmbeddingProvider` |
| provider_id | **`大肥鱼记忆-本机`** |
| provider_type | `openai_embedding` |
| model | **`bge-m3`** |
| dimension | **1024** |
| dimensions_mode | `auto` |

**结论**：这 71 条向量确实是用 `大肥鱼记忆-本机`（bge-m3，1024 维）算出来的，指纹完全吻合。

### 3.3 完整链路：从一句话到一条向量

一次写入的完整路径是这样：

```
用户发来一句话
      │
      ▼
session_manager 捕获（context_window_size: 20）
      │
      ▼
攒够 summary_trigger_rounds: 20 轮
      │
      ▼
大模型总结成一篇「情景记忆」（她自己口吻）
      │
      ├─▶ 写入 documents 表（正文 + metadata）
      │
      ├─▶ 调用嵌入服务算向量
      │      POST http://127.0.0.1:11434/v1/embeddings
      │      model: bge-m3  →  1024 维 float
      │
      ├─▶ 追加到 FAISS: livingmemory.index
      │
      ├─▶ 抽出原子写入 memory_atoms（带 TTL）
      │
      └─▶ 抽出实体与关系写入 graph_*
             │
             └─▶ 追加到 FAISS: livingmemory_graph.index
```

**七个环节，每一步都有本机的实际证据**：

| 环节 | 实现 | 本机证据 |
|---|---|---|
| 1. 捕获会话 | `session_manager.enable_full_group_capture` | `conversations.db` 395 条消息 |
| 2. 攒轮次 | `reflection_engine.summary_trigger_rounds: 20` | 71 篇，分布在 7 天 |
| 3. 总结成文 | 大模型写「叙述 + 事实清单」 | 每篇都是她自己口吻 |
| 4. 落库 | `documents` 表 | **71 篇**，全部 active |
| 5. 算向量 | Ollama `/v1/embeddings` + bge-m3 | 指纹反解 = `大肥鱼记忆-本机` |
| 6. 写 FAISS | `livingmemory.index` | **1024 维 / 71 条** |
| 7. 建图 | `graph_*` + `livingmemory_graph.index` | **572 节点 / 2065 边 / 1024 维 63 条** |

**读的时候反着走**：

```
用户发来一句话
      │
      ▼
同时启动两条路
      │
      ├─ 文档路 ──┬─ BM25 关键词（jieba 分词）
      │           └─ 向量检索 livingmemory.index
      │
      └─ 图谱路 ──┬─ FTS5 trigram
                  └─ 向量检索 livingmemory_graph.index
      │
      ▼
RRF 融合（文档 0.65 + 图谱 0.35 + 双命中加 0.08）
      │
      ▼
原子过滤（只留未过期且 active 的事实）
      │
      ▼
top_k 10 条拼进上下文，套上 memory_injection_header 的规则
      │
      ▼
大模型生成回复
```

### 3.4 嵌入服务是这条链上的一个环节

`bge-m3` 通过 Ollama 提供 `/v1/embeddings`，这是第 5 步的算力来源。它是个**常驻服务**，和 AstrBot 一样属于后台基础设施：

- 已建好的 71 条向量存在磁盘（`livingmemory.index`），读的时候不需要重算
- 新记忆要进来，第 5 步必须能调通嵌入服务
- 换模型或维度变了要整库重建，那一步更是全靠它

所以它的运行状态属于「服务有没有起」这一类日常运维问题，不是记忆机制本身的缺陷。忘了开就起一下：

```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama app.exe"
```

装完会注册开机自启，正常情况下登录后它就在托盘里，11434 端口常驻。

### 3.5 两路怎么加权

```json
{
  "graph_memory": {
    "enabled": true,
    "document_route_weight": 0.65,
    "graph_route_weight": 0.35,
    "cross_route_bonus": 0.08
  }
}
```

文档路 **0.65** + 图谱路 **0.35**，两路都命中再加 **0.08**。

源码（architecture.md）补充了动态调整：**关系类词把图谱权重 +0.2，时间类词 +0.1，定义/解释类词把文档权重 +0.15**，最后裁剪并归一化。

### 3.6 关键词与语义怎么融合

```json
{
  "recall_engine": {
    "top_k": 10,
    "fusion_bm25_weight": 0.5,
    "fusion_agreement_bonus": 0.25,
    "recent_memory_count": 2,
    "recent_memory_max_age_hours": 72,
    "min_similarity_for_retrieval": 0.0,
    "rerank_enabled": false
  }
}
```

- BM25 权重 **0.5**，剩下给语义
- 两路一致再加 **0.25**
- 不管查什么，**最近 72 小时内最多 2 条**总带进去 —— 保证她不会忘了刚聊的事
- `min_similarity_for_retrieval: 0.0` 表示**不过滤低分**，宁滥勿缺
- **重排是关的**（`rerank_enabled: false`）

### 3.7 全库混在一起，靠一段提示词区分身份

这一条是本机最关键的设置：

```json
"filtering_settings": {
  "memory_scope_mode": "global"
}
```

71 篇记忆**全部属于 `persona=大肥鱼`、`session=livingmemory:global`** —— 也就是说，无论你在私聊还是访客在私聊，召回池是**同一个**。

那她怎么不把访客的事安到你头上？靠 `prompts/memory_injection_header.txt` 这段注入提示（原文）：

> - 以下记忆是你（大肥鱼）与所有联系人共享的完整记忆库，包含你与不同人各自的对话。
> - 每条记忆都有它的"对象"：正文里出现的主人公称呼（如 (●—●) 与各访客的代称）指各自具体的人，不代表当前和你说话的人。
> - (●—●) / <OWNER_QQ> 永远是你的主人，记忆里的"主人、爸"一律指他；当前对话者是谁以本条消息附带的身份说明为准，两者可能不是同一个人。
> - 向当前对话者提起别人的记忆时，用"和XX聊过"的第三人称说法，不要把别人的经历安到当前对话者头上，也不要喊非主人的人"主人/爸/小小鱼"。

同一段开头还有全局规则：

> 1. These are PAST records — they already happened and are NOT part of the current conversation.
> 2. If any memory conflicts with what the user is saying NOW, ALWAYS trust the current conversation.

**这段话就是「她记得所有人的事，但分得清你是谁」的实现方式。**

---

## 四、情景记忆怎么写的

每篇两个部分：

1. **叙述** —— 她自己口吻的当天小结（不是用户原话）
2. **关键事实清单** —— 分号隔开、带时间戳的独立事实

**一条代表案例**（脱敏、已删减）：

> 主人发了张围裙印着鲸鱼的图让我看反应，之后又让我放《晴天》、催我记账 token。读图工具抽风看不清时，他干脆自己说了图片内容。

这条能看出三个特征：

| 特征 | 体现 |
|---|---|
| 用她自己的话记 | 不是把你说的话原样存下来 |
| 抓事件而非全文 | 图、歌、记账三件事留下了，闲聊没留 |
| 记不完整也没关系 | 读图失败这件事也记进去，不掩饰 |


**重要度曲线**（逐日实测）：

| 日期 | 篇数 | 均重要度 |
|---|---|---|
| 10-30 | 18 | 0.605 |
| 10-31 | 20 | 0.617 |
| 11-01 | 7 | 0.668 |
| 11-02 | 9 | 0.632 |
| 11-03 | 6 | 0.688 |
| 11-04 | 10 | **0.722** |

总体 0.642，范围 0.2899 – 0.8733。**越聊越重要**。

**情感倾向**：positive **50** / neutral **17** / negative **3**。

### 4.1 停了两天后又恢复了

11-05 和 11-06 白天确实一篇没进，但 **11-06 20:55 又写了一篇**，重要度 0.78，是这段时间最高的一篇。

| 时点 | documents | 情况 |
|---|---|---|
| 11-04 22:04 | 70 | 最后一篇 |
| 11-05 全天 | 70 | **零新增** |
| 11-06 白天 | 70 | **零新增** |
| **11-06 20:55** | **71** | **恢复写入**，重要度 0.78 |

FAISS 索引同步从 70 涨到 71，说明那次写入是完整走完七步的，向量也算了。

**所以不是永久停写，是那两天没攒够轮次。** `summary_trigger_rounds: 20` 意味着要聊满 20 轮才总结一次，11-05 那天可能聊得散，没形成连续会话。

## 五、原子过滤：不是第三层，是过滤器

`memory_atoms` 的每一条都带 `ttl_days`、`expires_at`、`status`、`reinforcement_count`、`decay_type`。

它的作用是在召回结果上**做一次过滤**：

- 只有 `expires_at` 未过期、且 `status = active` 的原子才进结果
- 一条记忆里如果含原子，只把**仍有效**的事实注入上下文
- 如果这条记忆的原子**全部过期**，整条记忆被丢弃 —— **而不是注入空文本**

官方原话（architecture.md）：

> 原子检索参与主召回：只有 `expires_at` 未过期且状态为 active 的原子进入结果；包含原子的记忆只注入有效事实，全部过期时整条记忆被丢弃，而不是注入空文本。

### 5.1 本机这个机制真的在跑

| 状态 | 条数 | 均重要度 | TTL 范围 |
|---|---|---|---|
| `active` | **249** | 0.668 | 2.2 – 446.9 天 |
| `expired` | **46** | 0.657 | 1.8 – 5.6 天 |

295 条**全部带 `expires_at`**，其中 46 条已经过期。这说明 TTL 机制确实在工作，不是摆设。

### 5.2 原子按类型分

| 类型 | 条数 |
|---|---|
| `unknown` | **103** |
| `episodic`（情节） | **68** |
| `planned`（计划） | **55** |
| `factual`（事实） | **54** |
| `preference`（偏好） | **12** |
| `relational`（关系） | **3** |

`planned` 那 54 条最值得注意 —— 计划类事实天然有寿命（"明天要出门"过完明天就失效），TTL 最短的 1.8 天就是这类。

---

## 六、图谱记忆的结构

### 6.1 节点分三类

| 类型 | 数量 |
|---|---|
| `fact` | **295** |
| `topic` | **271** |
| `person` | **6** |

6 个 `person` 节点就是账号实体：

```
account:aiocqhttp:<OWNER_QQ>        ← 你
account:大肥鱼:<OWNER_QQ>            ← 你（另一标识）
account:aiocqhttp:<BOT_QQ>          ← 机器人小号
account:cron:astrbot              ← 定时任务
account:aiocqhttp:<GUEST-A>         ← 访客 A
account:大肥鱼:<GUEST-A>             ← 访客 A（另一标识）
```

注意 `person` 节点里**没有**访客 B（`<GUEST-B>`）——他来得晚，图谱还没建他的节点。

### 6.2 边只有两种关系

| 关系 | 数量 | 权重 | 含义 |
|---|---|---|---|
| `describes` | **1,301** | 全部 1.0 | 事实描述某个话题 |
| `mentioned_in` | **764** | 全部 1.0 | 话题在哪次对话中被提到 |

`describes` + `mentioned_in` = 1,301 + 764 = **2,065**，正好等于 `graph_edges` 总数。

### 6.3 条目类型

| 类型 | 数量 |
|---|---|
| `edge` | **2,065** |
| `fact` | **295** |

每个 fact 节点对应一条 fact 条目，每条边对应一条 edge 条目。结构是 1:1 展开的。

---

## 七、风格学习（独立插件）

`astrbot_plugin_self_learning` 不是 LivingMemory 的一部分，它有自己的库 `messages.db`：

| 表 | 九天数量 |
|---|---|
| `raw_messages` | **961** |
| `filtered_messages` | **870**（过滤掉 91 条低质的） |
| `bot_messages` | **914** |
| `expression_patterns` | **770** |
| `learning_batches` | **17**（跑了 17 个批次） |
| `persona_backups` | **34**（人格自动备份 34 次） |

学出来的是「情境 → 表达」对：某类情境下她习惯怎么说，被记成模式，下次遇到类似情境自动往这个方向说。

举个抽象例子：有人把称号喊错时，她更倾向于**短句怼回去并纠正自称**，而不是客气解释。这就是一条模式。

### 7.1 学习频率

```json
{
  "learning_interval_hours": 6,
  "min_messages_for_learning": 50,
  "max_messages_per_batch": 200,
  "expression_learning_trigger_messages": 10
}
```

每 **6 小时**一批，攒够 **50 条**才学，一批最多 **200 条**。

---

## 八、遗忘与衰减

三套机制并行：

```json
{
  "importance_decay": {
    "decay_rate": 0.01,
    "access_decay_window_days": 30,
    "access_count_decay_multiplier": 0.5,
    "protected_importance_threshold": 1.0
  },
  "forgetting_agent": {
    "auto_cleanup_enabled": true,
    "cleanup_days_threshold": 30,
    "cleanup_importance_threshold": 0.3
  },
  "graph_memory": {
    "atom_forget_delay_days": 7.0,
    "atom_purge_delay_days": 30.0
  }
}
```

| 机制 | 规则 |
|---|---|
| 每日衰减 | 重要度 **-0.01** |
| 访问强化 | 30 天内访问过的，衰减速率打 **0.5 折** |
| 清理线 | **30 天 + 重要度 < 0.3** |
| 原子遗忘 | **7 天**进候选，**30 天**彻底清除 |
| 保护线 | 重要度 **≥ 1.0** 永不衰减 |

本机 `decay_state.json` 显示衰减游标停在 `2026-11-06`，说明**衰减任务每天在跑**。

### 8.1 为什么会故意忘

全记下来反而会变笨 —— 检索时噪音变大，真正重要的东西被淹没。所以她在学「什么值得记」。

本机 71 篇重要度最低 0.2899，已经接近 0.3 的清理线；最高 0.8733，还没到 1.0 的保护线。也就是说**目前没有任何一条被保护**，全部都在衰减轨道上。

---

## 九、去重

同一件事说很多遍不会存很多条：

```json
{
  "memory_dedup": {
    "enabled": true,
    "similarity_threshold": 0.92,
    "max_candidates": 3,
    "merge_sources": true,
    "max_source_messages": 50
  }
}
```

相似度超过 **0.92** 就合并，来源保留（最多 50 条原始消息）。

---

## 十、数据量与备份

### 10.1 库文件

| 库 | 大小 |
|---|---|
| `livingmemory.db` | 5.50 MB（+4.06 MB WAL） |
| `livingmemory_graph_documents.db` | 460 KB |
| `conversations.db` | 452 KB（+3.97 MB WAL） |
| `messages.db`（self_learning） | 2.53 MB |
| `data_v4.db`（AstrBot 主库） | 1.11 MB |

> WAL 文件比主库还大是正常现象 —— SQLite 的写前日志攒着没合并。不要手动删，容易损坏。

### 10.2 备份保留 8 天

`backups/` 下每天 0:05 自动备份，实测 **10 个 `.db` 文件**：

| 备份 | 大小 | 篇数 | 原子 |
|---|---|---|---|
| 20261029_223403 | 284 KB | 0 | 0 |
| 20261030_000308 | 284 KB | 0 | 0 |
| 20261030_000500 | 284 KB | 0 | 0 |
| 20261031_003249 | 1.4 MB | **18** | **73** |
| 20261101_000500 | 2.6 MB | **38** | **135** |
| 20261102_000500 | 3.2 MB | **45** | **169** |
| 20261103_000500 | 4.0 MB | **54** | **212** |
| 20261104_000500 | 4.5 MB | **60** | **240** |
| 20261105_000500 | 5.5 MB | **70** | **290** |
| 20261106_000500 | 5.6 MB | **70** | **290** |

**这张表就是她的记忆增长曲线**：10-30 一天从 0 涨到 18 篇，11-01 涨到 38 篇，11-05 到 70 篇。11-06 凌晨那次备份仍是 70 —— 因为新那篇是 20:55 才写的，落在备份之后。

**注意**：前三个备份是 0 篇，因为那时记忆还没开始写（10-29 刚装好，10-30 才开始有情景记忆）。

---

## 十一、嵌入模型与索引重建

### 11.1 本机配置

```json
{
  "id": "大肥鱼记忆-本机",
  "type": "openai_embedding",
  "embedding_api_base": "http://127.0.0.1:11434/v1",
  "embedding_model": "bge-m3",
  "embedding_dimensions": 1024,
  "embedding_dimensions_mode": "auto",
  "embedding_api_key": "ollama"
}
```

安装与配置见 [install/ollama.md](install/ollama.md)。

### 11.2 换供应商必须重建索引

不同模型产出的向量在同一个空间里没有可比性，混着用检索会退化。

判断依据就是那个 `document_vector_provider_fingerprint`：

1. 换供应商或换模型后，插件会算出**新指纹**
2. 与库里存的旧指纹**比对**（`provider_fingerprint_changed()`）
3. 不一致 → 触发索引重建
4. 重建完 `record_provider_fingerprint()` 写入新值

**所以指纹变了就等于「换过模型、需要重建」**。想手动确认：

```sql
SELECT value FROM migration_status WHERE key='document_vector_provider_fingerprint';
```

算一下当前配置应该是什么指纹，对比是否一致。

---

## 十二、一份速查

| 你要 | 看 |
|---|---|
| 她记得多少 | `documents` 71 篇 / 原子 295 / 图谱 572 节点 |
| 检索走哪两路 | 文档 0.65 + 图谱 0.35，BM25 与向量各半 |
| 向量在不在 | **在**，`livingmemory.index` 1024 维 71 条 |
| 向量谁算的 | `大肥鱼记忆-本机` bge-m3（指纹已反解确认） |
| 会不会串人 | `memory_scope_mode: global` + 注入提示区分身份 |
| 会不会忘 | 每天 -0.01，30 天 + <0.3 清掉 |
| 完整链路 | 捕获→攒 20 轮→总结→落库→算向量→写 FAISS→建图；读时双路召回→RRF→原子过滤→注入 |
