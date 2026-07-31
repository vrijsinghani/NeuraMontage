# Stills Director - Transformation Ad Pipeline

## Goal

Produce one approved still per planned shot. Nothing leaves this stage until the
operator has seen it, because the next stage spends motion credits against
whatever you hand it.

## Generate Stills Before Motion

This stage has no video generator in `tools_available`. That is deliberate and
not an oversight to work around: motion cannot be issued before the gate.

Use `grok_image` for hard spatial room edits — the quality tier is the proven
path for plates where architecture must hold. Its `image_paths` input takes
multiple references, which is how people-into-room composites are built: order
the references portrait-first and the setting plate last, and place people
relative to furniture rather than to frame coordinates.

`image_selector` is the fallback when Grok cannot hold a particular composite.
Reaching for it is a judgment call worth stating in the milestone note, because
the provider change usually shows in the plate's look.

## Still QC Gate (Seven Points)

Self-QC every still before showing it. All seven must pass:

1. **Room lock** — same room as every other shot; anchors in the same places.
2. **Scale** — people, tools, and fixtures are sized correctly against each other.
3. **Logo match** — branded apparel matches the official logo plate, not an
   approximation of it.
4. **Action believability** — the body is doing the action, not posing near it.
5. **Framing** — matches the scene spec, and the caption safe zone is clear.
6. **Material match** — finishes belong to *this* narrative state.
7. **No fake construction geometry** — no invented structural elements, no walls
   that could not exist, no floating fixtures.

A beautiful frame that fails point 6 is a reject. Do not argue with the state
contract.

## What You Show

Only candidates that passed your own seven-point review. For each, give the
filename and the full path. If a shot needed four attempts to pass, show the one
that passed — the operator is reviewing the plate, not your iteration count.

## Rejects Go To Quarantine

When the operator rejects a still, or when your own QC fails one you already
recorded:

- move it with the quarantine helper (`lib/asset_approval.quarantine_asset`),
  which relocates the file under the project's `quarantine/` directory and
  records `approval.state = "rejected"` with `approval.quarantine_path`,
- record the replacement with `record_replacement` so the new asset's
  `approval.supersedes` names the asset it replaces.

Never delete a reject and never overwrite it in place. The quarantined file is
the evidence that a decision was made, and the operator may want to compare.

## Do Not Batch-Generate Motion Off Rejected Stills

Stated plainly because it is the expensive mistake: a rejected still that is
still sitting in the manifest with `approval.state != "approved"` must not reach
`motion`. Motion reads the approved manifest. Keep it clean.

---

## Gate Reminder (Binding)

This stage gates on human approval (`human_approval_default: true`).

1. Write the checkpoint with `status="awaiting_human"` and the `asset_manifest`
   holding every candidate with `approval.state = "pending"`.
2. Present the candidates with paths.
3. **END YOUR TURN.**
4. On operator approval, mark each approved asset through
   `lib/asset_approval.approve_asset`, then write the checkpoint
   `status="completed"` with `human_approved=True`.

`lib/checkpoint.py` rejects a `completed` write on this stage without
`human_approved=True`. That is the enforcement, not a convention.
