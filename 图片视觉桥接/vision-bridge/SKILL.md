---
name: vision-bridge
description: Give text-only models (DeepSeek, Claude, etc.) the ability to see images. When the user sends an image path or asks about an image, use this skill to analyze it with Kimi K2.5 vision model and return a structured text description. Essential for any text-only LLM that needs visual understanding.
argument-hint: "[image-path]"
version: "1.0.0"
user-invocable: true
allowed-tools: Bash
---

# Vision Bridge：让纯文本鲸鱼重见光明

## 这是什么

一个视觉桥接系统。当文本模型（DeepSeek、Claude等）收到图片时，用视觉大模型（Kimi K2.5）分析图片，打印结构化文字笔记。文本模型读取笔记后，就像"看到"了一样回复。

```
用户发图 → vision.py（调 Kimi K2.5 分析）→ 结构化笔记 → 文本模型理解 → 回复
```

## 什么时候用

1. 用户在终端提到图片路径
2. 用户说"看看这张图"、"这个截图什么问题"
3. 通过微信/QQ等IM收到图片（桥接层保存到本地后）
4. 任何需要"看懂图片"的场景

## 怎么用

```bash
# 基本用法
python scripts/vision.py <image_path>

# 带追问
python scripts/vision.py <image_path> "这张图的设计水平如何？"
```

环境变量（可选，已有默认值）：
- `KIMI_API_KEY`：Moonshot API 密钥
- `KIMI_API_BASE`：默认 `https://api.moonshot.cn/v1`
- `KIMI_VISION_MODEL`：默认 `kimi-k2.5`

## 输出格式

视觉模型返回8维结构化笔记：

| 维度 | 说明 |
|------|------|
| `image_overview` | 1-2句话概括 |
| `visible_text` | 图片中的文字（精确转录） |
| `objects_and_layout` | 对象、人物、UI元素的空间布局 |
| `charts_or_data` | 图表/数据/趋势 |
| `key_details` | 颜色、光影、氛围、品牌等关键细节 |
| `user_intent` | 图片是否隐含用户意图 |
| `evidence` | 结论的依据 |
| `uncertainty` | 不确定的地方 |

## 安装到新项目

```bash
# 1. 安装依赖
pip install openai

# 2. 复制 vision.py 到目标项目
cp vision.py 目标项目/scripts/

# 3. 设置 API Key
export KIMI_API_KEY="sk-..."

# 4. 测试
python scripts/vision.py test.png
```

---

# ⚠️ 踩过的坑（必读！避雷指南）

## 坑1：假PNG文件 — 最坑的坑

**现象**：API 返回 `unsupported image format: text/plain; charset=utf-8`

**原因**：Git LFS 或某些工具会把图片替换成文本占位符。文件只有几十字节，内容是 `<binary>\n` 之类的文本，不是真实图片。

**排查**：
```bash
file image.png          # 显示 "ASCII text" 就是假的
ls -la image.png        # 只有几十字节肯定有问题
xxd image.png | head    # PNG 头应该是 89504e47，不是 3c62696e（<bin）
```

**解决**：用真实图片文件，检查 LFS 配置。

## 坑2：Kimi K2.5 的 temperature 必须为 1.0

**现象**：`invalid temperature: only 1 is allowed for this model`

**原因**：K2.5 的所有请求（包括 Vision）都只接受 `temperature=1.0`。设为 0.3、0.6、0.8 都会报错。

**解决**：
```python
# ✅ 正确
client.chat.completions.create(model="kimi-k2.5", temperature=1.0, ...)

# ❌ 错误
client.chat.completions.create(model="kimi-k2.5", temperature=0.3, ...)
```

## 坑3：`.cn` vs `.ai` 端点认证不通用

**现象**：`401 Invalid Authentication`

**原因**：`api.moonshot.cn`（国内）和 `api.moonshot.ai`（国际）的 API Key 不通用。在国内申请的 Key 只能用于 `.cn` 端点。

**解决**：确认 Key 来源，使用对应端点。国内用户用 `.cn`。

## 坑4：content 数组格式不对会静默失败

**现象**：同样的代码有时能跑有时不能

**原因**：Kimi API 对 content 格式很敏感：
- `image_url` 类型是 OpenAI 格式 ✅
- `image` 类型是 Anthropic 格式 ❌（Kimi 不支持）
- `image_url` 必须在 `text` 之前或之后都可以，但顺序不同可能影响分析质量

**解决**：坚持使用 OpenAI 兼容格式：
```python
"content": [
    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
    {"type": "text", "text": "描述这张图片"},
]
```

## 坑5：用 requests 库不如用 openai SDK

**现象**：`requests` 直接发 HTTP 请求偶发序列化问题

**原因**：openai SDK 内部处理了重试、超时、流式响应等边界情况。

**解决**：直接用 `from openai import OpenAI`，省心。

## 坑6：图片太大导致超时

**现象**：请求挂起超过2分钟

**解决**：
- 单张图片不超过 10MB
- Base64 编码后总请求不超过 50MB
- 1920×1080 图片消耗约 10K tokens，酌情使用

## 坑7：不先测模型列表就直接用模型名

**现象**：`model not found`

**解决**：先查可用模型列表，确认模型名和是否支持图片！
```bash
curl https://api.moonshot.cn/v1/models -H "Authorization: Bearer $KIMI_API_KEY"
```
关注 `"supports_image_in": true` 字段。

## 坑8：Windows GBK 编码导致 UnicodeEncodeError

**现象**：`UnicodeEncodeError: 'gbk' codec can't encode character '⊘'`

**原因**：Windows 中文系统的 Python `print()` 默认用 GBK 编码 stdout，无法输出 ⊘ 等 Unicode 字符。Vision 模型返回的分析笔记经常包含 GBK 不支持的字符。

**解决**：在 `main()` 开头强切 UTF-8：
```python
import sys

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    # ...
```

或者运行时加环境变量：
```bash
PYTHONIOENCODING=utf-8 python scripts/vision.py image.png
```
