# 安装本地生图

本机的图全是 ComfyUI 画的，没走云端。这一节讲怎么从零把 ComfyUI 和 AstrBot 接起来。

## 0. 官方地址

| 用途 | 地址 |
|---|---|
| **桌面版下载页** | https://github.com/Comfy-Org/Comfy-Desktop/releases |
| 官网下载入口 | https://comfy.org/download |
| 白皮书/主仓库 | https://github.com/comfyanonymous/ComfyUI |
| ComfyUI-Manager | 装好后在界面右侧面板 |

桌面版仓库是 **Comfy-Org/Comfy-Desktop**（旧仓库 `Comfy-Org/desktop` 已归档，别下错）。

> 官网 `comfy.org/download` 上那个一键链接会**自动识别平台**，Windows 直接下 NSIS 安装包，比在 Releases 里挑资产省事。

## 1. 装 ComfyUI

Windows 上最省事的是 **ComfyUI Desktop**（桌面版），双击安装包，选好安装目录。

**本机的目录结构**（Desktop 版有两层，别搞混）：

```
<COMFY_ROOT>\                            ← 我手动指定的根目录
├── ComfyUI-Installs\ComfyUI (1)\            ← Desktop 创建的"安装"
│   ├── ComfyUI\                             ← 真正的 ComfyUI 源码与节点
│   ├── standalone-env\                      ← Desktop 自己配的 Python 环境
│   └── ...
└── ComfyUI-Shared\                          ← 我额外建的共享目录
    ├── models\                              ← 模型放这
    ├── input\
    └── output\
```

Desktop 版默认会把用户数据放 `%APPDATA%\ComfyUI`，把程序放 `%LOCALAPPDATA%\Programs\ComfyUI`。本机是安装时手动改到了 E 盘。

装完打开，浏览器会自动开 `http://127.0.0.1:8188`。

**验证**：能看到 ComfyUI 的节点画布，就说明服务起来了。

## 2. 放模型

三个文件，缺一不可：

| 文件 | 放哪 | 大小 | 作用 |
|---|---|---|---|
| `moss_image_sft_int8_convrot.safetensors` | `models/diffusion_models/` | 5.04 GB | 主模型 |
| `qwen3.5_9b_w4a8_gptq.safetensors` | `models/text_encoders/` | 6.84 GB | 文本编码器 |
| `flux2-vae_small.safetensors` | `models/vae/` | 0.23 GB | VAE 解码器 |

**这三个放错目录是最常见的失败原因**。ComfyUI 按下拉框里的分类读模型，位置错了列表里根本不显示。

### 用共享模型目录

本机的做法是把模型放在一个公共目录，让多套 ComfyUI 共用：

```
<COMFY_ROOT>\ComfyUI-Shared\models\
├── diffusion_models\moss_image_sft_int8_convrot.safetensors
├── text_encoders\qwen3.5_9b_w4a8_gptq.safetensors
└── vae\flux2-vae_small.safetensors
```

然后在 ComfyUI 目录下配 `extra_model_paths.yaml`：

```yaml
comfyui_shared:
    base_path: E:/Comfy-Desktop/ComfyUI-Shared/
    diffusion_models: models/diffusion_models
    text_encoders: models/text_encoders
    vae: models/vae
```

这样换安装、升级 ComfyUI 都不用重下 12 GB 权重。

## 3. 装 anima_master 插件

ComfyUI 起来之后回 AstrBot 后台，「插件市场」搜 `anima_master`，或者直接上传 zip 装。

本机版本 **0.9.3**，作者 YayiMiko。

装完在「插件配置」里填这几项：

| 配置项 | 值 |
|---|---|
| `comfyui_base_url` | `http://127.0.0.1:8188` |
| `workflow` | `anima_t2i` |
| `custom_workflow_enabled` | `true` |
| `custom_workflow_path` | `variants/moss/workflows/moss_t2i_api.json` |
| `timeout` | `300` |
| `poll_interval` | `2` |

`timeout` 给 300 秒，因为单张实际要 70–80 秒，加上排队和首次加载，给少了会误判失败。

## 4. 填模型名

文件名要和 `models/` 下的**完全一致**，差一个字符都加载失败：

```json
{
  "unet_name": "moss_image_sft_int8_convrot.safetensors",
  "clip_name": "qwen3.5_9b_w4a8_gptq.safetensors",
  "vae_name": "flux2-vae_small.safetensors"
}
```

## 5. 设出图参数

```json
{
  "width": 1024,
  "height": 1536,
  "steps": 30,
  "cfg": 5.0,
  "sampler_name": "er_sde",
  "scheduler": "normal"
}
```

**这个组合是调出来的，不是默认值**：

- `1024×1536` 竖图，人像自拍的比例
- `steps 30` 是速度和细节的平衡点，降到 20 会糊，拉到 50 只多花时间
- `cfg 5.0` **刻意偏低**。这个模型在低 cfg 下画面松弛、像随手拍；cfg 拉到 8 以上会僵硬、颜色过饱和
- `er_sde` 采样器配 `normal` 调度器，配合 MOSS-Image 出图最稳

可选尺寸白名单：

```
832x1216   896x1152   1024x1024   1152x896
1216x832   768x1344   1344x768    1024x1536
```

## 6. 设质量词

```json
{
  "quality_prefix": "masterpiece, best quality, score_7, safe,",
  "negative_prompt": "worst quality, low quality, score_1, score_2, score_3, artist name"
}
```

负面词里的 `artist name` 是刻意加的——阻止模型模仿某个画师风格，让她画出来是自己的样子而不是某某的画风。

## 7. 开提示词优化

这是最关键的一步。她不会把你的中文原话直接丢给 ComfyUI，中间要过一道大模型：

```json
{
  "prompt_optimize_enabled": true,
  "prompt_builder_provider_id": "",
  "prompt_builder_max_tokens": 1000,
  "prompt_builder_max_content_tags": 65,
  "prompt_builder_web_search_enabled": true,
  "prompt_builder_search_max_results": 5,
  "prompt_builder_deep_thinking_enabled": true,
  "prompt_builder_reasoning_effort": "high"
}
```

链路是：

```
你说「画个穿睡衣的二次元女孩」
      │
      ▼
大模型（联网查角色外观资料）→ 写成一行英文 Danbooru tag
      │
      ▼
ComfyUI 执行 anima_t2i 工作流
      │
      ▼
outputs/images/*.png
```

`prompt_builder_web_search_enabled` 开着是为了画具体角色时能查到官方图、服装、配色。画原创角色时这个搜索不会触发。

**提示词模板**（`prompt_builder_template`，完整版在配置文件里）：

```
你是为 Anima 图像生成模型编写正面提示词的 AI 画师。

请根据用户的原始要求设计一幅完整、协调、具有视觉吸引力的画面，
并将结果输出为英文 Danbooru-style tags。

输出要求：
- 只输出一行英文 tags，使用英文逗号分隔。
- 不要输出解释、分析、标题、编号、Markdown、代码块或中文。
- 不要输出 masterpiece、best quality、score 等质量前缀。
- 不要输出画师 tags；质量词和画师预设会由程序另行拼接。
- 尽量使用模型容易理解的可见画面描述。
- 保持用户明确指定的角色、主体、人数、关键服装、动作、表情和道具。
- 用户未明确要求地点、环境或背景时，按单张角色立绘设计，不要自行创造场景。
```

这几条约束很关键：不让她自己加质量词（程序会加，加了会重复加权）、不让她加画师名（会污染风格）。

## 8. 出图存哪

```
<ASTRBOT_ROOT>/core/workspace/outputs/images/
```

文件名格式：

```
20261102-155048-777416-5a58dc2a_comfyui_1.png
└─日期──┘└时间──┘└微秒─┘└随机─┘
```

保留策略：

```json
{
  "storage_retention_days": 30,
  "manifest_max_records": 5000
}
```

## 9. 三条画图路径

她手上其实有三个画图工具，人格设定里规定了优先级：

| 工具 | 走哪 | 什么时候用 |
|---|---|---|
| `comfyui_generate` | 本机 ComfyUI | **默认**，慢但无水印 |
| `pc_generate_photo` | image_companion | 自拍、改图、把自己画进去 |
| `generate_image_with_theme` | 云端 API | 只在 ComfyUI 连不上、或你说「快点随便画一张」 |

这条规矩在人格设定里的原话：

> 主人没说要快，就用 comfyui_generate（本机 ComfyUI，慢一点但没水印）。自拍、改图、把自己画进去，用 pc_generate_photo。只有本机 ComfyUI 连不上、或者主人明说"快点随便画一张"，才用 generate_image_with_theme（云端，快，但右下角有水印）。

为什么这么定：云端要花钱、有水印、而且图会离开这台机器。

## 10. 验证

在 QQ 里跟她说「画一只猫」，应该看到：

1. 她回一句「画好了」之类的话（不是描述打算怎么画）
2. 几秒到一两分钟后，图发过来

如果只回话不出图，去 ComfyUI 界面看队列里有没有任务、报没报错。

## 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| 报连接失败 | ComfyUI 没启动 | `Get-NetTCPConnection -LocalPort 8188` |
| 模型列表里找不到 | 文件放错目录 | 按第 2 节的表对照 |
| 加载失败 | 文件名差一个字符 | 严格照抄 |
| 出图超时 | 首次加载慢 | `timeout` 加到 300+ |
| 出图糊 | steps 太低 | 提到 30 |
| 颜色过饱和、画面僵硬 | cfg 太高 | 降到 5.0 |
| 图出来了但发不到 QQ | 发送层问题 | 看 [tts.md](tts.md) 里 base64 那节 |
| 显存不足 | 同时开了别的大模型 | 关掉 Ollama 或别的占显存进程 |
