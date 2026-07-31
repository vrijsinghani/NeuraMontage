# Proposal Director - Transformation Ad Pipeline

## Goal

Put 2-3 genuinely different concepts in front of the operator, and settle the
render runtime by conversation rather than by default.

## Concept Requirements

Produce **2-3 concepts that differ in mechanic**, not in adjectives. Two
concepts that both say "cinematic reveal at the end" with different wording are
one concept.

Each concept carries:

- the transformation arc (opening state → actions → payoff state),
- the hook mechanic in the first ~2 seconds,
- shot count and rough runtime,
- audio architecture: VO or no VO, music energy, where energy shifts,
- caption strategy,
- estimated still count and motion clip count, with cost,
- one honest limitation.

## Do Not Copy The Reference

If a `video_analysis_brief` exists, you may borrow *structure* — payoff timing,
beat density, caption placement conventions. You may not reproduce the
reference's shot list, its specific framings in order, or its VO wording. A
concept that is the reference with different nouns is rejected. State explicitly
in each concept what it takes from the reference and what it does differently.

## Runtime Selection (HARD RULE)

Read `skills/core/hyperframes.md` before recommending anything.

Present all three runtimes to the operator. Do not pick silently.

| Runtime | Fit for this pipeline |
|---------|----------------------|
| `ffmpeg` | **Recommended.** The finish is a mux: generated clips, burned ASS captions, persistent logo overlay, VO + music, loudness normalisation. No React composition is needed. |
| `remotion` | Viable, but adds a React render layer over content that is already video. Pick it only if the concept needs composed motion graphics beyond burned captions. |
| `hyperframes` | Available in the repo, deferred for this pipeline. Caption-burn parity with the ASS kinetic engine is not established here, and captions are load-bearing for a sound-off ad. |

Per AGENT_GUIDE.md → "Present Both Composition Runtimes (HARD RULE)": naming a
constraint is not a substitute for the conversation. The operator still sees
that `hyperframes` exists and why it is not the pick here.

Write the decision to `decision_log` as `render_runtime_selection`, recording
the selected runtime **and both rejected alternatives with reasons**. A
single-option `render_runtime_selection` is a CRITICAL review finding.

```yaml
category: render_runtime_selection
selected: ffmpeg
rejected:
  - option: remotion
    because: "no composed motion graphics required; adds a render layer over finished video"
  - option: hyperframes
    because: "caption-burn parity deferred on transformation-ad; captions are load-bearing"
```

Wait for approval before locking `render_runtime` on `edit_decisions`.

## Cost Honesty

State the motion spend plainly. Motion is the budget. Give the operator the clip
count and the per-clip cost for the selected concept, and say what happens to
the number if a clip is rejected at the `motion` gate.

---

## Gate Reminder (Binding)

This stage gates on human approval (`human_approval_default: true`). After your
own review passes: checkpoint with `status="awaiting_human"`, present the
concepts, and **END YOUR TURN**. Do not begin `idea` in the same response.
Approval is per-gate.
