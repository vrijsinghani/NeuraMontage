"""The still-first gate is enforced by lib/checkpoint.py, not skill prose (U2).

`stills` and `motion` are gated stages that both produce `asset_manifest`.
Registering them in `CANONICAL_STAGE_ARTIFACTS` is what turns R4 ("no motion
against an unapproved still") into a write-time error instead of a convention
an agent can skip.

The fixture builds its own throwaway manifest rather than reading
`pipeline_defs/transformation-ad.yaml`, so this file proves the *substrate*
behaviour independently of any one pipeline's authoring choices.
"""

from __future__ import annotations

import yaml
import pytest

import lib.pipeline_loader as pipeline_loader
from lib.checkpoint import (
    CANONICAL_STAGE_ARTIFACTS,
    CheckpointValidationError,
    get_next_stage,
    get_pipeline_stages,
    write_checkpoint,
)

PIPELINE_NAME = "still-first-fixture"

_MANIFEST = {
    "name": PIPELINE_NAME,
    "version": "1.0",
    "stages": [
        # A non-canonical opening stage keeps this file focused on the
        # stills -> motion boundary instead of another stage's artifact shape.
        {"name": "plan"},
        {
            "name": "stills",
            "produces": ["asset_manifest"],
            "human_approval_default": True,
        },
        {
            "name": "motion",
            "produces": ["asset_manifest"],
            "human_approval_default": True,
        },
        {"name": "edit", "produces": ["edit_decisions"]},
    ],
}


def _manifest_of(assets: list[dict]) -> dict:
    return {"version": "1.0", "assets": assets}


def _still(asset_id: str, state: str = "approved") -> dict:
    return {
        "id": asset_id,
        "type": "image",
        "path": f"assets/images/{asset_id}.png",
        "source_tool": "grok_image",
        "scene_id": "s01",
        "approval": {"state": state},
    }


@pytest.fixture()
def fixture_pipeline(tmp_path, monkeypatch):
    """Install a throwaway manifest as the only pipeline the loader can see."""
    defs_dir = tmp_path / "pipeline_defs"
    defs_dir.mkdir()
    (defs_dir / f"{PIPELINE_NAME}.yaml").write_text(yaml.safe_dump(_MANIFEST))
    monkeypatch.setattr(pipeline_loader, "PIPELINE_DEFS_DIR", defs_dir)
    pipeline_loader._load_pipeline_cached.cache_clear()
    yield
    pipeline_loader._load_pipeline_cached.cache_clear()


@pytest.fixture()
def project(tmp_path):
    (tmp_path / "proj").mkdir()
    return tmp_path


def test_stills_and_motion_both_produce_asset_manifest():
    assert CANONICAL_STAGE_ARTIFACTS["stills"] == "asset_manifest"
    assert CANONICAL_STAGE_ARTIFACTS["motion"] == "asset_manifest"


def test_canonical_stage_map_keeps_the_legacy_assets_stage():
    """Other pipelines still checkpoint `assets`; U2 is additive."""
    assert CANONICAL_STAGE_ARTIFACTS["assets"] == "asset_manifest"


def test_stills_and_motion_stay_out_of_the_no_manifest_fallback():
    """ALL_KNOWN_STAGES is the fallback for checkpoints with no pipeline_type.
    Custom stages belong to their manifest, matching character-animation."""
    from lib.checkpoint import ALL_KNOWN_STAGES, STAGES

    assert "stills" not in ALL_KNOWN_STAGES
    assert "motion" not in ALL_KNOWN_STAGES
    assert "stills" not in STAGES
    assert "motion" not in STAGES


def test_fixture_manifest_declares_the_gated_stages(fixture_pipeline):
    assert get_pipeline_stages(PIPELINE_NAME) == ["plan", "stills", "motion", "edit"]


def test_completing_stills_without_approval_raises(fixture_pipeline, project):
    with pytest.raises(CheckpointValidationError, match="GATE VIOLATION"):
        write_checkpoint(
            project,
            "proj",
            "stills",
            "completed",
            {"asset_manifest": _manifest_of([_still("still_01")])},
            pipeline_type=PIPELINE_NAME,
        )


def test_completing_motion_without_approval_raises(fixture_pipeline, project):
    with pytest.raises(CheckpointValidationError, match="GATE VIOLATION"):
        write_checkpoint(
            project,
            "proj",
            "motion",
            "completed",
            {"asset_manifest": _manifest_of([_still("clip_01")])},
            pipeline_type=PIPELINE_NAME,
            human_approved=False,
        )


def test_awaiting_human_without_asset_manifest_raises(fixture_pipeline, project):
    with pytest.raises(CheckpointValidationError, match="asset_manifest"):
        write_checkpoint(
            project,
            "proj",
            "stills",
            "awaiting_human",
            {},
            pipeline_type=PIPELINE_NAME,
        )


def test_stills_completes_with_approval_and_manifest(fixture_pipeline, project):
    path = write_checkpoint(
        project,
        "proj",
        "stills",
        "completed",
        {"asset_manifest": _manifest_of([_still("still_01")])},
        pipeline_type=PIPELINE_NAME,
        human_approved=True,
    )
    assert path.exists()


def test_next_stage_holds_at_stills_until_it_completes(fixture_pipeline, project):
    write_checkpoint(project, "proj", "plan", "completed", {}, pipeline_type=PIPELINE_NAME)
    assert get_next_stage(project, "proj", PIPELINE_NAME) == "stills"

    # An awaiting_human stills checkpoint is not completion — motion must wait.
    write_checkpoint(
        project,
        "proj",
        "stills",
        "awaiting_human",
        {"asset_manifest": _manifest_of([_still("still_01", state="pending")])},
        pipeline_type=PIPELINE_NAME,
    )
    assert get_next_stage(project, "proj", PIPELINE_NAME) == "stills"

    write_checkpoint(
        project,
        "proj",
        "stills",
        "completed",
        {"asset_manifest": _manifest_of([_still("still_01")])},
        pipeline_type=PIPELINE_NAME,
        human_approved=True,
    )
    assert get_next_stage(project, "proj", PIPELINE_NAME) == "motion"
