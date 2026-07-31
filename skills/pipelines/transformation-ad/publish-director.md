# Publish Director - Transformation Ad Pipeline

## Goal

Package the approved cut so the operator can post it without opening another
tool, and leave a record of what was made.

## Export Package

- The approved MP4 at its full path, named for the client and the job.
- A thumbnail frame taken from the payoff state, not the opening state.
- Caption text as a separate file where the platform accepts uploaded captions —
  burned captions cover sound-off viewing, uploaded captions cover accessibility
  and search.

## Metadata

Per destination:

- hook line drawn from the script's first beat,
- description carrying the CTA from the end card,
- the operator's service area and business name exactly as written in the brief.

## Provenance

Record what produced the deliverable:

- pipeline, playbook, and `render_runtime`,
- the still and clip asset ids that made the final cut,
- the quarantine directory contents, so the rejects stay traceable to the
  assets that superseded them.

An ad the operator wants to iterate on six months from now is only cheap to
revisit if this record exists.

## Output

`publish_log`. This stage does not gate: the operator already approved the cut
at `compose`, and asking again for the packaging is gate fatigue. Present the
package and the export paths, then checkpoint `completed`.
