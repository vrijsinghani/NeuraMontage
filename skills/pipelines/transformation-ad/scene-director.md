# Scene Director - Transformation Ad Pipeline

## Goal

Turn beats into a shot list precise enough that each still can be generated
without further interpretation.

## Per-Shot Specification

Every scene entry carries:

- `scene_id` and the `beat_id` it serves,
- narrative state (which point on the transformation arc),
- camera: framing, height, lens feel, and any move,
- subject action — exactly one, stated as a verb,
- the room anchors visible in this shot,
- materials and finishes appropriate to *this* state,
- caption safe zone: where text will sit, and what must stay clear of it.

## Shot Framing (R5 — Binding Craft)

Close on the person or the work for process shots. Wide full-room plates are
for before/after reveals only.

When writing each shot's camera framing:

- **Process / install / detail beats** — medium or tight on the worker and the
  material being acted on. The room may appear as context, but the frame's job
  is the credible action, not a tour of the space.
- **Before and after reveals** — wide plates that show the full room. Do not
  use a wide establishing frame for a process beat "because it looks nicer."

This rule lives here and in `stills-director.md`. It also lives in
`docs/AI_VIDEO_PRODUCTION_RUNBOOK.md` §1. Violating it is the usual path to
physically unbelievable motion later.

## One Action Per Shot

A shot that contains two actions cannot be generated as motion from a single
still, and cannot be QC'd. Split it.

## State Progression Is Monotonic

Order the scenes chronologically along the transformation arc. Then read the
list backwards and check: does any earlier shot contain a material, fixture, or
finish that only exists later? If yes, fix the scene spec now. This is the
single most common failure in this genre and it is free to catch here.

## Anchor Continuity

Every shot inside the space lists the same persistent anchors. Where an anchor
is out of frame, say so explicitly rather than omitting it — an omission reads
downstream as "anchor not required" and the plate drifts.

## Caption Reservation

Reserve the caption zone in the shot spec, not at compose time. If the subject
action happens where the text will burn, the caption becomes unreadable and the
shot has to be regenerated. Cheaper to move the framing now.

## Still Count

The scene plan determines how many stills `stills` generates and therefore how
many motion clips `motion` can cost. State the count and reconcile it against
the approved budget from `proposal`. If the plan has grown, surface that before
generating anything.

## Output

`scene_plan`. This stage does not gate, but it is the last stage before spend.
