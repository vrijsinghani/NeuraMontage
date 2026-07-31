# Motion Director - Transformation Ad Pipeline

## Goal

Animate approved stills into unique clips, one per planned shot, and reject
anything that breaks the illusion.

## Precondition

Every input still carries `approval.state == "approved"` in the incoming
`asset_manifest`. If one does not, stop and send back to `stills`. Do not
"just try it" — that is the spend this gate exists to prevent.

## Provider Path

Default is `grok_video` image-to-video against the approved still.

### Motion Prompt Shape

The prompt describes three things and nothing else:

1. **One action** — the single verb from the scene spec.
2. **Camera movement** — the move, or explicitly "static".
3. **Continuity locks** — the anchors, materials, and branding that must not change.

Do not re-describe the image. Do not ask the model to redesign, improve, or
"enhance" the scene. The still was approved; the model's job is to move it.

### Veo Escalation Is A Decision, Not A Retry

If `grok_video` underperforms on people motion — morphing limbs, tool
substitution, faces that drift — escalate to `veo_video`. Escalation is
recorded, not silent:

```yaml
category: motion_provider_escalation
scene_id: s04
from: grok_video
to: veo_video
because: "two attempts produced limb morphing on the pry action"
```

Write it to `decision_log`. A silent provider swap hides the failure signal the
operator needs when deciding whether the shot should exist at all, and it hides
the cost delta.

## Motion QC

Contact strips are navigation aids, not approval. Watch the actual MP4 at normal
speed and check:

- no internal scene resets — the clip does not restart itself mid-shot,
- no morphing people, tools, or materials,
- the action stays physically believable end to end,
- no fake completion jumps — the space does not skip ahead a state,
- the logo does not mutate,
- room anchors hold for the whole clip.

## Every Clip Is Unique (R7)

One action, one clip. The cut does not repeat, freeze, loop, or slow a clip to
fill runtime. If the edit is short, the answer is a longer native select from a
unique clip, or a declared held still for CTA space — never a duplicate.

`tools/video/_finish_stack.py` enforces this at compose time and will reject a
cut containing repeated clips. Discovering it there costs a re-render; catching
it here costs nothing.

## Rejects Go To Quarantine

Same rule as `stills`: `quarantine_asset` for the reject, `record_replacement`
for the clip that supersedes it. The rejected MP4 is evidence.

---

## Gate Reminder (Binding)

This stage gates on human approval (`human_approval_default: true`). Checkpoint
`status="awaiting_human"` with every clip and its full path, present, and **END
YOUR TURN**. On approval, mark the assets approved and write `completed` with
`human_approved=True`. Approval at `stills` does not cover this gate.
