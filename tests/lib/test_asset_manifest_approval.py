"""Approval provenance on asset_manifest items (U1).

The still-first gate (R4) and quarantine rule (R9) need machine-readable
evidence on the artifact itself, not only in skill prose. Asset items are
`additionalProperties: false`, so the block has to be declared in the schema
before any producer can write it.
"""

from __future__ import annotations

import copy

import pytest
from jsonschema import ValidationError

from schemas.artifacts import validate_artifact


def _manifest(**asset_overrides) -> dict:
    asset = {
        "id": "still_before_01",
        "type": "image",
        "path": "assets/images/still_before_01.png",
        "source_tool": "grok_image",
        "scene_id": "s01",
    }
    asset.update(asset_overrides)
    return {"version": "1.0", "assets": [asset]}


def test_manifest_without_approval_still_validates():
    validate_artifact("asset_manifest", _manifest())


def test_manifest_with_full_approval_block_validates():
    manifest = _manifest(
        approval={
            "state": "approved",
            "approved_by": "operator",
            "approved_at": "2026-07-31T12:00:00Z",
            "review_notes": "Room lock and scale both hold.",
            "quarantine_path": "quarantine/stills/still_before_00.png",
            "supersedes": "still_before_00",
        }
    )
    validate_artifact("asset_manifest", manifest)


@pytest.mark.parametrize("state", ["pending", "approved", "rejected"])
def test_every_declared_state_validates(state):
    validate_artifact("asset_manifest", _manifest(approval={"state": state}))


def test_unknown_key_inside_approval_is_rejected():
    manifest = _manifest(approval={"state": "approved", "approval_state": "yes"})
    with pytest.raises(ValidationError):
        validate_artifact("asset_manifest", manifest)


def test_unknown_state_value_is_rejected():
    manifest = _manifest(approval={"state": "probably_fine"})
    with pytest.raises(ValidationError):
        validate_artifact("asset_manifest", manifest)


def test_approval_is_optional_per_asset():
    """A stills manifest mid-review carries approved, rejected, and untouched
    assets side by side — the block must not become required by adding it."""
    manifest = _manifest()
    manifest["assets"].append(
        {
            "id": "still_before_02",
            "type": "image",
            "path": "assets/images/still_before_02.png",
            "source_tool": "grok_image",
            "scene_id": "s02",
            "approval": {"state": "rejected", "quarantine_path": "quarantine/stills/x.png"},
        }
    )
    validate_artifact("asset_manifest", manifest)


def test_required_fields_are_unchanged():
    """Adding `approval` must not widen or narrow the item's required set."""
    manifest = _manifest()
    for field in ("id", "type", "path", "source_tool", "scene_id"):
        broken = copy.deepcopy(manifest)
        del broken["assets"][0][field]
        with pytest.raises(ValidationError):
            validate_artifact("asset_manifest", broken)
