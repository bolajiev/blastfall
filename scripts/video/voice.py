#!/usr/bin/env python3
"""Generate and place the TTS voiceover for the demo video.

Reads the assembled segment durations (cold / terminal / ui / result / card),
generates per-segment narration with edge-tts, delays each clip to its beat,
and mixes into a single voice track matching the video length.
Output: scripts/video/voice-track.m4a
"""
import asyncio
import os
import subprocess
import sys
from pathlib import Path

import edge_tts

OUT = Path(__file__).parent
VOICE = os.environ.get("VOICE", "en-US-ChristopherNeural")


def dur(f):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(f)]).decode().strip()
    return float(out)


async def tts(text, path):
    await edge_tts.Communicate(text, VOICE).save(str(path))


def main():
    cold = dur(OUT / "seg1-cold.mp4")
    term = dur(OUT / "seg2-terminal.mp4")
    ui = dur(OUT / "seg3-ui.mp4")
    close_a = dur(OUT / "seg4a-result.mp4")
    close_b = dur(OUT / "seg4b-card.mp4")
    total = cold + term + ui + close_a + close_b

    ui_s = cold + term
    card_s = ui_s + ui + close_a

    # (placement_ms, text)
    beats = [
        (int(cold * 0.15 * 1000), "In May twenty twenty-six, TanStack's CI pipeline was breached. "
         "Eighty-four malicious artifacts across forty-two packages, in six minutes. "
         "The defender's question: a package is compromised at nine a.m. "
         "Which of your services are exposed by nine oh six?"),
        (int((cold + 1.0) * 1000), "Blastfall ingests the real npm dependency graph into HydraDB. "
         "Every version, every publish date, every maintainer. "
         "Blast radius as a graph traversal, not a similarity search."),
        (int((cold + 11) * 1000), "We compromise ms, one of the most depended-on packages in the ecosystem. "
         "One thousand seven hundred fifty-one versions are exposed. Four of five services."),
        (int((ui_s + 2) * 1000), "Here's the reverse dependency closure. "
         "The graph walks incoming edges from the compromised node, out to every exposed version."),
        (int((ui_s + 12) * 1000), "Which version introduced the vulnerability? "
         "Debug first pulled in the bad release at four point three point seven, "
         "back in September twenty twenty-four."),
        (int((ui_s + 20) * 1000), "Set the attack time, and the resolution window shows exactly "
         "which releases shipped the compromised code before anyone knew."),
        (int((ui_s + 28) * 1000), "Packages that share a maintainer, and close name typosquats. "
         "Both are single hop traversals."),
        (int((ui_s + 38) * 1000), "Now the real attack: two hijacked packages, rc and colors. "
         "Their union blast radius: two thousand versions, eighty-two packages. "
         "One batched MSpaths call. A vector index cannot do this at all."),
        (int((card_s + 0.5) * 1000), "Blastfall. Powered by algo.MSpaths and object storage. "
         "Compromised at nine. Exposed by nine oh six."),
    ]

    clips = []
    for i, (ms, text) in enumerate(beats):
        mp3 = OUT / f"vo{i}.mp3"
        print(f"  tts[{i}] @ {ms / 1000:.1f}s ({len(text)} chars)")
        asyncio.run(tts(text, mp3))
        clips.append((ms, mp3))

    # build delayed clips and mix
    parts = []
    for i, (ms, mp3) in enumerate(clips):
        delayed = OUT / f"vo{i}_d.m4a"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(mp3),
                        "-af", f"adelay={ms}|{ms},apad", "-t", str(total),
                        "-c:a", "aac", "-b:a", "96k", str(delayed)], check=True)
        parts.append(str(delayed))

    filtergraph = "".join(f"[{i}:a]" for i in range(len(parts))) + \
        f"amix=inputs={len(parts)}:normalize=0:dropout_transition=0[out]"
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for p in parts:
        cmd += ["-i", p]
    cmd += ["-filter_complex", filtergraph, "-map", "[out]",
            "-c:a", "aac", "-b:a", "128k", str(OUT / "voice-track.m4a")]
    subprocess.run(cmd, check=True)

    for f in list(OUT.glob("vo*.mp3")) + list(OUT.glob("vo*_d.m4a")):
        f.unlink()
    print(f"voice-track.m4a ({total:.1f}s video)")


if __name__ == "__main__":
    main()
