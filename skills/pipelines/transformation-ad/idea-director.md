# Idea Director - Transformation Ad Pipeline

## Goal

Turn the approved concept into a `brief` concrete enough that the script writes
itself and the still list is already implied.

## What The Brief Must Pin Down

- **Subject state pair.** What the space looks like at open, and at payoff.
  Be specific about materials, fixtures, and layout — these become continuity
  locks that every later stage checks against.
- **Action sequence.** The ordered list of on-camera actions between the two
  states. Each action appears exactly once.
- **Room anchors.** The elements that must persist across every shot: window
  position, door, ceiling geometry, wall runs. If an anchor moves between
  shots, the ad reads as two different rooms.
- **Crew presence.** Whether people appear, how many, and what they wear.
  Branded apparel means the logo becomes a QC item at every gate.
- **Runtime target and platform.** Vertical short-form unless the operator says
  otherwise.
- **Deliverable definition.** What "done" means, including whether a CTA end
  card is required.

## Carry The Runtime Forward

`render_runtime` was settled at `proposal`. Record it in the brief so `edit` and
`compose` inherit it rather than re-deciding. If the operator changes their mind
here, that is a new `render_runtime_selection` decision, not an edit to the old
one.

## Continuity Contract

Write the narrative-state rule into the brief explicitly:

> No later-state material may appear in an earlier shot. A well-composed frame
> showing the finished space during a demolition beat is a reject, not a
> near-miss.

This sentence is what `stills` and `motion` QC against. If it is not in the
brief, the QC has nothing to point at.

## Output

`brief` and any `decision_log` entries. This stage does not gate.
