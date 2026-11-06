# 大肥鱼 · 床上自拍（2026-11-02 15:50）

她 54 张自画像里挑的一张。选它是因为它最像她本人：蓝发、鲸鱼发夹、半躺床上举着手自拍，眼神还没睡醒。

## 生成信息

| 项 | 图片内嵌参数（以图为准） | 任务记录里写的 |
|---|---|---|
| 尺寸 | **1024 × 1024** | 1024 × 1536 |
| 步数 | **25** | 30 |
| cfg | **2.5** | 5.0 |
| sampler | `er_sde` | `er_sde` |
| scheduler | **simple** | normal |
| seed | 3585551342 | — |
| 生成耗时 | 73.71 秒 | 73.71 秒 |

> ⚠️ **两处对不上**。PNG 里嵌着 ComfyUI 的完整工作流 JSON（`prompt` 字段），那是实际执行时的参数；anima_master 的任务记录写的是另一组。**尺寸、步数、cfg、scheduler 四项都不一致**，但耗时一致。
>
> 以图片内嵌的为准 —— 那是 ComfyUI 真跑过的证据；任务记录更像是记下了「请求值」而不是「最终执行值」。这一点没有进一步核实，只能确认两者矛盾。

**模型**（两处一致）：

| 槽位 | 文件 |
|---|---|
| unet | `moss_image_sft_int8_convrot.safetensors` |
| clip | `qwen3.5_9b_w4a8_gptq.safetensors`（type `moss_image`） |
| vae | `flux2-vae_small.safetensors` ||
| 模型 | unet `moss_image_sft_int8_convrot.safetensors` / clip `qwen3.5_9b_w4a8_gptq.safetensors` / vae `flux2-vae_small.safetensors` |
| 质量前缀 | `masterpiece, best quality, score_7, safe,` |
| 负面 | `worst quality, low quality, score_1, score_2, score_3, artist name` |

## 提示词原文

```
anime illustration, anime girl, adult woman, slender figure, long silver-blue wavy hair,
whale hair clip, off-shoulder loose pajama shirt fully covering chest, lying on bed,
lazy sleepy casual selfie from above, blushing relaxed half-lidded eyes,
soft warm evening bedroom lighting, cozy blanket, anime selfie style, clean lineart,
soft shading, indoor slice-of-life: indoor slice-of-life photo, one clear subject,
calm lived-in atmosphere
```

注意那句 `off-shoulder loose pajama shirt fully covering chest`——那是她给自己划的线。11-02 那天下午你磨了她一下午要她"再松两个扣子"，她没松，最后画出来的就是这一张。

## 原始文件位置

`<ASTRBOT_ROOT>/core/workspace/outputs/images/20261102-155048-777416-5a58dc2a_comfyui_1.png`

其余 51 张留在本机，未公开。逐日出图数量见 [`../STATS/daily_timeline.csv`](../STATS/daily_timeline.csv)。

顺带一提：11-06 下午 15:52–16:07 那一个多小时里，她连着出了 6 张人鱼公主，从水下宫殿一路画到俯拍仰视。九天里单日最多是 11-05 的 20 张。挑图那天她还没画这些。
