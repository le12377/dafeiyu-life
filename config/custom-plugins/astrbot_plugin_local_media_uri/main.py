"""让超大音频/图片走本地路径而不是 base64，避免撑爆 NapCat 的 WS 上限。

背景：AstrBot 的 aiocqhttp 适配器把 Record 段统一转成 WAV 再 base64
（Record.convert_to_base64(target_format="wav")）。一首 4 分半的歌
会变成约 48MB WAV → 64MB base64 → 超过 NapCat 硬编码的 50MB maxPayload，
反向 WS 直接断线（RangeError: Max payload size exceeded）。

本插件只改一处：当 Record 指向本机文件且文件大于 3MB 时，
把段转成 file:// URI 交给 NapCat（同机可读），帧大小从 60MB+ 降到几 KB。
小文件（TTS 语音等）仍走原来的 base64 逻辑，行为不变。
"""

import os
from pathlib import Path

from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent  # noqa: F401
from astrbot.api.message_components import Image, Record
from astrbot.api.star import Star

BIG_FILE_BYTES = 3 * 1024 * 1024

logger.info("[local_media_uri] 模块已导入（module import ok）")


class LocalMediaUri(Star):
    def __init__(self, context, config=None):
        super().__init__(context)
        self._install()

    def _install(self) -> None:
        try:
            from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
                AiocqhttpMessageEvent,
            )
        except Exception as exc:  # pragma: no cover
            logger.error(f"[local_media_uri] 无法导入适配器: {exc}")
            return

        original = AiocqhttpMessageEvent.__dict__["_from_segment_to_dict"]
        if getattr(original, "_local_media_uri_patched", False):
            logger.info("[local_media_uri] 已经打过补丁，跳过")
            return

        async def _patched(segment, _orig=original.__func__):
            if isinstance(segment, Record):
                try:
                    source = await segment._resolve_file_source()
                    if (
                        source
                        and not source.startswith(("base64://", "data:", "http://", "https://"))
                    ):
                        path = Path(source)
                        if path.is_file() and path.stat().st_size > BIG_FILE_BYTES:
                            uri = path.as_uri()
                            logger.info(
                                "[local_media_uri] 大语音 %.1fMB 改走本地路径: %s",
                                path.stat().st_size / 1048576,
                                uri,
                            )
                            return {
                                "type": segment.type.lower(),
                                "data": {"file": uri},
                            }
                except Exception as exc:
                    logger.warning(f"[local_media_uri] 判定失败，回退 base64: {exc}")
            return await _orig(segment)

        _patched._local_media_uri_patched = True
        AiocqhttpMessageEvent._from_segment_to_dict = staticmethod(_patched)
        logger.info(
            f"[local_media_uri] 已挂上：Record 源码文件 >{BIG_FILE_BYTES // 1048576}MB 时用 file:// 发送"
        )

    async def terminate(self):
        logger.info("[local_media_uri] 插件已卸载（补丁随进程存活，需重启才回滚）")
