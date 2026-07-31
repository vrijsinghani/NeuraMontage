# Repeatable AI Video-Ad Production Runbook

**Audience:** humans and AI agents producing short-form transformation ads  
**Primary use case:** home-services / flooring / kitchen / bathroom transformation Reels  
**Output target:** vertical 9:16, ~30–40s, coherent before → process → after story with beat-aligned VO, kinetic captions, logo, music, CTA, and delivery QA.

This document distills what worked across Floors & Kitchens Today, the iDeal Floors kitchen remodel, and the iDeal Floors bathroom transformation. It includes the exact process, provider choices, approval gates, and references to reusable code snippets.

---

## 1. The final product we are trying to produce

A credible transformation ad, not a montage of pretty AI nonsense.

Expected structure:

```text
0–3s     approved BEFORE room
3–6s     worker enters / starts
6–17s    close process work, one credible action per beat
17–24s   finished AFTER room reveal
24–30s   after hold / CTA space
30–36s   branded end card
```

Core rules:

1. **Still-first, then motion.** Never animate an unapproved still.
2. **Close on the person/work for process shots.** Wide full-room plates are for before/after reveals only.
3. **The action must be physically believable for the specific remodel.** No fake installs, tile-on-tile, tile-into-recess, drawer-face-on-finished-drawer, or quartz-from-heaven.
4. **User playback judgment beats auxiliary vision QC.** If the user watched and rejected it, it is rejected.
5. **Every moving clip is unique, native speed, used once.** No loops, freezes, repeated tails, or slowed footage hiding a coverage gap.
6. **Milestones, not process essays.** Present approved still/video milestones with filenames and full paths.
7. **Preserve rejected work.** Quarantine it; do not silently overwrite or delete evidence.
8. **No API keys in project files.** Credentials live in `~/.hermes/.env` or the runtime environment.

---

## 2. Required inputs before generation

Collect these before spending provider credits:

- Client website and verified claims
- Service and market
- Offer/CTA language
- Official logo file
- Brand colors/fonts if known
- Reference video URL/file if the ad is “inspired by” something
- Target runtime and aspect ratio
- Approval owner
- Provider credentials and provider-specific billing/credit status
- Any existing voice/music assets that must be reused

Required environment variables, depending on provider path:

```bash
GEMINI_API_KEY=...
XAI_API_KEY=...
ELEVENLABS_API_KEY=...
FISH_API_KEY=...
```

Do **not** write real keys into project docs, scripts, manifests, or repos.

---

## 3. Durable project layout

Use a durable NAS project root for final artifacts, plus local work dirs as needed:

```text
/mnt/nas/public/video-gen/{project}/
├── assets/
│   ├── logo.png
│   └── logo-whiteplate.png
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

Local production helpers:

```text
/home/vikas/video-poc/
├── generate_vo.py
├── caption_engine.py
├── qa_captions.py
├── qa_video.py
├── project_pipeline.py
├── brands/{project}.yaml
└── docs/
    ├── AI_VIDEO_PRODUCTION_RUNBOOK.md
    └── AI_VIDEO_PRODUCTION_SNIPPETS.md
```

Reference code snippets for all major steps are in:

- `/home/vikas/video-poc/docs/AI_VIDEO_PRODUCTION_SNIPPETS.md`

---

## 4. Stage 0 — preflight before spending anything

Verify the exact runtime and credentials:

```bash
cd /home/vikas/video-poc
.venv/bin/python -c 'from google import genai; print("google-genai OK")'
ffmpeg -version | head -1
ffprobe -version | head -1
fc-list | grep -i 'Montserrat\|Anton' | head
```

Check keys are present without printing them:

```bash
python3 - <<'PY'
from pathlib import Path
env = Path.home().joinpath('.hermes/.env').read_text().splitlines()
for key in ['GEMINI_API_KEY', 'XAI_API_KEY', 'ELEVENLABS_API_KEY', 'FISH_API_KEY']:
    present = any(line.startswith(key + '=') and line.split('=', 1)[1].strip() for line in env)
    print(key, 'present' if present else 'missing')
PY
```

Provider-specific credit traps:

- **Fish Audio:** platform package credits and API credits are separate. A funded web package does **not** guarantee `api.fish.audio` works. Check API credit separately.
- **xAI/Grok:** an API key may exist while a specific model/endpoint is unavailable or a request shape is wrong.
- **ElevenLabs:** default public voices are recognizable everywhere; use a private clone or approved non-stock voice when brand distinctiveness matters.

---

## 5. Stage 1 — evidence-first reference and brand research

If the ad is inspired by an existing video:

1. Get the actual source MP4, not a thumbnail or transcript alone.
2. Watch it at normal speed.
3. Record observable grammar:
   - shot count
   - average shot length
   - camera distance from people/work
   - process vs reveal ratio
   - whether captions/VO/music carry it
   - final CTA/hold pattern

For the bathroom reference, the working grammar was:

- fast process beats
- close worker/action shots
- no wide empty-room people plates
- slow finished-room payoff
- music-led energy

For the reference line:

```text
This is what a home transformation looks like.
```

the project-specific adaptation became:

```text
This is what a bathroom transformation looks like.
```

and later a beat-aligned VO rather than one rambling narration.

---

## 6. Stage 2 — concept and approval packet

Before first generation, present a concise packet and wait for approval:

- premise
- audience
- offer
- runtime/aspect
- narrative-state sequence
- recurring setting/people continuity plan
- exact first keyframe prompt
- budget/provider estimate
- assumptions affecting room scale, people, logo, chronology

Do not spend credits until approval.

The agent should not dump a menu of options after approval. It should own execution, QC, and milestone presentation.

---

## 7. Stage 3 — brand YAML

Captions, end card, emphasis words, colors, CTA, and safe zones belong in YAML, not code.

Example:

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

Real example:

- `/home/vikas/video-poc/brands/idealfloors-bathroom-transformation.yaml`

Code reference:

- `/home/vikas/video-poc/caption_engine.py:30-80` — YAML loading
- `/home/vikas/video-poc/caption_engine.py:544-590` — CLI entry

---

## 8. Stage 4 — canonical setting and situational brief

For same-room transformations, create and approve a canonical setting before dependent shots.

### 8.1 Spatial program first

For renovation rooms, decide the spatial program before finishes:

- room shape and footprint
- camera position and viewing direction
- fixture zones
- open floor zone
- toilet/privacy zones
- where tile actually belongs
- where craft actions can credibly happen

For the bathroom:

- left: long double vanity
- center: corner tub under frosted windows
- right: standalone shower stall + toilet closet
- tile work belongs in the shower stall / tub deck / floor, not random painted walls

### 8.2 Generate before/after as locked plates

The successful bathroom path used Grok Imagine:

- floor plan → approved BEFORE
- BEFORE → approved AFTER
- then clean 9:16 conversion

Important xAI aspect-ratio lesson:

- **single-image edits inherit input aspect ratio**
- **multi-image edits can override aspect ratio**

So:

1. Generate the broad room first, often square.
2. Convert to clean 9:16 with an edit prompt that preserves camera distance and architecture.
3. Do not use blur bars unless intentionally declared.

### 8.3 Lock architecture

The AFTER must preserve:

- camera position and room width
- ceiling vent positions
- window positions
- vanity run
- tub/shower footprint
- door
- overall fixture geography

The bathroom failed repeatedly when the AFTER moved a ceiling vent. That is an automatic reject.

### 8.4 Situational brief before craft shots

Before generating process work, produce a superintendent-style brief:

- layout
- before finishes
- after finishes
- what changed vs stayed
- real construction sequence
- valid craft actions
- invalid craft actions

For this bathroom, valid examples included:

- shower-stall tile install on continuous backer/thinset
- floor hex tile setting
- vanity leveling
- faucet/quartz detail work

Invalid examples:

- tile into a fake wall recess
- tile on finished tile
- installing a drawer face that already exists
- tiling ordinary painted drywall outside the shower

---

## 9. Stage 5 — people identity and logo conditioning

### 9.1 People identity

Use **head-and-shoulders portrait references** for recurring people. Do not use full-body hero stills as the primary identity source.

Kitchen-proven order:

1. character portrait(s) first
2. setting plate last
3. wrapper prompt preserves identities and room architecture
4. people described relative to furniture, not frame-height percentages

Code reference:

- `/home/vikas/video-poc/project_pipeline.py:62-91` — `generate_image`
- `/home/vikas/video-poc/project_pipeline.py:150-173` — bounded keyframe attempts/QC

### 9.2 Logo on workwear

Use the **official logo file**, not a prose description.

Better conditioning:

1. create a large white **logo plate**
2. put logo plate first in multi-image order
3. use a strong prompt that says reproduce this exact mark as a small left-chest patch
4. self-QC the chest mark against the official logo before motion

Failure lesson:

- attaching the logo file alone was not enough; the model still invented a wrong shirt mark until the logo plate and conditioning were fixed.

### 9.3 Process-shot framing

Default renovation-Reel framing is:

- medium torso or tighter
- macro hands/tools
- low-angle work
- camera moves with the action

Not:

- wide empty bathroom with a small/giant person in the middle

---

## 10. Stage 6 — shot plan with narrative-state contract

Every shot needs a declared semantic state and scene-specific facts.

Minimum fields:

```json
{
  "id": "s03",
  "state": "before",
  "framing": "close_person",
  "subject": "worker at vanity toe-kick",
  "motion": "one broad pry",
  "required": ["same room", "ordinary adult scale", "credible pry contact"],
  "forbidden": ["giant person", "wrong room", "text", "fake action"],
  "source": "approved still-first keyframe",
  "qc_contract": "Fail if the action is implausible or the room changes."
}
```

Full example:

- `/tmp/openmontage-review/projects/idealfloors-bathroom-transformation/artifacts/high-energy-shot-blueprint.json`

Narrative-state rules:

- state ordering must make sense
- no later-state materials in earlier shots
- shared room anchors must persist
- a beautiful frame in the wrong state is still a failure

---

## 11. Stage 7 — still-first generation and self-QC

Generate stills before motion. Use provider-specific paths deliberately.

### 11.1 Grok Imagine for hard spatial room edits

Use xAI Imagine models, not chat/reasoning models.

Preferred for bathroom room plates and hard image edits:

- `grok-imagine-image-quality`

Relevant docs:

- xAI image generation: `POST https://api.x.ai/v1/images/generations`
- xAI image editing: `POST https://api.x.ai/v1/images/edits`

Important:

- multi-image edit uses `images: [{url, type}]`
- single-image edit uses `image: {url, type}`
- request base64 output when you need direct file writing

### 11.2 Gemini for people-into-room when following kitchen contract

Use the existing wrapper rather than improvising:

- portrait refs first
- setting plate last
- preserve identities and architecture
- furniture-relative people placement

### 11.3 Still QC gate

Self-QC each still for:

- room lock
- scale
- logo match
- action believability
- framing
- material match
- no fake construction geometry

Only show milestone candidates that pass your own review. Include filename and full path.

Do not batch-generate motion off rejected stills.

---

## 12. Stage 8 — motion generation

### 12.1 Preferred: xAI Grok image-to-video

For approved stills, use:

- `grok-imagine-video-1.5`

Request shape:

- `POST https://api.x.ai/v1/videos/generations`
- poll `GET https://api.x.ai/v1/videos/{request_id}`

Motion prompt describes only:

- one action
- camera movement
- continuity locks

Do not re-describe the entire image or ask the model to redesign the scene.

### 12.2 Alternate: Veo 3.1

Use Veo when it is the proven path for a particular project or Grok I2V underperforms on people motion.

Code reference:

- `/home/vikas/video-poc/project_pipeline.py:175-198` — Veo animation
- `/home/vikas/video-poc/project_pipeline.py:200-222` — temporal QC

### 12.3 Motion QC

Do not rely only on contact strips.

Check:

- actual MP4 at normal speed
- no internal scene resets
- no morphing people/tools/materials
- action remains physically believable
- no fake completion jumps
- logo does not mutate

Strips are navigation aids, not final approval.

---

## 13. Stage 9 — assemble the clean cut

Assembly that worked:

```text
before → walk/arrive → demo/pry → tile/install → vanity → detail → reveal → hold
```

Rules:

- chronological
- each action once
- longer native selects instead of repeats
- short crossfades (~0.10s)
- if more runtime is needed, use longer selects from unique clips or a declared after still hold for CTA space
- never use random repeats to fake coverage

The accepted bathroom cut:

```text
0–3.2s    before push
3.1–6.1s  walk
6.0–8.6s  pry
8.5–11.1s tile
11.0–13.6s vanity level
13.5–16.7s after detail glide
16.6–24.1s after reveal
24.1–30s  after hold
```

---

## 14. Stage 10 — voiceover and beat alignment

### 14.1 Script must match the cut

Do not generate one long narration and drop it over the montage.

Write one short line per beat, aligned to actual part durations.

Bathroom example:

```text
before   "Your bathroom shouldn't feel stuck in another decade."
walk     "This is the before."
pry      "The tear-out."
tile     "The craft."
vanity   "Every finish, designed together."
detail   "Then the crew finishes strong."
reveal   "This is the reveal."
cta_hold "Arlington, Garland, Duncanville — free estimate at idealfloors.com."
```

### 14.2 Fish Audio path

Preferred when you need distinctive voices beyond common internet presets.

Key facts:

- base URL: `https://api.fish.audio`
- endpoint: `POST /v1/tts`
- required model header
- test/dev model: `s2.1-pro-free`
- production model: `s2.1-pro`
- voice selection: `reference_id`

API credit is separate from platform credit. Confirm it explicitly.

### 14.3 ElevenLabs path

Use when:

- you need native word/character alignment immediately
- a private clone or approved voice is available
- the brand accepts that voice’s public recognizability

Code reference:

- `/home/vikas/video-poc/generate_vo.py:60-91` — timestamped TTS
- `/home/vikas/video-poc/generate_vo.py:122-159` — saves `vo-timestamped.mp3` and `vo-alignment.json`

### 14.4 Fish alignment workaround

Fish does not currently provide the same native alignment artifact in this workflow, so generate per-beat audio and synthesize alignment from:

- actual beat starts
- actual segment durations
- explicit gaps between lines

Then feed that alignment into the caption engine.

---

## 15. Stage 11 — captions and end card

Use ASS/libass, not static banners.

The caption engine:

- parses alignment
- segments phrases
- applies emphasis color/pop
- places captions in safe zones
- builds end card events
- renders with logo, ASS, VO, and music

Code references:

- `/home/vikas/video-poc/caption_engine.py:128-168` — alignment → words
- `/home/vikas/video-poc/caption_engine.py:187-259` — phrase segmentation
- `/home/vikas/video-poc/caption_engine.py:274-361` — emphasis/animation tags
- `/home/vikas/video-poc/caption_engine.py:364-393` — narration events
- `/home/vikas/video-poc/caption_engine.py:405-458` — end card events
- `/home/vikas/video-poc/caption_engine.py:463-539` — ASS assembly and render
- `/home/vikas/video-poc/caption_engine.py:544-590` — CLI

Important caption lessons:

- include real time gaps between beat lines or phrases will merge incorrectly
- brand stays in one phrase
- captions are creative kinetic typography, not subtitles
- lower-middle safe zone
- end card starts at VO end, not arbitrary video tail

---

## 16. Stage 12 — final render

The final render combines:

- video-only timeline
- persistent logo
- ASS captions
- VO
- music
- end-card band

Key render rules:

- final duration = VO end + card duration
- avoid `-shortest` when it can hide the end card
- use `tpad=stop_mode=clone` only for the declared post-VO card extension, not to fake moving footage
- normalize audio to roughly paid-social loudness (~-14 LUFS target)

Reusable command shape is in:

- `/home/vikas/video-poc/docs/AI_VIDEO_PRODUCTION_SNIPPETS.md`

---

## 17. Stage 13 — QA and delivery

### Structural QA

Use:

```bash
cd /home/vikas/video-poc
.venv/bin/python qa_captions.py /mnt/nas/public/video-gen/{project}/captions.ass \
  --brand "iDeal Floors" \
  --vo-end {vo_end} \
  --video-duration {final_duration} \
  --min-display 0.7 \
  --max-width 680

.venv/bin/python qa_video.py /mnt/nas/public/video-gen/{project}/output.mp4 \
  --vo-end {vo_end} \
  --duration {final_duration}
```

### Manual QA

Before delivery, a human or the owning agent must watch the actual final MP4 and verify:

- story order makes sense
- process actions are physically believable
- logo and captions are readable
- music and VO are audible
- end card appears after the reveal
- no stutter, frozen tails, loops, or repeated clips

### Delivery format

Always deliver with filenames and full paths, not only attachments.

---

## 18. Provider cheat sheet

### xAI / Grok Imagine

Use for:

- hard spatial room edits
- canonical before/after room plates
- close process stills
- image-to-video from approved stills

Models:

- `grok-imagine-image-quality` for best image edits
- `grok-imagine-video-1.5` for image-to-video
- `grok-imagine-video` for broader/reference-to-video needs

Traps:

- wrong endpoint or request shape can look like a model failure
- single-image edits inherit source aspect ratio
- OpenMontage wrappers may lag the docs; direct API calls are safer when debugging

### Gemini image / Veo

Use for:

- kitchen-proven people-into-room stills
- multi-reference wrapper when following `project_pipeline.py`
- Veo 3.1 image-to-video when that path is already proven for the project

Models used in current code:

- `gemini-3.1-flash-image`
- `veo-3.1-fast-generate-preview`

### Fish Audio

Use for:

- distinctive VO voices
- custom cloned voices
- avoiding overused default internet voices

Models:

- `s2.1-pro-free` for test/dev
- `s2.1-pro` for production

Traps:

- API credit is separate from platform package credit
- `reference_id` is required for a specific voice

### ElevenLabs

Use for:

- timestamped VO + alignment
- familiar stock voices only if acceptable
- private clone workflows

Traps:

- default public voices sound like every other internet ad
- script voice names must resolve to actual voice IDs

---

## 19. Failure playbook

| Symptom | Likely cause | Correct response |
|---|---|---|
| Women choosing finishes inside an already remodeled kitchen | QC optimized for finished palette, not narrative state | add narrative-state contract; reject wrong-state frame |
| Worker becomes giant/dwarf | full-body paste, wide room plate, wrong multi-image order | use portrait refs + setting plate last + furniture-relative placement |
| Wrong bathroom appears | setting lock ignored or wrong reference image | quarantine; regenerate from canonical plate only |
| Ceiling vent moves between before/after | AFTER not architecture-locked | regenerate AFTER from BEFORE with explicit fixture lock |
| Logo on shirt is wrong | prose-only logo or weak conditioning | official logo plate first + exact chest-patch prompt + logo QC |
| Quartz drops from heaven | fake install action | change to grounded seat/level/press action |
| Tile placed on finished tile | action not tied to remodel state | regenerate mid-install open-cell action |
| Tile placed into wall recess | model invented fake construction geometry | require continuous flat substrate and shower-stall location |
| VO feels like rambling TTS | script not mapped to cuts | write one line per beat and align per actual part durations |
| Captions merge unrelated beats | alignment lacks real gaps between lines | synthesize gaps between line windows before segmentation |
| Fish TTS returns 402 despite package balance | API credit empty | fund API credit separately |
| Music inaudible | bad mix or near-silent envelope | use loudnorm and verify with `volumedetect` |

---

## 20. Agent operating instructions

A future agent running this process must:

1. Load the relevant skill before production.
2. Verify current code/docs, not assume memory.
3. Inspect actual MP4s before judging quality or provenance.
4. Use the approved canonical setting, portraits, and logo plate.
5. Self-QC before showing anything.
6. Present only milestones with filenames and full paths.
7. Stop before material deviations.
8. Never patch shared skills or shared production code without prior discussion and approval.
9. Never conclude “the model can’t” before checking model name, endpoint, request shape, credits, and provider docs.
10. Never hide insufficient footage with loops, slows, freezes, or repeats.
11. Never generate motion from an unapproved or failed still.
12. Never write API keys into project artifacts.

---

## 21. Reusable code references

Primary reusable code:

- `/home/vikas/video-poc/generate_vo.py`
- `/home/vikas/video-poc/caption_engine.py`
- `/home/vikas/video-poc/qa_captions.py`
- `/home/vikas/video-poc/qa_video.py`
- `/home/vikas/video-poc/project_pipeline.py`
- `/home/vikas/video-poc/brands/*.yaml`

OpenMontage reference implementations:

- `/tmp/openmontage-review/tools/graphics/grok_image.py`
- `/tmp/openmontage-review/tools/video/grok_video.py`
- `/tmp/openmontage-review/tools/video/veo_video.py`

Bathroom project artifacts:

- `/tmp/openmontage-review/projects/idealfloors-bathroom-transformation/artifacts/high-energy-shot-blueprint.json`
- `/mnt/nas/public/video-gen/idealfloors-bathroom-transformation/brand.yaml`
- `/mnt/nas/public/video-gen/idealfloors-bathroom-transformation/captions.ass`
- `/mnt/nas/public/video-gen/idealfloors-bathroom-transformation/output.mp4`

Copy/paste API and ffmpeg snippets:

- `/home/vikas/video-poc/docs/AI_VIDEO_PRODUCTION_SNIPPETS.md`

---

## 22. Minimal human checklist

Before final delivery, confirm:

- [ ] reference video actually watched
- [ ] concept and first prompt approved
- [ ] brand YAML created
- [ ] canonical BEFORE/AFTER approved
- [ ] room situational brief written
- [ ] people/logo references approved
- [ ] stills approved before motion
- [ ] each motion clip watched at normal speed
- [ ] clean chronological cut approved
- [ ] beat-aligned VO approved
- [ ] captions/end card approved
- [ ] structural QA passed
- [ ] final MP4 watched
- [ ] final delivered from durable path
