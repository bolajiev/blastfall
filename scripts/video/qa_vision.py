#!/usr/bin/env python3
"""QA the assembled demo video frames with a vision model."""
import base64
import json
import os
import sys
import urllib.request

API = "https://opencode.ai/zen/go/v1/chat/completions"
MODEL = os.environ.get("VISION_MODEL", "qwen3.5-plus")
KEY = os.environ["OPENAI_API_KEY"]
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/151.0.0.0 Safari/537.36")
FRAMES = sys.argv[1:] if len(sys.argv) > 1 else sorted(
    f"qa-frames/{f}" for f in os.listdir("qa-frames"))

PROMPT = """You are a video-editing QA reviewer. I'm showing you still frames from
a 3-minute hackathon demo video for a supply-chain security tool. For EACH frame,
report concisely:
1. what it shows (one line)
2. TEXT LEGIBILITY: is any on-screen text crisp and readable, or blurry/blocky?
3. LAYOUT: overlapping elements? text cut off at edges? awkward framing?
4. CURSOR: is a red circular cursor visible and reasonably placed?
5. any obvious problem that would look bad in a submitted demo video.

End with an OVERALL VERDICT and a numbered list of the most important fixes
(limit to the top 6). Be blunt and specific. If a frame is fine, say so in one
line - don't pad."""


def b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def main():
    content = [{"type": "text", "text": PROMPT}]
    for path in FRAMES:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64(path)}"},
        })
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 4096,
    }
    req = urllib.request.Request(
        API, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
                 "User-Agent": UA},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read().decode())
    text = data["choices"][0]["message"]["content"]
    print(text)


if __name__ == "__main__":
    main()
