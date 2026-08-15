#!/usr/bin/env python3
"""Professional frame-by-frame audit of the demo video using a vision model.

Frames are named fNNN.png sampled every STEP seconds from the video.
Sends them in batches so the whole video is reviewed.
"""
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
FRAMES_DIR = sys.argv[1] if len(sys.argv) > 1 else "audit-frames"
STEP = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
BATCH = int(sys.argv[3]) if len(sys.argv) > 3 else 18

PROMPT = """You are a senior video editor who reviews product-demo cutdowns for
VC demo reels. I am sending you stills sampled every {step} seconds from a
2.5-minute hackathon demo video of a software supply-chain security tool.
Audit it frame-by-frame like a professional.

For EACH frame, output exactly one line:
T={{t:.1f}}s | SHOT=<what's on screen, 4-8 words> | VERDICT=<KEEP|TRIM|CUT|RETIME> | WHY=<one clause>

Then finish with:
PACE REPORT: list every place the screen is static too long (dead air), every
hold that should be shortened, and any frames that waste the viewer's time
(repeated/identical frames, empty regions, redundant shots). Be blunt and
specific. The goal is a tighter, more professional cut.""".format(step=STEP)


def b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def ask(frames):
    content = [{"type": "text", "text": PROMPT}]
    for idx, path in frames:
        content.append({"type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64(path)}"}})
    body = {"model": MODEL, "messages": [{"role": "user", "content": content}],
            "max_tokens": 8192}
    req = urllib.request.Request(
        API, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
                 "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = json.loads(resp.read().decode())
    return data["choices"][0]["message"]["content"]


def main():
    names = sorted(os.listdir(FRAMES_DIR))
    frames = [(i * STEP, os.path.join(FRAMES_DIR, f)) for i, f in enumerate(names)
              if f.endswith(".png")]
    for start in range(0, len(frames), BATCH):
        chunk = frames[start:start + BATCH]
        print(f"\n===== FRAMES {start * STEP:.0f}s - {(start + len(chunk)) * STEP:.0f}s =====")
        print(ask(chunk))


if __name__ == "__main__":
    main()
