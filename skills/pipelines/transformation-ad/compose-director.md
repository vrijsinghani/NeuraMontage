# Compose Director - Transformation Ad Pipeline

## Goal

Render the client-ready MP4: cut, captions, logo, VO, music, end card, and
broadcast-sane loudness — in one mux.

## Runtime Routing

Route by `edit_decisions.render_runtime`. Do not infer it and do not default.

| `render_runtime` | Action |
|------------------|--------|
| `ffmpeg` | The expected path. Use the finish stack described below. |
| `remotion` | Valid if the approved concept needed composed motion graphics. Render through the Remotion runtime; the ASS caption burn is replaced by Remotion's caption layer. |
| `hyperframes` | **Not available on this pipeline.** Caption-burn parity with the ASS kinetic engine is not established here, and captions are load-bearing for a sound-off ad. |

If `render_runtime == "hyperframes"`, stop. Do not substitute a runtime
silently. Re-open the planning conversation so the operator sees the real
constraint and locks a runtime with a `render_runtime_selection` decision that
records `hyperframes` as `rejected_because: "caption-burn parity deferred on
transformation-ad"`. Per AGENT_GUIDE.md → "Present Both Composition Runtimes
(HARD RULE)", the constraint is not an excuse to skip the conversation — the
operator still learns HyperFrames exists.

Pass `proposal_packet` / `brief` into `video_compose.execute()` so the in-tool
runtime-swap check runs end to end.

## The Finish Stack (FFmpeg Path)

Generate captions first with `kinetic_captions`, then hand `video_compose` a
`finish_stack` input. One pass, not a chain of renders:

- persistent logo overlay for the full duration,
- burned ASS captions from `kinetic_captions`,
- VO and music mixed, music ducked under narration,
- `tpad` to extend the last frame when the cut is shorter than the end card
  needs,
- loudness normalised to -14 LUFS.

Final duration is `vo_end + card_duration`. **Never pass `-shortest`** — it
truncates at the shortest input and drops the end card, which is where the CTA
lives.

## Caption Generation

`kinetic_captions` takes word-level alignment and the beat boundaries from
`edit_decisions`. Check its output before burning:

- brand tokens are intact and correctly cased,
- no caption straddles a beat boundary,
- the end-card text appears after `vo_end`,
- captions sit inside the safe zone reserved at `scene_plan`.

## Unique Clips

`video_compose` validates R7 before encoding and fails the render if any clip
repeats. If it fires, the fix is in `edit`, not here — do not work around it by
re-cutting to hide the duplicate.

## Verify Before Presenting

Watch the MP4 at normal speed. Whole thing. Then check:

- duration matches `vo_end + card_duration`,
- no black opening frame,
- captions readable against every background they cross,
- logo present throughout and not mutating,
- VO intelligible over the music bed,
- the end card holds long enough to read the CTA.

Automated checks confirm the file is valid. They do not confirm it is good.

---

## Gate Reminder (Binding)

This stage gates on human approval (`human_approval_default: true`). Checkpoint
`status="awaiting_human"` with the full output path, present, and **END YOUR
TURN**. The operator's playback judgment is the verdict — if they watched it and
rejected it, it is rejected regardless of what the automated checks said.
