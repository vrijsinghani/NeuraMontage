# Executive Producer - Transformation Ad Pipeline

## What This Pipeline Is For

Short-form before/after transformation ads. The operator is selling a service by
showing a space change state on camera. The deliverable is one vertical cut the
operator would send to a paying client without apologising for it.

## The Shape Of The Job

Ten stages: `research → proposal → idea → script → scene_plan → stills → motion →
edit → compose → publish`.

`assets` is deliberately split into `stills` and `motion`. That split exists for
one reason: motion costs real money per clip, and a still that is wrong stays
wrong once it moves. The operator approves every still before any motion request
is issued. Do not try to "save a round trip" by generating a clip from a still
you have not shown.

## Gates You Own

Four stages carry `human_approval_default: true`:

| Gate | What the operator is deciding |
|------|-------------------------------|
| `proposal` | Which concept, and which render runtime |
| `stills` | Which plates are allowed to cost motion credits |
| `motion` | Which clips are allowed into the cut |
| `compose` | Whether the final MP4 ships |

At each one: checkpoint `status="awaiting_human"`, present the artifact, and
**end your turn**. An earlier "looks good" never carries forward to the next
gate. Read `skills/meta/checkpoint-protocol.md` if that protocol is not already
loaded.

## Budget And Escalation

Default budget is small and the spend is concentrated in `motion`. Track it:

- stills are cheap, so iterate there rather than in motion,
- every motion clip is a unique action — no repeats, no freezes, no loops,
- if a provider underperforms, escalate as a recorded decision, not a silent retry.

## Where The Craft Lives

The stage names and artifact names in this pipeline are genre-neutral on
purpose: the same spine runs a different short-form ad genre by swapping these
director skills. Home-services specifics (room state, trade actions, crew
believability) belong in this skill directory and in the playbook, never in the
manifest.

## Failure Modes To Watch

- Motion generated from a still the operator never saw. Hard stop.
- A rejected asset deleted or overwritten instead of quarantined. Evidence loss.
- Runtime chosen by default instead of by conversation. See `proposal-director.md`.
- A beautiful frame in the wrong narrative state treated as a pass. It is a reject.
