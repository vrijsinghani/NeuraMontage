"""Shared reject-without-losing-it glue for asset approval (U3).

R9 says a rejected asset is quarantined, never deleted or overwritten. Without
one implementation every project reinvents the move, and the failure mode is
silent: a clobbered file looks identical to a successful replacement.
"""

from __future__ import annotations

import pytest

from lib.asset_approval import (
    AssetApprovalError,
    approve_asset,
    quarantine_asset,
    record_replacement,
)
from schemas.artifacts import validate_artifact


@pytest.fixture()
def project_dir(tmp_path):
    (tmp_path / "assets" / "images").mkdir(parents=True)
    (tmp_path / "assets" / "video").mkdir(parents=True)
    (tmp_path / "assets" / "images" / "still_01.png").write_bytes(b"first take")
    (tmp_path / "assets" / "images" / "still_02.png").write_bytes(b"second take")
    (tmp_path / "assets" / "video" / "clip_01.mp4").write_bytes(b"motion take")
    return tmp_path


@pytest.fixture()
def manifest():
    return {
        "version": "1.0",
        "assets": [
            {
                "id": "still_01",
                "type": "image",
                "path": "assets/images/still_01.png",
                "source_tool": "grok_image",
                "scene_id": "s01",
            },
            {
                "id": "still_02",
                "type": "image",
                "path": "assets/images/still_02.png",
                "source_tool": "grok_image",
                "scene_id": "s01",
            },
            {
                "id": "clip_01",
                "type": "video",
                "path": "assets/video/clip_01.mp4",
                "source_tool": "grok_video",
                "scene_id": "s01",
            },
        ],
    }


def _asset(manifest: dict, asset_id: str) -> dict:
    return next(a for a in manifest["assets"] if a["id"] == asset_id)


# --- quarantine ------------------------------------------------------------


def test_quarantine_moves_the_file_and_empties_the_original_path(project_dir, manifest):
    updated = quarantine_asset(manifest, "still_01", project_dir, "vent moved in AFTER")

    assert not (project_dir / "assets/images/still_01.png").exists()
    quarantined = project_dir / _asset(updated, "still_01")["approval"]["quarantine_path"]
    assert quarantined.exists()
    assert quarantined.read_bytes() == b"first take"


def test_quarantine_routes_by_asset_type(project_dir, manifest):
    stills = quarantine_asset(manifest, "still_01", project_dir, "reject")
    assert _asset(stills, "still_01")["approval"]["quarantine_path"].startswith(
        "quarantine/stills/"
    )

    motion = quarantine_asset(stills, "clip_01", project_dir, "reject")
    assert _asset(motion, "clip_01")["approval"]["quarantine_path"].startswith(
        "quarantine/motion/"
    )


def test_quarantine_records_state_and_reason(project_dir, manifest):
    updated = quarantine_asset(manifest, "still_01", project_dir, "scale is wrong")
    approval = _asset(updated, "still_01")["approval"]

    assert approval["state"] == "rejected"
    assert approval["review_notes"] == "scale is wrong"


def test_quarantine_twice_raises_rather_than_clobbering(project_dir, manifest):
    updated = quarantine_asset(manifest, "still_01", project_dir, "first reject")
    quarantined = project_dir / _asset(updated, "still_01")["approval"]["quarantine_path"]

    # A regenerated asset reusing the id must not silently overwrite the
    # evidence of why the first one was rejected.
    (project_dir / "assets/images/still_01.png").write_bytes(b"regenerated take")
    with pytest.raises(AssetApprovalError, match="already exists"):
        quarantine_asset(updated, "still_01", project_dir, "second reject")

    assert quarantined.read_bytes() == b"first take"
    assert (project_dir / "assets/images/still_01.png").exists()


def test_quarantine_of_unknown_asset_raises(project_dir, manifest):
    with pytest.raises(AssetApprovalError, match="nope"):
        quarantine_asset(manifest, "nope", project_dir, "reject")


def test_quarantine_of_missing_file_raises(project_dir, manifest):
    (project_dir / "assets/images/still_01.png").unlink()
    with pytest.raises(AssetApprovalError, match="not found"):
        quarantine_asset(manifest, "still_01", project_dir, "reject")


def test_quarantine_does_not_mutate_the_input_manifest(project_dir, manifest):
    quarantine_asset(manifest, "still_01", project_dir, "reject")
    assert "approval" not in _asset(manifest, "still_01")


def test_quarantine_leaves_other_assets_untouched(project_dir, manifest):
    updated = quarantine_asset(manifest, "still_01", project_dir, "reject")
    assert "approval" not in _asset(updated, "still_02")
    assert (project_dir / "assets/images/still_02.png").exists()


# --- approve ---------------------------------------------------------------


def test_approve_sets_state_actor_and_timestamp(manifest):
    updated = approve_asset(manifest, "still_01", "operator", "room lock holds")
    approval = _asset(updated, "still_01")["approval"]

    assert approval["state"] == "approved"
    assert approval["approved_by"] == "operator"
    assert approval["review_notes"] == "room lock holds"
    assert approval["approved_at"].endswith("Z")


def test_approve_notes_are_optional(manifest):
    approval = _asset(approve_asset(manifest, "still_01", "operator"), "still_01")["approval"]
    assert approval["state"] == "approved"
    assert "review_notes" not in approval


def test_approving_a_quarantined_asset_raises(project_dir, manifest):
    """Approving a rejected asset would point the motion stage at a file that
    no longer sits at `path`."""
    updated = quarantine_asset(manifest, "still_01", project_dir, "reject")
    with pytest.raises(AssetApprovalError, match="rejected"):
        approve_asset(updated, "still_01", "operator")


def test_approve_of_unknown_asset_raises(manifest):
    with pytest.raises(AssetApprovalError, match="nope"):
        approve_asset(manifest, "nope", "operator")


# --- supersede -------------------------------------------------------------


def test_record_replacement_links_the_new_asset_to_the_rejected_one(project_dir, manifest):
    updated = quarantine_asset(manifest, "still_01", project_dir, "reject")
    updated = record_replacement(updated, "still_02", "still_01")

    assert _asset(updated, "still_02")["approval"]["supersedes"] == "still_01"


def test_record_replacement_preserves_existing_approval_fields(manifest):
    updated = approve_asset(manifest, "still_02", "operator")
    updated = record_replacement(updated, "still_02", "still_01")
    approval = _asset(updated, "still_02")["approval"]

    assert approval["state"] == "approved"
    assert approval["supersedes"] == "still_01"


def test_record_replacement_with_unknown_superseded_id_raises(manifest):
    with pytest.raises(AssetApprovalError, match="ghost"):
        record_replacement(manifest, "still_02", "ghost")


def test_asset_cannot_supersede_itself(manifest):
    with pytest.raises(AssetApprovalError, match="itself"):
        record_replacement(manifest, "still_02", "still_02")


# --- schema round trip -----------------------------------------------------


def test_every_helper_output_validates_against_the_manifest_schema(project_dir, manifest):
    updated = quarantine_asset(manifest, "still_01", project_dir, "reject")
    updated = approve_asset(updated, "clip_01", "operator", "motion reads clean")
    updated = record_replacement(updated, "still_02", "still_01")

    validate_artifact("asset_manifest", updated)
