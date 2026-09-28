from __future__ import annotations

import json
import re
from typing import Callable

from openai import OpenAI

from ai_tool.runtime_config import get_ai_config


DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-flash"


def _parse_json_array(content: str | None) -> list[str]:
    if not content:
        return []
    match = re.search(r"\[[\s\S]*\]", content)
    if match is None:
        return []
    try:
        value = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _generate_json_array(
    prompt: str,
    *,
    max_tokens: int,
    client_factory: Callable[..., object],
) -> list[str]:
    try:
        config = get_ai_config()
    except RuntimeError:
        # Unit tests inject a fake client and do not need a real credential.
        # The production OpenAI client still fails fast with an actionable
        # configuration error when no key is supplied.
        if client_factory is OpenAI:
            raise
        config = {
            "api_key": "test-key",
            "base_url": DEEPSEEK_BASE_URL,
            "model": DEEPSEEK_MODEL,
        }
    client = client_factory(**config, timeout=90)
    response = client.chat.completions.create(
        model=config["model"],
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        extra_body={"thinking": {"type": "disabled"}},
        stream=False,
    )
    return _parse_json_array(response.choices[0].message.content)


def generate_strategy_content(
    title: str,
    requirements: str,
    *,
    client_factory: Callable[..., object] = OpenAI,
) -> list[str]:
    """Generate the segmented Sanong script with the verified DeepSeek model."""
    prompt = f"""
根据短视频标题生成视频字幕文案数组。

标题：{title}
要求：{requirements}

规则：
1. 只返回标准 JSON 字符串数组，不要返回 Markdown 或解释。
2. 第一项是吸引注意的开场，最后两项是总结性的结束语。
3. 中间内容分成多段，每段不超过 30 个汉字。
4. 总字数约 300 字，总元素数量以 8 至 12 个为宜。
5. 内容必须准确、通俗、有实际帮助，不包含点赞、关注等引导。
6. 文案中不使用标点，使用空格分隔句子。
""".strip()
    return _generate_json_array(
        prompt,
        max_tokens=2048,
        client_factory=client_factory,
    )


def generate_topics(
    text: str,
    *,
    client_factory: Callable[..., object] = OpenAI,
) -> list[str]:
    """Generate short publishing topics for the completed video script."""
    prompt = f"""
请根据下面的三农短视频内容生成发布话题。

视频内容：{text}

规则：
1. 只返回标准 JSON 字符串数组，不要返回 Markdown 或解释。
2. 返回 2 至 4 个简短、准确、便于发布检索的话题。
3. 话题不带 # 号，不添加空泛或与内容无关的词。
4. 内容中明确出现市级或县级行政区时，可将其标准简称单独作为话题。
""".strip()
    return _generate_json_array(
        prompt,
        max_tokens=512,
        client_factory=client_factory,
    )[:4]


def generate_material_tags(
    title: str,
    text: str,
    *,
    client_factory: Callable[..., object] = OpenAI,
) -> list[str]:
    """Generate searchable visual-material tags for one script segment."""
    prompt = f"""
请为三农短视频的这一段文案提取画面素材搜索标签。

视频标题：{title}
当前文案：{text}

规则：
1. 只返回标准 JSON 字符串数组，不要返回 Markdown 或解释。
2. 返回 2 至 5 个能直接用于查找画面素材的名词或短语。
3. 优先选择文案中的人物 地点 农作物 土地 房屋 工具 场景或具体事务。
4. 不要求必须有地名；没有地名时应提取与标题和当前文案相关的通用画面要素。
5. 标签不带 # 号，不返回抽象评价、完整句子或重复内容。
""".strip()
    return _generate_json_array(
        prompt,
        max_tokens=512,
        client_factory=client_factory,
    )[:5]


__all__ = [
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_MODEL",
    "generate_material_tags",
    "generate_strategy_content",
    "generate_topics",
]
