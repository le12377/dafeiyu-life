"""修复 Breeze 语音的两个问题：WAV 头 + 句尾被吞。

问题一（时长乱）：Breeze 的 `POST /v1/audio/speech` 在 response_format=wav 时返回
流式 WAV，RIFF/data 长度字段都是 0xFFFFFFFF（未知长度）。AstrBot 原样落盘，
QQ 拿到的语音时长变成天文数字，进度条乱跳、放一半就停。

问题二（最后一个字没了）：Breeze 在默认 seed 下经常提前 EOS，音频停在半个字上
（末尾 100ms 还有很大的能量）。实测同一句话换 seed 就会正常收尾——所以这里
生成后检查"尾巴"，如果发现还在说话，就换个 seed 再生成，最多 3 次，取最干净的一条。

做法：替换 `ProviderOpenAITTSAPI.get_audio`（不改核心代码，AstrBot 升级不丢）。
"""

import asyncio
import os
import struct

import httpx

from astrbot import logger
from astrbot.api.star import Context, Star, register
from astrbot.core.utils.astrbot_path import get_astrbot_temp_path
from astrbot.core.utils.datetime_utils import generate_timestamp_id

_PATCH_FLAG = "_tts_wav_fix_patched"

# 第一次用服务端默认 seed，后面换几个不同的 seed 重试
_SEEDS = [None, 3, 7, 11, 1234]
_MAX_ATTEMPTS = 3

# 末尾 80ms 的峰值超过这个值，就认为还没说完（int16 满量程 32767）
# 2026-11-01: 1500 -> 4000。实测正常收尾的余音峰值常在 1500~3000，
# 阈值太严会导致整句无谓重合成（Breeze 一次约 27~30s，延迟翻倍）。
# 真正被截断的情况实测在 6000~11000，4000 仍能拦住。
_CLEAN_TAIL_PEAK = 4000


def repair_wav_header(path: str) -> bool:
    """把 0xFFFFFFFF 的 RIFF/data 长度改成真实值；返回是否改动过。"""
    try:
        with open(path, "rb") as f:
            data = bytearray(f.read())
    except OSError:
        return False

    if len(data) < 44 or data[0:4] != b"RIFF" or data[8:12] != b"WAVE":
        return False

    idx = data.find(b"data", 12, 4096)
    if idx < 0:
        return False

    data_off = idx + 8
    data_size = len(data) - data_off
    riff_size = struct.unpack("<I", data[4:8])[0]
    cur_data_size = struct.unpack("<I", data[data_off - 4 : data_off])[0]

    if riff_size == data_size + 8 and cur_data_size == data_size:
        return False
    if riff_size != 0xFFFFFFFF and cur_data_size != 0xFFFFFFFF:
        return False

    data[4:8] = struct.pack("<I", len(data) - 8)
    data[data_off - 4 : data_off] = struct.pack("<I", data_size)
    with open(path, "wb") as f:
        f.write(data)
    return True


def tail_peak(raw: bytes, ms: int = 80) -> int:
    """末尾 ms 毫秒的最大振幅（16bit PCM）。"""
    idx = raw.find(b"data", 12, 4096)
    if idx < 0:
        return 32767
    data = raw[idx + 8 :]
    total = len(data) // 2
    n = min(total, int(24000 * ms / 1000))
    if n <= 0:
        return 32767
    seg = data[(total - n) * 2 : total * 2]
    vals = struct.unpack("<%dh" % n, seg)
    return max(abs(v) for v in vals)


def install_patch() -> bool:
    from astrbot.core.provider.sources.openai_tts_api_source import (
        ProviderOpenAITTSAPI,
    )

    if getattr(ProviderOpenAITTSAPI, _PATCH_FLAG, False):
        return True

    async def get_audio(self, text: str) -> str:
        base = str(self.client.base_url).rstrip("/")
        url = base + "/audio/speech"
        temp_dir = get_astrbot_temp_path()

        best_path = None
        best_peak = None
        async with httpx.AsyncClient(timeout=httpx.Timeout(180.0)) as client:
            for seed in _SEEDS[:_MAX_ATTEMPTS]:
                body = {
                    "model": self.model_name,
                    "voice": self.voice,
                    "input": text,
                    "response_format": "wav",
                }
                if seed is not None:
                    body["seed"] = seed

                resp = None
                for _ in range(6):
                    resp = await client.post(url, json=body)
                    if resp.status_code == 409:  # Breeze 单请求忙
                        await asyncio.sleep(0.4)
                        continue
                    break
                if resp is None or resp.status_code != 200:
                    logger.warning(
                        f"[tts_wav_fix] TTS 请求失败: {getattr(resp, 'status_code', '?')}"
                    )
                    continue

                path = os.path.join(
                    temp_dir, f"openai_tts_api_{generate_timestamp_id()}.wav"
                )
                with open(path, "wb") as f:
                    f.write(resp.content)
                repair_wav_header(path)

                peak = tail_peak(resp.content)
                if best_peak is None or peak < best_peak:
                    best_path, best_peak = path, peak
                if peak <= _CLEAN_TAIL_PEAK:
                    break
                logger.info(
                    f"[tts_wav_fix] 句尾没说完（末尾峰值 {peak}），换 seed 重试"
                )

        if best_path is None:
            raise RuntimeError("TTS 全部重试均失败")
        logger.info(f"[tts_wav_fix] 语音就绪 末尾峰值={best_peak}: {best_path}")
        return best_path

    ProviderOpenAITTSAPI.get_audio = get_audio
    setattr(ProviderOpenAITTSAPI, _PATCH_FLAG, True)
    return True


@register(
    "astrbot_plugin_tts_wav_fix",
    "<SELF>",
    "修正流式 TTS 的 WAV 头，并在句尾被吞时换 seed 重新生成",
    "v0.2.0",
)
class TtsWavFix(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        try:
            install_patch()
            logger.info("[tts_wav_fix] v0.2 已挂上：WAV 头修正 + 句尾自动重试")
        except Exception as exc:
            logger.warning(f"[tts_wav_fix] 挂载失败: {exc}")
