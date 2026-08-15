#!/usr/bin/env python3
"""Generate and place the TTS voiceover for the demo video.

Each clip's leading/trailing silence is trimmed, clips are placed so they
never overlap (start = max(target, prev_end + gap)), and the mixed track is
written to voice-track.m4a. Numbers in the narration are spelled out for
correct pronunciation.
"""
import asyncio
import os
import subprocess
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


def trim_silence(mp3, trimmed):
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(mp3),
         "-af", ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,"
                 "areverse,"
                 "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,"
                 "areverse"),
         "-acodec", "libmp3lame", "-q:a", "4", str(trimmed)], check=True)


def main():
    cold = dur(OUT / "seg1-cold.mp4")
    term = dur(OUT / "seg2-terminal.mp4")
    ui = dur(OUT / "seg3-ui.mp4")
    close_a = dur(OUT / "seg4a-result.mp4")
    close_b = dur(OUT / "seg4b-card.mp4")
    total = cold + term + ui + close_a + close_b

    ui_s = cold + term
    card_s = ui_s + ui + close_a

    beats = [
        (0.3, "May twenty twenty-six. TanStack's CI pipeline is breached. "
         "Eighty-four malicious artifacts across forty-two packages, in six minutes. "
         "Compromised at nine a.m. Exposed by nine oh six."),
        (cold + 1.0, "Blastfall ingests the real npm dependency graph into HydraDB. "
         "Every version, publish date, maintainer. "
         "Blast radius as graph traversal, not similarity search."),
        (cold + 12.0, "We compromise ms, one of the most depended-on packages in the ecosystem. "
         "One thousand seven hundred fifty-one versions exposed. Four of five services."),
        (ui_s + 2.0, "Here's the reverse dependency closure. "
         "Incoming edges walked from the compromised node to every exposed version."),
        (ui_s + 14.0, "Which version introduced it? Debug first pulled in the bad release "
         "at four point three point seven, in September twenty twenty-four."),
        (ui_s + 24.0, "Set the attack time, and the resolution window shows which releases "
         "shipped the compromised code before anyone knew."),
        (ui_s + 34.0, "Shared maintainers, and close name typosquats. "
         "Both single hop traversals."),
        (ui_s + 42.0, "Now the real attack. Two hijacked packages, rc and colors. "
         "Two thousand exposed versions, eighty-two packages. "
         "One batched M S Paths call."),
        (ui_s + ui - 8.0, "A vector index cannot do this at all. "
         "Blast radius at six hops, well under a second."),
        (card_s - 5.0, "Blastfall. Powered by algo M S Paths and object storage. Compromised at nine. Exposed by nine oh six."),
    ]

    clips = []
    for i, (target, text) in enumerate(beats):
        mp3 = OUT / f"vo{i}.mp3"
        trimmed = OUT / f"vo{i}.trim.mp3"
        print(f"  tts[{i}] target@{target:.1f}s ({len(text)} chars)")
        asyncio.run(tts(text, mp3))
        trim_silence(mp3, trimmed)
        mp3.unlink()
        clips.append((target, trimmed, dur(trimmed)))

    placed = []
    prev_end = 0.0
    for target, mp3, d in clips:
        start = max(target, prev_end + 0.25)
        placed.append((start, mp3, d))
        prev_end = start + d
        print(f"  place[{mp3.stem}] start={start:.1f}s dur={d:.1f}s end={prev_end:.1f}s")

    parts = []
    for i, (start, mp3, d) in enumerate(placed):
        delayed = OUT / f"vo{i}_d.m4a"
        pad_before = int(start * 1000)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(mp3),
                        "-af", f"adelay={pad_before}|{pad_before}", "-c:a", "aac",
                        "-b:a", "96k", str(delayed)], check=True)
        parts.append(str(delayed))

    filtergraph = "".join(f"[{i}:a]" for i in range(len(parts))) + \
        f"amix=inputs={len(parts)}:normalize=0:dropout_transition=0,apad,alimiter=limit=0.95[out]"
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for p in parts:
        cmd += ["-i", p]
    cmd += ["-filter_complex", filtergraph, "-map", "[out]",
            "-t", str(total), "-c:a", "aac", "-b:a", "128k",
            str(OUT / "voice-track.m4a")]
    subprocess.run(cmd, check=True)

    for f in list(OUT.glob("vo[0-9]*")):
        if f.is_file():
            f.unlink()
    print(f"voice-track.m4a ({total:.1f}s video, {len(placed)} non-overlapping clips)")


if __name__ == "__main__":
    main()
