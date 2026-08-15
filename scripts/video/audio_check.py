#!/usr/bin/env python3
"""Have an audio-capable model listen to the voiceover track and report problems."""
import base64
import json
import os
import sys
import urllib.request

API = "https://opencode.ai/zen/go/v1/chat/completions"
MODEL = os.environ.get("AUDIO_MODEL", "mimo-v2.5")
KEY = os.environ["OPENAI_API_KEY"]
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/151.0.0.0 Safari/537.36")

PROMPT = """You are an audio QC engineer. I'm sending you the voiceover audio track
of a product demo video. Listen carefully and report:
1. TRANSCRIPTION: transcribe the narration exactly (best effort).
2. DOUBLING: any moment where two voices overlap (a doubled/slurred voice)?
   Give approximate timestamps.
3. DEAD AIR: any silent gap longer than ~3 seconds? Give timestamps.
4. PRONUNCIATION: any numbers or version strings mispronounced
   (e.g. "1,751", "4.3.7", "ms", "rc", "colors", "algo MSpaths")?
5. CLIPPING: any distortion/clipping or unnaturally loud bursts?
6. VERDICT: PASS or FIX, with the top 3 issues only.
Be blunt and specific with timestamps."""


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "voice-check.wav"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    content = [
        {"type": "text", "text": PROMPT},
        {"type": "input_audio",
         "input_audio": {"data": b64, "format": "wav"}},
    ]
    body = {"model": MODEL, "messages": [{"role": "user", "content": content}],
            "max_tokens": 4096}
    req = urllib.request.Request(
        API, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
                 "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = json.loads(resp.read().decode())
    print(data["choices"][0]["message"]["content"])


if __name__ == "__main__":
    main()
