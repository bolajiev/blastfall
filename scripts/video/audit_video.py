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

PROMPT = """You are auditing this video while operating under a strict
engineering operating doctrine (the "all-you-need-skill"). Apply its
non-negotiables to the audit itself:

1. VERIFY, DON'T ASSUME. Every verdict must cite evidence you can actually see
   in the frame (specific text, specific element, specific pixel-level issue).
   Never write "probably fine" or "it should work". If you cannot confirm
   something from the image, say "cannot verify from this frame".
2. NO STOPGAPS. Anything that LOOKS done but isn't (a caption overlapping UI,
   a broken/truncated element, a fake-looking result, misaligned text, a
   recording artifact passed off as a transition) must be named as a defect,
   not waved through. Call out slop.
3. SAY WHEN TO STOP. If a frame is ambiguous (you can't tell what it shows or
   whether text is legible), say so explicitly with "AMBIGUOUS:" — do not guess
   a verdict.
4. AUDIT TRAIL. Every issue gets a timestamp (T=...) and is reproducible.
5. You are a senior video editor reviewing a hackathon product-demo reel for
   judges, not a friend. Be blunt.

I am sending you stills sampled every {step} seconds from a ~1:40 demo video
of a software supply-chain security tool.

For EACH frame, output exactly one line:
T={{t:.1f}}s | SHOT=<what's on screen, 4-8 words> | VERDICT=<KEEP|TRIM|CUT|RETIME> | WHY=<one clause, evidence-based>

Then finish with:
PACE REPORT: list every place the screen is static too long (dead air), every
hold that should be shortened, and any frames that waste the viewer's time
(repeated/identical frames, empty regions, redundant shots).
DEFECT LIST: every named stopgap-style defect with its timestamp, one line
each. Be specific and blunt.""".format(step=STEP)


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
