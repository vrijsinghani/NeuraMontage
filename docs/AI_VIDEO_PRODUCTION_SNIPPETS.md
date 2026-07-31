# AI Video Production Snippets

**Purpose:** copy/paste-ready code references for future transformation ads.  
**Companion doc:** `/home/vikas/video-poc/docs/AI_VIDEO_PRODUCTION_RUNBOOK.md`

Replace `{project}`, paths, reference IDs, and prompts per project. Never store real API keys in these files.

---

## 1. Environment and preflight

```bash
set -a
source ~/.hermes/.env
set +a

cd /home/vikas/video-poc
.venv/bin/python -c 'from google import genai; print("google-genai OK")'
ffmpeg -version | head -1
ffprobe -version | head -1
fc-list | grep -i 'Montserrat\|Anton' | head
```

Check keys without printing them:

```bash
python3 - <<'PY'
from pathlib import Path
lines = Path.home().joinpath('.hermes/.env').read_text().splitlines()
for key in ['GEMINI_API_KEY', 'XAI_API_KEY', 'ELEVENLABS_API_KEY', 'FISH_API_KEY']:
    present = any(x.startswith(key + '=') and x.split('=', 1)[1].strip() for x in lines)
    print(key, 'present' if present else 'missing')
PY
```

---

## 2. Project directories

```bash
PROJECT=client-transformation
NAS=/mnt/nas/public/video-gen/$PROJECT
mkdir -p "$NAS"/{assets,music,manifests}
```

Expected durable layout:

```text
/mnt/nas/public/video-gen/{project}/
├── assets/
├── music/
├── manifests/
├── brand.yaml
├── script.txt
├── vo-timestamped.mp3
├── vo-alignment.json
├── captions.ass
├── video-only.mp4
└── output.mp4
```

---

## 3. xAI Grok image edit — canonical room / craft still

Use for canonical before/after, architecture-locked edits, logo-conditioned people stills, and hard spatial edits.

```python
import base64, os
from pathlib import Path
import requests

KEY = os.environ['XAI_API_KEY']

def data_uri(path):
    path = Path(path)
    return f"data:image/png;base64,{base64.b64encode(path.read_bytes()).decode()}"

payload = {
    'model': 'grok-imagine-image-quality',
    'prompt': '''Edit IMAGE 1 while preserving the exact architecture and camera position.
Use IMAGE 2 only for identity. Use IMAGE 3 only for the exact logo mark.
Keep scale physically credible. No room redesign. No text overlays.''',
    'images': [
        {'url': data_uri('/path/to/setting.png'), 'type': 'image_url'},
        {'url': data_uri('/path/to/person.png'), 'type': 'image_url'},
        {'url': data_uri('/path/to/logo-plate.png'), 'type': 'image_url'},
    ],
    'aspect_ratio': '9:16',
    'resolution': '2k',
    'response_format': 'b64_json',
}

r = requests.post(
    'https://api.x.ai/v1/images/edits',
    headers={
        'Authorization': f'Bearer {KEY}',
        'Content-Type': 'application/json',
    },
    json=payload,
    timeout=300,
)
r.raise_for_status()
item = r.json()['data'][0]
Path('/path/to/output.png').write_bytes(base64.b64decode(item['b64_json']))
```

Aspect-ratio rule:

- **single-image edit inherits source aspect ratio**
- **multi-image edit can override aspect ratio**

OpenMontage reference:

- `/tmp/openmontage-review/tools/graphics/grok_image.py:159-202`
- `/tmp/openmontage-review/tools/graphics/grok_image.py:225-296`

---

## 4. xAI Grok image-to-video

Use for approved stills only.

```python
import base64, os, time
from pathlib import Path
import requests

KEY = os.environ['XAI_API_KEY']
still = Path('/path/to/approved-still.png')
out = Path('/path/to/clip.mp4')

payload = {
    'model': 'grok-imagine-video-1.5',
    'prompt': '''Image-to-video from the exact first frame.
One continuous real-time action only. Camera stays close to the work.
Preserve identity, materials, and room geometry. No cuts, no morphing, no text, no music.''',
    'image': {
        'url': f"data:image/png;base64,{base64.b64encode(still.read_bytes()).decode()}"
    },
    'duration': 4,
    'aspect_ratio': '9:16',
    'resolution': '720p',
}

headers = {
    'Authorization': f'Bearer {KEY}',
    'Content-Type': 'application/json',
}

r = requests.post(
    'https://api.x.ai/v1/videos/generations',
    headers=headers,
    json=payload,
    timeout=60,
)
r.raise_for_status()
request_id = r.json()['request_id']

while True:
    result = requests.get(
        f'https://api.x.ai/v1/videos/{request_id}',
        headers={'Authorization': headers['Authorization']},
        timeout=30,
    )
    result.raise_for_status()
    data = result.json()
    status = data.get('status')
    if status == 'done':
        url = data['video']['url']
        out.write_bytes(requests.get(url, timeout=300).content)
        break
    if status in {'failed', 'expired'}:
        raise RuntimeError(data)
    time.sleep(5)
```

OpenMontage reference:

- `/tmp/openmontage-review/tools/video/grok_video.py:183-219`
- `/tmp/openmontage-review/tools/video/grok_video.py:221-304`

---

## 5. Gemini people-into-room still generation

Use the kitchen-proven wrapper order:

1. portrait refs first
2. setting plate last
3. preserve identity + architecture
4. describe people relative to furniture

```python
from pathlib import Path
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])

prompt = '''Preserve the exact identities, faces, hair, ages, and wardrobe from the attached reference portraits.
The final attached image is the canonical setting reference. Preserve its exact room footprint,
ceiling height, window and doorway positions, appliance locations, cabinet runs, worktable position,
camera axis, and architectural proportions. Change only the finishes, people, or construction state
explicitly requested. Add the exact installer from the portrait standing relative to the vanity,
with normal adult scale. MANDATORY vertical 9:16 portrait first frame for a phone video.'''

contents = [
    types.Part.from_bytes(data=Path('/path/to/portrait.png').read_bytes(), mime_type='image/png'),
    types.Part.from_bytes(data=Path('/path/to/logo.png').read_bytes(), mime_type='image/png'),
    types.Part.from_bytes(data=Path('/path/to/setting.png').read_bytes(), mime_type='image/png'),
    types.Part.from_text(text=prompt),
]

response = client.models.generate_content(
    model='gemini-3.1-flash-image',
    contents=contents,
    config=types.GenerateContentConfig(
        response_modalities=['IMAGE'],
        image_config=types.ImageConfig(aspect_ratio='9:16', image_size='2K'),
    ),
)

for part in response.candidates[0].content.parts:
    data = getattr(getattr(part, 'inline_data', None), 'data', None)
    if data:
        Path('/path/to/still.png').write_bytes(data)
        break
```

Code reference:

- `/home/vikas/video-poc/project_pipeline.py:62-91`

---

## 6. Veo image-to-video

```python
from pathlib import Path
from google import genai
from google.genai import types
import time

client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])

operation = client.models.generate_videos(
    model='veo-3.1-fast-generate-preview',
    source=types.GenerateVideosSource(
        prompt='One simple action and one camera move only.',
        image=types.Image(
            image_bytes=Path('/path/to/keyframe.png').read_bytes(),
            mime_type='image/png',
        ),
    ),
    config=types.GenerateVideosConfig(
        aspect_ratio='9:16',
        resolution='720p',
        duration_seconds=8,
        number_of_videos=1,
        person_generation='allow_adult',
    ),
)

while not operation.done:
    time.sleep(10)
    operation = client.operations.get(operation)

video = operation.response.generated_videos[0]
client.files.download(file=video.video)
video.video.save('/path/to/clip.mp4')
```

Code reference:

- `/home/vikas/video-poc/project_pipeline.py:175-198`

---

## 7. Vision QC helper

Use strict JSON QC on stills and motion strips, but do not let it override informed human playback.

```python
import base64, json, urllib.request
from pathlib import Path

def b64(path):
    return base64.b64encode(Path(path).read_bytes()).decode()

content = [
    {'type': 'text', 'text': 'Return ONLY JSON. Judge scale, room lock, logo match, and action believability.'},
    {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + b64('/path/to/image.png')}},
]
payload = {
    'model': 'chatgpt/gpt-5.6-luna',
    'stream': True,
    'max_completion_tokens': 1200,
    'messages': [{'role': 'user', 'content': content}],
}
req = urllib.request.Request(
    'http://192.168.1.160:4000/v1/chat/completions',
    data=json.dumps(payload).encode(),
    headers={
        'Authorization': 'Bearer YOUR_LITELLM_KEY',
        'Content-Type': 'application/json',
    },
)
with urllib.request.urlopen(req, timeout=300) as response:
    text = ''
    for raw in response:
        line = raw.decode().strip()
        if line.startswith('data: ') and line != 'data: [DONE]':
            event = json.loads(line[6:])
            text += ''.join(c.get('delta', {}).get('content', '') for c in event.get('choices', []))
print(text)
```

Code reference:

- `/home/vikas/video-poc/project_pipeline.py:103-139`

---

## 8. Fish Audio TTS

Use for distinctive voices. Remember: API credit is separate from platform credit.

```python
import json, os
from pathlib import Path
import urllib.request

payload = {
    'text': 'Your short line here.',
    'reference_id': 'e1d994592ff24fd292a5bb6e58240dee',
    'format': 'mp3',
    'mp3_bitrate': 192,
    'normalize': True,
    'latency': 'normal',
    'prosody': {'speed': 1.0},
}

req = urllib.request.Request(
    'https://api.fish.audio/v1/tts',
    data=json.dumps(payload).encode(),
    headers={
        'Authorization': f"Bearer {os.environ['FISH_API_KEY']}",
        'Content-Type': 'application/json',
        'model': 's2.1-pro-free',
    },
    method='POST',
)
with urllib.request.urlopen(req, timeout=180) as response:
    audio = response.read()
Path('/path/to/vo-line.mp3').write_bytes(audio)
```

Useful models:

- `s2.1-pro-free` for test/dev
- `s2.1-pro` for production

Docs path verified during production:

- `POST https://api.fish.audio/v1/tts`
- required header: `model`

---

## 9. ElevenLabs timestamped VO

Existing helper:

```bash
cd /home/vikas/video-poc
.venv/bin/python generate_vo.py \
  --script /path/to/script.txt \
  --out /mnt/nas/public/video-gen/{project}/ \
  --voice Brian \
  --stability 0.35 \
  --similarity 0.85 \
  --style 0.25
```

Core request shape:

- `POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps`
- outputs `vo-timestamped.mp3` and `vo-alignment.json`

Code reference:

- `/home/vikas/video-poc/generate_vo.py:60-91`
- `/home/vikas/video-poc/generate_vo.py:122-159`

---

## 10. Beat-aligned VO synthesis for non-timestamped providers

When a provider does not return word alignment, generate one line per beat and synthesize alignment from actual beat timing and segment durations.

```python
import json, subprocess
from pathlib import Path

beats = [
    ('before', 0.0, 3.2, "Your bathroom shouldn't feel stuck in another decade."),
    ('walk', 3.1, 3.0, 'This is the before.'),
    ('pry', 6.0, 2.6, 'The tear-out.'),
    ('tile', 8.5, 2.6, 'The craft.'),
    ('vanity', 11.0, 2.6, 'Every finish, designed together.'),
    ('detail', 13.5, 3.2, 'Then the crew finishes strong.'),
    ('reveal', 16.7, 7.5, 'This is the reveal.'),
    ('cta_hold', 24.0, 6.0, 'Arlington, Garland, Duncanville — free estimate at idealfloors.com.'),
]

chars = []
starts = []
ends = []

for beat, start, duration, text in beats:
    audio = Path(f'/path/to/{beat}.mp3')
    seg_dur = float(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'csv=p=0', str(audio)
    ], text=True).strip())
    g0 = start + 0.12
    max_fit = max(0.4, duration - 0.25)
    atempo = min(1.25, seg_dur / max_fit) if seg_dur > max_fit else 1.0
    g1 = g0 + seg_dur / atempo
    n = len(text)
    span = max(0.05, g1 - g0)
    for i, ch in enumerate(text):
        starts.append(round(g0 + span * (i / max(1, n)), 4))
        ends.append(round(g0 + span * ((i + 1) / max(1, n)), 4))
        chars.append(ch)
    # explicit gap so caption phrase segmentation does not merge beats
    chars.append(' ')
    starts.append(round(g1 + 0.02, 4))
    ends.append(round(g1 + 0.25, 4))

alignment = {
    'characters': chars,
    'character_start_times_seconds': starts,
    'character_end_times_seconds': ends,
}
Path('/path/to/vo-alignment.json').write_text(json.dumps(alignment, indent=2))
```

---

## 11. Build an aligned VO track from beat lines

```bash
# This pattern uses delayed per-beat clips and mixes them into a 30s VO track.
# Generate each line first, then place it at its beat start.
```

Python pattern:

```python
import subprocess
from pathlib import Path

items = [
    (0.12, '/path/to/before.mp3'),
    (3.23, '/path/to/walk.mp3'),
    (6.13, '/path/to/pry.mp3'),
    (8.65, '/path/to/tile.mp3'),
    (11.18, '/path/to/vanity.mp3'),
    (13.70, '/path/to/detail.mp3'),
    (16.81, '/path/to/reveal.mp3'),
    (24.20, '/path/to/cta.mp3'),
]
total = 30.0
inputs = []
filters = []
for i, (start, path) in enumerate(items):
    delay = int(start * 1000)
    inputs.extend(['-i', path])
    filters.append(
        f'[{i}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,'
        f'volume=1.0,adelay={delay}|{delay},apad=whole_dur={total}[a{i}]'
    )
filters.append(
    ''.join(f'[a{i}]' for i in range(len(items))) +
    f'amix=inputs={len(items)}:duration=longest:dropout_transition=0,'
    f'atrim=0:{total},loudnorm=I=-16:TP=-2:LRA=11[out]'
)
out = Path('/path/to/vo-aligned.mp3')
subprocess.check_call([
    'ffmpeg', '-y', '-loglevel', 'error',
    *inputs,
    '-filter_complex', ';'.join(filters),
    '-map', '[out]',
    '-c:a', 'libmp3lame', '-b:a', '192k',
    str(out),
])
```

---

## 12. Clean timeline assembly with crossfades

```python
import subprocess
from pathlib import Path

clips = [
    ('/path/to/before.mp4', 0.0, 3.2, 'before'),
    ('/path/to/walk.mp4', 0.15, 3.0, 'walk'),
    ('/path/to/pry.mp4', 0.25, 2.6, 'pry'),
    ('/path/to/tile.mp4', 0.30, 2.6, 'tile'),
    ('/path/to/vanity.mp4', 0.25, 2.6, 'vanity'),
    ('/path/to/detail.mp4', 0.15, 3.2, 'detail'),
    ('/path/to/reveal.mp4', 0.30, 7.5, 'reveal'),
]

work = Path('/path/to/work')
work.mkdir(parents=True, exist_ok=True)
parts = []
for i, (src, ss, dur, tag) in enumerate(clips):
    out = work / f'p{i:02d}_{tag}.mp4'
    subprocess.check_call([
        'ffmpeg', '-y', '-loglevel', 'error',
        '-ss', f'{ss:.3f}', '-t', f'{dur:.3f}', '-i', src,
        '-vf', 'scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,fps=24,setsar=1,format=yuv420p',
        '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '17',
        str(out),
    ])
    parts.append((out, dur))

fade = 0.10
inputs = []
for p, _ in parts:
    inputs.extend(['-i', str(p)])
filters = [f'[{i}:v]setpts=PTS-STARTPTS,fps=24,format=yuv420p[v{i}]' for i in range(len(parts))]
cur = 'v0'
cur_dur = parts[0][1]
for i in range(1, len(parts)):
    offset = max(0.01, cur_dur - fade)
    outlab = f'x{i}' if i < len(parts) - 1 else 'vout'
    filters.append(f'[{cur}][v{i}]xfade=transition=fade:duration={fade}:offset={offset:.3f}[{outlab}]')
    cur = outlab
    cur_dur = cur_dur + parts[i][1] - fade
subprocess.check_call([
    'ffmpeg', '-y', '-loglevel', 'error',
    *inputs,
    '-filter_complex', ';'.join(filters),
    '-map', '[vout]',
    '-c:v', 'libx264', '-preset', 'fast', '-crf', '17', '-r', '24',
    str(work / 'video.mp4'),
])
```

If more runtime is needed:

- use longer native selects from unique clips
- or add a declared after still hold for CTA space

Do **not** solve runtime with random repeats.

---

## 13. Brand YAML

```yaml
brand:
  name: "iDeal Floors"
  name_vo: "iDeal Floors"
  logo: "assets/logo.png"
  colors:
    accent: "#72bf44"
    text: "#ffffff"
    background: "#151515"
  fonts:
    display: "Anton"
    narration: "Montserrat ExtraBold"
    body: "Montserrat"
  emphasis_words: [bathroom, before, tear-out, craft, reveal, vanity, quartz, tile, flooring, together, free, estimate]
  cta:
    headline: "Schedule Your Free In-Home Estimate"
    website: "idealfloors.com"
    locations:
      - city: "DFW Showrooms"
        address: "Arlington | Garland | Duncanville"
        phone: "972-4-FLOORS"
frame:
  width: 720
  height: 1280
  max_caption_width: 680
  safe_zone_y: [430, 830]
captions:
  max_duration: 3.0
  max_words: 4
  min_gap: 0.12
  min_display: 0.7
  fontsize_narration: 48
  fontsize_display: 58
  fontsize_cta: 34
  fontsize_location: 25
  fontsize_website: 25
endcard:
  duration: 6.0
  start_at: "vo_end"
```

---

## 14. Generate captions and render via caption engine

```bash
cd /home/vikas/video-poc
.venv/bin/python caption_engine.py \
  --brand brands/{project}.yaml \
  --output-dir /mnt/nas/public/video-gen/{project} \
  --alignment /mnt/nas/public/video-gen/{project}/vo-alignment.json \
  --video /mnt/nas/public/video-gen/{project}/video-only.mp4 \
  --vo /mnt/nas/public/video-gen/{project}/vo-timestamped.mp3 \
  --music /mnt/nas/public/video-gen/{project}/music/music.mp3 \
  --out /mnt/nas/public/video-gen/{project}/output.mp4
```

Code references:

- `/home/vikas/video-poc/caption_engine.py:128-168` — words from alignment
- `/home/vikas/video-poc/caption_engine.py:187-259` — phrase segmentation
- `/home/vikas/video-poc/caption_engine.py:274-361` — animation/emphasis
- `/home/vikas/video-poc/caption_engine.py:364-458` — narration and card events
- `/home/vikas/video-poc/caption_engine.py:463-539` — ASS + render
- `/home/vikas/video-poc/caption_engine.py:544-590` — CLI

---

## 15. Final render filter shape

Use when rendering manually instead of through `caption_engine.py`.

```python
import subprocess
from pathlib import Path

vo_end = 29.86
card_duration = 6.0
final_dur = vo_end + card_duration
fw, fh = 720, 1280
accent = '72bf44'
bg = '151515'
fontsdir = str(Path.home() / '.local/share/fonts')

ass_path = '/path/to/captions.ass'
ass_esc = ass_path.replace('\\', '\\\\').replace(':', '\\:').replace("'", "\\'")
fonts_esc = fontsdir.replace('\\', '\\\\').replace(':', '\\:').replace("'", "\\'")

filter_complex = (
    f"[1:v]scale=160:-1,format=rgba,colorchannelmixer=aa=0.90[logo];"
    f"[0:v]fps=24,format=yuv420p,setsar=1[basev];"
    f"[basev]tpad=stop_mode=clone:stop_duration={max(0.1, final_dur - 30.0):.3f}[vext];"
    f"[vext][logo]overlay=532:24[vl];"
    f"[vl]drawbox=x=0:y={fh - 340}:w={fw}:h=340:color=0x{bg}@0.72:t=fill:"
    f"enable='between(t,{vo_end:.3f},{final_dur:.3f})'[vb];"
    f"[vb]drawbox=x=0:y={fh - 340}:w={fw}:h=4:color=0x{accent}@0.95:t=fill:"
    f"enable='between(t,{vo_end:.3f},{final_dur:.3f})'[vc];"
    f"[vc]ass='{ass_esc}':fontsdir='{fonts_esc}'[vout];"
    f"[2:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
    f"volume=1.2,apad=whole_dur={final_dur:.3f}[vo];"
    f"[3:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
    f"atrim=0:{final_dur:.3f},asetpts=PTS-STARTPTS,"
    f"volume=0.28,afade=t=in:st=0:d=0.5,"
    f"afade=t=out:st={final_dur - 2.0:.3f}:d=2.0,"
    f"volume='if(lt(t,{vo_end:.3f}),0.55,1.25)':eval=frame[mus];"
    f"[vo][mus]amix=inputs=2:duration=longest:dropout_transition=0,"
    f"loudnorm=I=-14:TP=-1.5:LRA=11[aout]"
)

subprocess.check_call([
    'ffmpeg', '-y', '-loglevel', 'error',
    '-i', '/path/to/video-only.mp4',
    '-i', '/path/to/logo.png',
    '-i', '/path/to/vo-timestamped.mp3',
    '-stream_loop', '-1', '-i', '/path/to/music.mp3',
    '-filter_complex', filter_complex,
    '-t', f'{final_dur:.3f}',
    '-map', '[vout]', '-map', '[aout]',
    '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-r', '24',
    '-c:a', 'aac', '-b:a', '192k',
    '-movflags', '+faststart',
    '/path/to/output.mp4',
])
```

Important:

- final duration = `vo_end + card_duration`
- avoid `-shortest` if it hides the end card
- `tpad=stop_mode=clone` is only for the declared end-card extension, not for hiding missing moving footage

---

## 16. Structural QA

```bash
cd /home/vikas/video-poc
.venv/bin/python qa_captions.py /mnt/nas/public/video-gen/{project}/captions.ass \
  --brand "iDeal Floors" \
  --vo-end 29.86 \
  --video-duration 35.86 \
  --min-display 0.7 \
  --max-width 680

.venv/bin/python qa_video.py /mnt/nas/public/video-gen/{project}/output.mp4 \
  --vo-end 29.86 \
  --duration 35.86
```

Check audio presence:

```bash
ffmpeg -i /mnt/nas/public/video-gen/{project}/output.mp4 \
  -af volumedetect -f null - 2>&1 | grep -E 'mean_volume|max_volume|Duration'
```

---

## 17. Common ffmpeg probes

```bash
ffprobe -v error \
  -show_entries format=duration,size \
  -show_entries stream=codec_type,codec_name,width,height \
  -of default=noprint_wrappers=1 \
  /path/to/file.mp4
```

Scene-cut heuristic only, not final approval:

```bash
ffmpeg -i /path/to/clip.mp4 \
  -vf "select='gt(scene,0.3)',showinfo" -f null - 2>&1 | grep -c pts_time
```

Motion strip for review:

```bash
ffmpeg -y -loglevel error -i /path/to/clip.mp4 \
  -vf "fps=1,scale=160:-1,tile=8x1" -frames:v 1 \
  /path/to/clip-strip.jpg
```

---

## 18. What not to do

Do not:

- animate unapproved stills
- use full-body people pastes as identity anchors
- ask a model to preserve architecture and redesign the room in the same call
- use prose-only logo descriptions on workwear
- generate wide full-room people plates for process Reels
- accept a still merely because a vision model scored it high
- stretch five seconds of footage across longer narration with loops, slowdowns, or frozen tails
- put unrelated lines together in one TTS file and hope captions align magically
- write API keys into project files
- conclude a model “can’t” before checking endpoint, request shape, model name, and provider credits
