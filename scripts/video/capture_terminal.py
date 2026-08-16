#!/usr/bin/env python3
"""Record the terminal segment via a real browser-rendered terminal (ttyd).

Deterministic typing, no typos, full 1920x1080 resolution.
Produces: scripts/video/terminal-demo.webm
"""
import os
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT_DIR = Path(__file__).parent
TTYD_URL = os.environ.get("TTYD_URL", "http://127.0.0.1:7777")

COMMANDS = [
    ("./bin/blastfall scan ms@2.1.3", 3.5),
]


def type_slow(page, text, cps=32):
    for ch in text:
        page.keyboard.type(ch)
        time.sleep(1 / cps)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        ctx = browser.new_context(
            viewport={"width": 1440, "height": 810},
            record_video_dir=str(OUT_DIR / "term-capture"),
            record_video_size={"width": 1440, "height": 810},
        )
        page = ctx.new_page()
        page.goto(TTYD_URL, wait_until="networkidle")
        page.wait_for_selector(".terminal, .xterm", timeout=15000)
        time.sleep(1.5)
        # full-bleed dark terminal; remove any page chrome
        page.add_style_tag(content="html,body{background:#000!important;margin:0!important;}")
        time.sleep(0.3)
        # focus the terminal
        page.evaluate("document.querySelector('textarea').focus()")
        time.sleep(0.5)

        for cmd, hold in COMMANDS:
            type_slow(page, cmd)
            time.sleep(0.4)
            page.keyboard.press("Enter")
            time.sleep(hold)

        page.close()
        ctx.close()
        browser.close()

    videos = sorted((OUT_DIR / "term-capture").glob("*.webm"))
    if videos:
        dst = OUT_DIR / "terminal-demo.webm"
        os.replace(videos[-1], dst)
        print(f"video -> {dst}")
    else:
        print("no video recorded!")


if __name__ == "__main__":
    main()
