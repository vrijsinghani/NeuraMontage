# Script Director - Transformation Ad Pipeline

## Goal

Write VO and on-screen copy that survives being watched with the sound off.

## Beat Structure

The script is a beat list, not prose. Each beat carries:

- `beat_id`,
- the action or state it covers,
- VO line (or explicit `null` for a silent beat),
- the caption phrase the viewer reads,
- approximate duration.

Beats map one-to-one onto planned shots. If a beat needs two shots, it is two
beats.

## Sound-Off First

Most of the audience never hears the VO. The caption line must carry the meaning
on its own. Write the caption first, then the VO that supports it — not the
reverse.

Caption phrases are short: a phrase the eye takes in at a glance, not a
sentence. The kinetic caption engine segments on word-level alignment and will
not rescue a caption that was written as a paragraph.

## Brand Integrity

Company names, product names, and the operator's brand appear **exactly as
written** in the brief. The caption engine will not split or re-case a brand
token, and neither do you. If a brand name is long enough to need its own beat,
give it one.

## VO Constraints

- Conversational, not announcer-voiced.
- One idea per line. The line ends when the beat ends.
- No line spans a beat boundary. The caption engine clamps events at beat edges,
  so a straddling line gets cut, not compressed.
- The CTA lives on the end card, after VO ends. Do not narrate over it.

## Hook

The first beat earns the rest. It states or shows the problem within roughly two
seconds. A hook that describes what the viewer is about to see, rather than
showing it, is a scroll.

## Output

`script`. This stage does not gate, but a weak script is cheapest to fix here —
every downstream stage inherits its beat count.
