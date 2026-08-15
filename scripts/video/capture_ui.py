#!/usr/bin/env python3
"""Record the Blastfall UI demo with a scripted, visible cursor.

Produces: scripts/video/ui-demo.webm (page video at 1920x1080).
Run against a live app: http://localhost:8123
"""
import os
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BLASTFALL_URL", "http://localhost:8123")
OUT_DIR = Path(__file__).parent

CURSOR_JS = """
(() => {
  const c = document.createElement('div');
  c.id = 'fakecursor';
  c.style.cssText = 'position:fixed;top:0;left:0;z-index:99999;pointer-events:none;'
    + 'width:30px;height:30px;margin:-15px 0 0 -15px;border:3px solid #f85149;'
    + 'border-radius:50%;background:rgba(248,81,73,.28);box-shadow:0 0 12px rgba(248,81,73,.6);';
  const d = document.createElement('div');
  d.style.cssText = 'position:absolute;top:50%;left:50%;width:6px;height:6px;'
    + 'margin:-3px 0 0 -3px;border-radius:50%;background:#fff;';
  c.appendChild(d);
  document.documentElement.appendChild(c);
  window.__cursor = c;
  document.addEventListener('mousemove', e => {
    c.style.left = e.clientX + 'px';
    c.style.top = e.clientY + 'px';
  });
})();
"""


def pause(page, seconds):
    time.sleep(seconds)


def move(page, x, y, steps=30):
    page.mouse.move(x, y, steps=steps)
    time.sleep(0.15)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        ctx = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=str(OUT_DIR / "ui-capture"),
            record_video_size={"width": 1920, "height": 1080},
        )
        page = ctx.new_page()
        page.goto(BASE, wait_until="networkidle")
        page.add_script_tag(content=CURSOR_JS)
        page.evaluate("document.body.style.zoom = '1.35'")
        time.sleep(2)

        # load featured incidents
        page.wait_for_selector("#incidents .tag", timeout=15000)
        time.sleep(1)

        # --- compromise ms@2.1.3 via featured chip ---
        chip = page.locator("#incidents .tag[data-spec='ms@2.1.3']")
        box = chip.bounding_box()
        move(page, box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        pause(page, 0.5)
        chip.click()
        page.wait_for_selector("#results", state="visible", timeout=20000)
        pause(page, 6)  # graph reveal animation
        # center the exposure-map graph so the whole closure is visible
        page.evaluate("document.querySelector('#graph-panel').scrollIntoView({block:'center'})")
        move(page, 1700, 100)
        pause(page, 3)  # read the cards + graph (cursor in header)

        # --- scroll through the report ---
        for sel, hold in [("#intro-panel", 4), ("#dependents", 3)]:
            page.evaluate(f"document.querySelector('{sel}').scrollIntoView({{block:'center'}})")
            move(page, 1700, 100)
            pause(page, hold)

        # --- attack time + resolution window ---
        now = time.strftime("%Y-%m-%dT%H:%M", time.gmtime())
        at = page.locator("#attack")
        at.fill(now)
        go = page.locator("#go")
        gb = go.bounding_box()
        move(page, gb["x"] + gb["width"] / 2, gb["y"] + gb["height"] / 2)
        pause(page, 0.3)
        go.click()
        page.wait_for_timeout(2200)
        page.evaluate("window.scrollTo(0, 0)")
        move(page, 1700, 100)
        pause(page, 2)
        page.evaluate("document.querySelector('#window-panel').scrollIntoView({block:'center'})")
        move(page, 1700, 100)
        pause(page, 3.5)

        # --- shared maintainers + typosquats ---
        page.evaluate("document.querySelector('#mnts').scrollIntoView({block:'center'})")
        move(page, 1700, 100)
        pause(page, 2)
        page.evaluate("document.querySelector('#typos').scrollIntoView({block:'center'})")
        move(page, 1700, 100)
        pause(page, 2)

        # --- worm scenario (MSpaths) ---
        page.evaluate("document.querySelector('.panel').scrollIntoView({block:'start'})")
        pause(page, 0.5)
        worm = page.locator("#worm")
        worm.fill("rc, colors")
        wb = page.locator("#wormgo").bounding_box()
        move(page, wb["x"] + wb["width"] / 2, wb["y"] + wb["height"] / 2)
        pause(page, 0.3)
        page.locator("#wormgo").click()
        page.wait_for_timeout(5000)  # union traversal
        move(page, 1700, 100)
        pause(page, 4)  # hold on the result
        page.screenshot(path=str(OUT_DIR / "worm-result.png"))

        page.close()
        ctx.close()
        browser.close()

    # locate the recorded video
    videos = sorted((OUT_DIR / "ui-capture").glob("*.webm"))
    if videos:
        dst = OUT_DIR / "ui-demo.webm"
        os.replace(videos[-1], dst)
        print(f"video -> {dst}")
    else:
        print("no video recorded!")


if __name__ == "__main__":
    main()
