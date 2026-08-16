#!/usr/bin/env bash
# Assemble the Blastfall demo video: cold open + terminal take + UI take + close,
# with burned-in captions. Output: scripts/video/blastfall-demo.mp4
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
COLD_MS=2500
CLOSE_MS=6000

# --- cold open card ---
printf '%s\n' \
  'TanStack, May 2026' \
  '84 malicious artifacts across 42 packages in 6 minutes' \
  '' \
  "The defender's question: compromised at 09:00," \
  'which of my services are exposed by 09:06?' > /tmp/cold.txt
ffmpeg -y -v error -f lavfi -i color=c=0x0d1117:s=1920x1080:d=${COLD_MS}ms \
  -vf "drawtext=text='Blastfall':fontfile=${FONT}:fontcolor=0xf85149:fontsize=72:x=(w-text_w)/2:y=200, \
       drawtext=textfile=/tmp/cold.txt:fontfile=${FONT}:fontcolor=white:fontsize=44:line_spacing=28:x=(w-text_w)/2:y=420" \
  -r 60 -c:v libx264 -preset fast -crf 20 -pix_fmt yuv420p seg1-cold.mp4

# --- terminal take (crisp, real terminal via ttyd; recorded at 1440x810) ---
ffmpeg -y -v error -ss 2.2 -i terminal-demo.webm -vf "scale=1920:1080:flags=lanczos" \
  -r 60 -c:v libx264 -preset fast -crf 20 -pix_fmt yuv420p seg2-terminal.mp4

# --- UI take (fresh from the latest capture), slowed ~0.9x, skip lead-in ---
ffmpeg -y -v error -ss 0.5 -i ui-demo.webm -filter_complex "[0:v]setpts=1/0.9*PTS[v]" -map "[v]" \
  -r 60 -c:v libx264 -preset fast -crf 20 -pix_fmt yuv420p seg3-ui.mp4

# --- closing: the last query result (clean), then a callout card ---
ffmpeg -y -v error -loop 1 -i worm-result.png -t 5000ms -r 60 \
  -c:v libx264 -preset fast -crf 20 -pix_fmt yuv420p seg4a-result.mp4
ffmpeg -y -v error -f lavfi -i color=c=0x0d1117:s=1920x1080:d=${CLOSE_MS}ms \
  -vf "drawtext=text='Blastfall':fontfile=${FONT}:fontcolor=0xf85149:fontsize=72:x=(w-text_w)/2:y=320, \
       drawtext=text='Powered by algo.MSpaths + object storage':fontfile=${FONT}:fontcolor=white:fontsize=38:x=(w-text_w)/2:y=480, \
       drawtext=text='- not a vector index -':fontfile=${FONT}:fontcolor=0x8b949e:fontsize=30:x=(w-text_w)/2:y=560, \
       drawtext=text='Hack Hydra 2026':fontfile=${FONT}:fontcolor=0x30363d:fontsize=26:x=(w-text_w)/2:y=660" \
  -r 60 -c:v libx264 -preset fast -crf 20 -pix_fmt yuv420p seg4b-card.mp4

# --- timing + captions ---
python3 - "$COLD_MS" "$CLOSE_MS" <<'PY'
import sys, subprocess

def dur(f):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", f]).decode().strip()
    return float(out)

cold = dur("seg1-cold.mp4")
term = dur("seg2-terminal.mp4")
ui = dur("seg3-ui.mp4")
close_a = dur("seg4a-result.mp4")
close_b = dur("seg4b-card.mp4")

t1 = cold
t2 = t1 + term
t3 = t2 + ui
t4 = t3 + close_a
t5 = t4 + close_b

def cap(start, end, text):
    def fmt(t):
        h = int(t // 3600); m = int((t % 3600) // 60); s = int(t % 60); ms = int(round((t - int(t)) * 1000))
        if ms == 1000: s += 1; ms = 0
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    return f"{fmt(start)} --> {fmt(end)}\n{text}\n"

srt = []
i = 1
for st, en, txt in [
    (t1, t1 + 3, "Blastfall"),
    (t2 + 1.0, t2 + 8.0, "Blastfall: the real npm dependency graph in HydraDB."),
    (t3 + 1.0, t3 + 8.0, "The reverse-dependency closure - 1,751 versions, 4 of 5 services - walked as incoming DEPENDS_ON edges."),
    (t3 + 14.0, t3 + 26.0, "Which version introduced it: debug@4.3.7 first pulled in ms@2.1.3 (Sep 2024). Resolution window: releases that shipped the bad version between publish and discovery."),
    (t3 + 32.0, t3 + 40.0, "Shared maintainers and close-name typosquats - single-hop traversals."),
    (t3 + 44.0, t3 + 56.0, "A reverse closure over millions of versioned nodes - a vector index cannot do this at all. rc + colors: 2,000 exposed versions in one algo.MSpaths call."),
]:
    srt.append(f"{i}\n" + cap(st, en, txt)); i += 1

with open("captions.srt", "w") as f:
    f.write("\n".join(srt))

print(f"cold={cold:.2f} term={term:.2f} ui={ui:.2f} result={close_a:.2f} card={close_b:.2f} total={t5:.2f}")
PY

# --- concat (voiceover carries the narration; no burned-in captions) ---
printf "file 'seg1-cold.mp4'\nfile 'seg2-terminal.mp4'\nfile 'seg3-ui.mp4'\nfile 'seg4a-result.mp4'\nfile 'seg4b-card.mp4'\n" > list.txt
ffmpeg -y -v error -f concat -safe 0 -i list.txt \
  -c:v libx264 -preset fast -crf 20 -pix_fmt yuv420p blastfall-silent.mp4

# --- voiceover ---
echo "generating voiceover..."
python3 voice.py

# --- mux ---
ffmpeg -y -v error -i blastfall-silent.mp4 -i voice-track.m4a \
  -c:v copy -c:a aac -b:a 128k -shortest blastfall-demo.mp4

echo "done -> blastfall-demo.mp4 (with voiceover)"
