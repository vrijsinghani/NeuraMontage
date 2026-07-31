# Research Director - Transformation Ad Pipeline

## Goal

Ground the ad in evidence before anyone writes a line: what the reference
actually does, and what comparable transformation ads do that works.

## Reference Analysis (When A Reference Exists)

The operator usually arrives with a Reel they want to compete with. Analyse it;
do not absorb it.

| Tool | Use |
|------|-----|
| `video_downloader` | Fetch the reference locally |
| `video_analyzer` | Deep pass — structure, pacing, on-screen text behaviour |
| `transcript_fetcher` | VO wording and cadence |
| `scene_detect` | Cut rhythm and shot count |
| `frame_sampler` | Framing, state progression, caption placement |

Produce `video_analysis_brief` with, at minimum:

- shot count and average shot length,
- where the transformation payoff lands in the timeline,
- caption style: placement, emphasis pattern, how much text per beat,
- audio architecture: VO present or not, music energy, where it changes,
- the hook mechanic in the first ~2 seconds.

## Analyse Structure, Not Frames

Record *why* the reference works — "payoff at 60% runtime", "one action per
beat", "captions sit in the lower third clear of the subject". Do not record a
shot list to reproduce. Frame-level copying is rejected at proposal.

## Comparable Work

Summarise at least three comparable transformation ads or techniques. For each:
the mechanic used, why it holds attention, and whether it is reproducible with
generated stills and image-to-video motion.

## Feasibility Notes

Flag anything the reference does that this pipeline cannot do honestly:

- continuous handheld camera moves across a room,
- real crew doing a real action for more than a few seconds,
- text effects that require frame-accurate typography beyond burned captions.

Say so now. A feasibility problem discovered at `motion` costs credits; the same
problem discovered here costs a sentence.

## Output

`research_brief` and `video_analysis_brief`. This stage does not gate — it feeds
`proposal`, which does.
