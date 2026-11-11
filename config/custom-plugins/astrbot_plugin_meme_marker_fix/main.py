"""把模型漏成半截的表情包标记补全成对。

现象：meme_manager 的标记协议是 `&&happy&&`，模型偶尔只写出 `&&happy`
（收尾少一个 `&&`），插件解析不到就当成普通文字发出去，QQ 里就露字。
而且一旦某条assistant回复里漏了半截标记，这条会进聊天记录/记忆，
模型下一轮照着学，越漏越多。

这个插件在三个位置补齐：
1. on_llm_request：发给模型的历史里，把之前漏的半截标记补成对，断掉模仿；
2. on_llm_response：模型这一轮的回复先补；
3. on_decorating_result：真正发出去之前最后补一遍（排在表情包插件之前）。
"""
import re

from astrbot import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Plain
from astrbot.api.star import Context, Star

# 行尾一个或两个 & 紧跟分类键（字母开头，可带 : 的数字 id），后面只有空白或行尾。
# 已经成对的 &&happy&& 不会被匹配（键后面不是行尾）。
_HALF = re.compile(
    r"(?<![&\w])&{1,2}([A-Za-z_][A-Za-z0-9_:]{0,40})(?=[ \t]*(?:\r?\n|$))"
)


def _close_line(line: str) -> str:
    """只补不在反引号代码里的半截标记。"""
    if "`" in line:
        return line
    return _HALF.sub(r"&&\1&&", line)


def close_markers(text: str) -> str:
    if not text or "&&" not in text and not re.search(r"(?<![&\w])&[A-Za-z_]", text):
        return text
    parts = text.splitlines(keepends=True)
    return "".join(_close_line(p) for p in parts)


def _fix_content(content):
    """content 可能是 str、OpenAI 格式 dict 列表或 TextPart 列表。"""
    changed = False
    if isinstance(content, str):
        new = close_markers(content)
        return new, new != content
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                new = close_markers(part["text"])
                if new != part["text"]:
                    part["text"] = new
                    changed = True
            elif isinstance(getattr(part, "text", None), str):
                new = close_markers(part.text)
                if new != part.text:
                    part.text = new
                    changed = True
    return content, changed


class MemeMarkerFix(Star):
    def __init__(self, context: Context) -> None:
        super().__init__(context)

    @filter.on_llm_request(priority=100000)
    async def fix_history(self, event: AstrMessageEvent, req):
        n = 0
        for msg in getattr(req, "contexts", None) or []:
            if isinstance(msg, dict) and msg.get("role") == "assistant":
                _, changed = _fix_content(msg.get("content"))
                n += changed
        if n:
            logger.info(f"[meme_marker_fix] 历史里有 {n} 条回复的标记不成对，已补齐")

    @filter.on_llm_response(priority=99998)
    async def fix_response(self, event: AstrMessageEvent, resp):
        # 流式分片里标记可能还没写完，补了会破坏正确的标记，只在完整回复上补。
        if getattr(resp, "is_chunk", False):
            return
        text = getattr(resp, "completion_text", None)
        if isinstance(text, str):
            new = close_markers(text)
            if new != text:
                try:
                    resp.completion_text = new
                except Exception:
                    pass

    @filter.on_decorating_result(priority=99998)
    async def fix_result(self, event: AstrMessageEvent):
        try:
            result = event.get_result()
        except Exception:
            return
        chain = getattr(result, "chain", None) or []
        for comp in chain:
            if isinstance(comp, Plain) and comp.text:
                new = close_markers(comp.text)
                if new != comp.text:
                    comp.text = new
