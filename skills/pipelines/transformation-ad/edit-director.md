# Edit Director - Transformation Ad Pipeline

## Goal

Assemble approved clips into a cut that reads as one continuous transformation,
and hand `compose` a spec it can execute without interpretation.

## Assembly Order

Chronological along the transformation arc. The shape that works:

```text
before → arrive → demo → install → detail → reveal → hold
```

Each action appears exactly once. If the arc needs more runtime, take longer
native selects from the unique clips you already have, or declare a held
after-state still for CTA space. Never pad with repeats.

## Cut Rules

- Short crossfades (~0.10s). Long dissolves read as stock footage.
- Cut on the action, not after it settles.
- The payoff lands with runtime left to hold on it. A reveal that is immediately
  followed by the end card gives the viewer nothing to look at.
- Beat boundaries from the script drive the cut points. The caption engine
  clamps caption events to those boundaries, so a cut that ignores them produces
  captions that end mid-thought.

## Sub-Stages

Run the clean cut first, then the beat-aligned VO pass. Reviewing a cut with VO
already on it makes it impossible to tell whether a pacing problem is picture or
audio.

1. **Clean cut** — picture only, no VO, no captions. Judge the visual arc.
2. **VO align** — lay VO against the cut and confirm each line sits inside its
   beat. Adjust the cut to the VO, not the VO to the cut; the script was written
   sound-off-first and shortening a line to fit picture loses meaning.

## Carry The Runtime Forward

Set `render_runtime` on `edit_decisions` from the `render_runtime_selection`
decision recorded at `proposal`. Do not re-decide it here and do not leave it
unset — an unset runtime means `compose` falls back to legacy behaviour and
silently picks Remotion.

## Unique Clip Check

Before writing `edit_decisions`, verify no clip path appears twice in the cut
list. `tools/video/_finish_stack.py` rejects duplicates, but the failure message
is clearer when you find it here.

## Timing Handoff

`edit_decisions` records the numbers `compose` needs:

- per-cut in/out points and the resulting `base_duration`,
- `vo_end` — where narration finishes,
- `card_duration` — how long the end card holds after VO.

Final duration is `vo_end + card_duration`. `compose` never uses `-shortest`,
because it would drop the card.

## Output

`edit_decisions`. This stage does not gate.
