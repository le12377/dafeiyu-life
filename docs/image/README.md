# 本地生图

她的图全是本机 ComfyUI 画的，没走云端 API。好处是不用按张付费、可以画到很久；代价是出图慢（单张 70–80 秒）。

## 调用链路

```
AstrBot（大肥鱼）
   │  调用工具
   ▼
anima_master 0.9.3  ──提示词优化──▶ 大模型写成 Danbooru 风格英文 tag
   │  HTTP
   ▼
ComfyUI（127.0.0.1:8188）
   │  执行 anima_t2i 工作流
   ▼
MOSS-Image-SFT 模型出图 → outputs/images/*.png
```

## 模型清单

三个文件都在 `<COMFY_ROOT>\ComfyUI-Shared\models\`：

| 文件 | 类型 | 大小 | 作用 |
|---|---|---|---|
| `moss_image_sft_int8_convrot.safetensors` | diffusion_models | 5.04 GB | 主模型（MOSS-Image SFT，int8 量化） |
| `qwen3.5_9b_w4a8_gptq.safetensors` | text_encoders | 6.84 GB | 文本编码器（Qwen3.5-9B，4bit 量化） |
| `flux2-vae_small.safetensors` | vae | 0.23 GB | VAE 解码器 |

这套组合是 **MOSS-Image** 架构（ComfyUI 内置支持，不是第三方自定义节点），配合 Qwen3.5 做文本编码、FLUX2 的小 VAE 解码。

## ComfyUI 侧配置

ComfyUI 用的是 Desktop 版，装在 `<COMFY_ROOT>\ComfyUI-Installs\ComfyUI (1)\ComfyUI`，监听 8188。模型目录通过 `extra_model_paths` 指向 `ComfyUI-Shared`，这样多套安装共用一份权重。

## anima_master 插件配置

完整配置见 [`../../config/plugins/astrbot_plugin_anima_master.json`](../../config/plugins/astrbot_plugin_anima_master.json)。关键项：

### 连接

```json
{
  "comfyui_base_url": "http://127.0.0.1:8188",
  "workflow": "anima_t2i",
  "custom_workflow_enabled": true,
  "custom_workflow_path": "variants/moss/workflows/moss_t2i_api.json",
  "timeout": 300,
  "poll_interval": 2
}
```

`timeout` 给到 300 秒，因为单张实际要 70–80 秒，加上排队和模型加载，给少了会误判超时。

### 模型

```json
{
  "unet_name": "moss_image_sft_int8_convrot.safetensors",
  "clip_name": "qwen3.5_9b_w4a8_gptq.safetensors",
  "vae_name": "flux2-vae_small.safetensors"
}
```

### 出图参数

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

默认竖图 1024×1536（自拍、人像用这个比例）。可选的尺寸白名单：

```
832x1216  896x1152  1024x1024  1152x896  1216x832
768x1344  1344x768  1024x1536
```

`cfg 5.0` 偏低是刻意的。这个模型在低 cfg 下画面更松弛、更像随手拍；cfg 拉到 8 以上会变得僵硬、颜色过饱和。

### 质量词与负面词

```json
{
  "quality_prefix": "masterpiece, best quality, score_7, safe,",
  "negative_prompt": "worst quality, low quality, score_1, score_2, score_3, artist name"
}
```

负面词里特意排除了 `artist name`——这样模型不会模仿某个画师的风格，画出来是她自己的样子。

### 提示词怎么来的

她不会直接把你的中文话丢给 ComfyUI。中间有个提示词优化环节：

```json
{
  "prompt_optimize_enabled": true,
  "prompt_builder_web_search_enabled": true,
  "prompt_builder_search_max_results": 5,
  "prompt_builder_deep_thinking_enabled": true,
  "prompt_builder_reasoning_effort": "high",
  "prompt_builder_max_content_tags": 65
}
```

流程是：你的话 → 大模型联网查角色外观资料（如果画的是某个具体角色）→ 写成一行英文 Danbooru tag → ComfyUI 出图。

实际用的提示词模板（节选）：

> 你是为 Anima 图像生成模型编写正面提示词的 AI 画师。
> 请根据用户的原始要求设计一幅完整、协调、具有视觉吸引力的画面，并将结果输出为英文 Danbooru-style tags。
> 只输出一行英文 tags，使用英文逗号分隔。
> 不要输出解释、分析、标题、编号、Markdown、代码块或中文。
> 不要输出 masterpiece、best quality、score 等质量前缀。

完整模板在配置文件的 `prompt_builder_template` 字段。

### 一张真实出图的完整参数

2026-11-02 15:50 那张（[`../../media/大肥鱼-床上自拍-2026-11-02.png`](../../media/大肥鱼-床上自拍-2026-11-02.png)）：

| 项 | 值 |
|---|---|
| 尺寸 | 1024 × 1536 |
| steps / cfg | 30 / 5.0 |
| sampler / scheduler | `er_sde` / `normal` |
| 耗时 | 73.71 秒 |
| 提示词 | `anime illustration, anime girl, adult woman, slender figure, long silver-blue wavy hair, whale hair clip, off-shoulder loose pajama shirt fully covering chest, lying on bed, lazy sleepy casual selfie from above, blushing relaxed half-lidded eyes, soft warm evening bedroom lighting, cozy blanket, anime selfie style, clean lineart, soft shading, indoor slice-of-life: indoor slice-of-life photo, one clear subject, calm lived-in atmosphere` |

提示词原文和生成元数据在 [`../../media/README.md`](../../media/README.md)。

## 生图入口有三个

她手上其实有三条画图路径，人格设定里明确规定了什么时候用哪个：

| 工具 | 走哪 | 什么时候用 |
|---|---|---|
| `comfyui_generate` | 本机 ComfyUI | 默认，慢但无水印 |
| `pc_generate_photo` | private_companion / image_companion | 自拍、改图、把自己画进去 |
| `generate_image_with_theme` | 云端 API | 只在 ComfyUI 连不上、或你说"快点随便画一张"时 |

优先级是刻意的：**能用本机就不用云端**，因为云端有水印、要花钱、而且图会离开这台机器。

## 输出与清理

出图落在：

```
<ASTRBOT_ROOT>/core/workspace/outputs/images/
```

文件名格式：`YYYYMMDD-HHMMSS-微秒-随机_comfyui_1.png`。

清理策略：

```json
{
  "storage_retention_days": 30,
  "manifest_max_records": 5000
}
```

保留 30 天，任务清单最多留 5000 条。九天里她一共画了 **52** 张。

## 常见坑

1. **ComfyUI 没启动** —— AstrBot 报连接失败。检查 `Get-NetTCPConnection -LocalPort 8188`，没起来就手动开 ComfyUI。
2. **模型名对不上** —— 配置里写的文件名必须和 `models/` 下的完全一致，差一个字符就加载失败。
3. **显存不够** —— 这套模型峰值占用不小。同机跑 ComfyUI 时别同时开别的吃显存的东西。
4. **单张超时** —— 把 `timeout` 从 300 再往上加，或者把 steps 降到 25。
5. **工作流出图正常但发不出 QQ** —— 那是语音/图片发送的问题，看 [`../tts/README.md`](../tts/README.md) 里 base64 那节。
