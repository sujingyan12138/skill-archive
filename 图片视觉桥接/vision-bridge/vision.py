#!/usr/bin/env python3
"""Vision bridge — Kimi K2.5 视觉模型 → 文字描述。

参考 openhanako 的 Vision Bridge 架构：
用视觉模型处理图片，生成结构化文字笔记，文本模型（我）接收笔记。
"""

import base64
import os
import sys
from pathlib import Path

from openai import OpenAI


API_KEY = os.environ.get("KIMI_API_KEY", "sk-sWDDZaXgplp6a0f1erihrElg9uvw45wefNeLsfitb152Xuuq")
API_BASE = os.environ.get("KIMI_API_BASE", "https://api.moonshot.cn/v1")
MODEL = os.environ.get("KIMI_VISION_MODEL", "kimi-k2.5")

client = OpenAI(api_key=API_KEY, base_url=API_BASE)

# openhanako 式的结构化分析 prompt
VISION_PROMPT = """You are an image analyst for a text-only AI assistant. Carefully examine this image and produce a structured note covering these sections:

## image_overview
A concise 1-2 sentence summary of what this image shows.

## visible_text
Any text visible in the image, transcribed exactly as it appears. If none, say "无文字".

## objects_and_layout
Key objects, people, UI elements, or visual components and how they are arranged spatially.

## charts_or_data
If the image contains charts, graphs, tables, or data visualizations, describe the data and trends. If none, say "无数据图表".

## key_details
Notable visual details: colors, lighting, expressions, branding, numbers, code — anything that might matter for understanding the image.

## user_intent
If a user request or question seems to be implied by the image, describe it. If none, say "无明显意图指示".

## evidence
Why you drew each conclusion — what specifically in the image supports your observations.

## uncertainty
Anything you are unsure about, could not read clearly, or multiple possible interpretations."""


def image_to_base64(image_path: str) -> tuple[str, str]:
    """Encode image file to base64 URL. Returns (data_url, mime_type)."""
    ext = Path(image_path).suffix.lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
    }
    mime = mime_map.get(ext, "image/png")
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{data}", mime


def analyze_image(image_path: str, user_request: str = "") -> str:
    """Send image to Kimi K2.5 for analysis, return structured text note."""
    data_url, mime = image_to_base64(image_path)

    prompt = VISION_PROMPT
    if user_request:
        prompt += f"\n\n用户关于这张图的附加说明：{user_request}"

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url},
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            max_tokens=4096,
            temperature=1.0,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"[vision bridge error] {e}"


def main():
    # Windows 默认用 GBK 编码 stdout，Unicode 字符（如 ⊘）会炸。
    # 强制换成 UTF-8，解决 UnicodeEncodeError。
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    if len(sys.argv) < 2:
        print("用法: python vision.py <image_path> [user_request]")
        print("环境变量: KIMI_API_KEY, KIMI_API_BASE, KIMI_VISION_MODEL")
        sys.exit(1)

    image_path = sys.argv[1]
    user_request = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""

    if not os.path.exists(image_path):
        print(f"错误: 文件不存在 — {image_path}")
        sys.exit(1)

    print(analyze_image(image_path, user_request))


if __name__ == "__main__":
    main()
