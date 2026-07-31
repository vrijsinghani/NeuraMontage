"""Approval and quarantine helpers for `asset_manifest` items.

A rejected asset is evidence: it explains why the replacement was generated and
what the reviewer was reacting to. Deleting it (or letting a regenerated asset
overwrite it at the same path) destroys that trail, so quarantine moves the file
aside and records the move on the manifest item itself.

All three helpers return a new manifest and never mutate their input, so a
caller can build up a review pass and only then write the checkpoint.
"""

from __future__ import annotations

import copy
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

QUARANTINE_DIRNAME = "quarantine"

# Asset type -> quarantine subdirectory. Types outside this map fall back to
# the generic bucket rather than failing a rejection.
_TYPE_TO_STAGE = {
    "image": "stills",
    "video": "motion",
    "audio": "audio",
}
_DEFAULT_STAGE = "assets"


class AssetApprovalError(RuntimeError):
    """Raised when an approval transition would lose or misrepresent an asset."""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _find(manifest: dict[str, Any], asset_id: str) -> dict[str, Any]:
    for asset in manifest.get("assets", []):
        if asset.get("id") == asset_id:
            return asset
    raise AssetApprovalError(f"Asset {asset_id!r} is not in the manifest")


def quarantine_stage_for(asset: dict[str, Any]) -> str:
    """Quarantine subdirectory for an asset, derived from its type."""
    return _TYPE_TO_STAGE.get(asset.get("type", ""), _DEFAULT_STAGE)


def quarantine_asset(
    manifest: dict[str, Any],
    asset_id: str,
    project_dir: Path | str,
    reason: str,
    *,
    stage: Optional[str] = None,
) -> dict[str, Any]:
    """Move a rejected asset out of the way and record why.

    Args:
        manifest: asset_manifest artifact.
        asset_id: id of the asset being rejected.
        project_dir: project root that `asset["path"]` is relative to.
        reason: reviewer note, stored as `approval.review_notes`.
        stage: quarantine subdirectory; derived from the asset type by default.

    Returns:
        An updated copy of the manifest.

    Raises:
        AssetApprovalError: if the asset or its file is missing, or the
            quarantine destination is already occupied.
    """
    project_dir = Path(project_dir)
    updated = copy.deepcopy(manifest)
    asset = _find(updated, asset_id)

    source = project_dir / asset["path"]
    if not source.exists():
        raise AssetApprovalError(f"Asset file not found: {source}")

    destination_rel = Path(QUARANTINE_DIRNAME) / (stage or quarantine_stage_for(asset)) / source.name
    destination = project_dir / destination_rel
    if destination.exists():
        raise AssetApprovalError(
            f"Quarantine destination already exists: {destination}. "
            "Rename the incoming asset instead of overwriting the earlier rejection."
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))

    approval = dict(asset.get("approval", {}))
    approval.update(
        {
            "state": "rejected",
            "review_notes": reason,
            "quarantine_path": destination_rel.as_posix(),
        }
    )
    asset["approval"] = approval
    return updated


def approve_asset(
    manifest: dict[str, Any],
    asset_id: str,
    approved_by: str,
    notes: Optional[str] = None,
) -> dict[str, Any]:
    """Mark an asset approved, recording who approved it and when.

    Raises:
        AssetApprovalError: if the asset is missing or already quarantined —
            its file no longer sits at `path`, so approving it would point a
            downstream stage at nothing.
    """
    updated = copy.deepcopy(manifest)
    asset = _find(updated, asset_id)

    approval = dict(asset.get("approval", {}))
    if approval.get("state") == "rejected":
        raise AssetApprovalError(
            f"Asset {asset_id!r} was rejected and quarantined; generate a "
            "replacement and record it with record_replacement() instead."
        )

    approval.update({"state": "approved", "approved_by": approved_by, "approved_at": _now()})
    if notes is not None:
        approval["review_notes"] = notes
    asset["approval"] = approval
    return updated


def record_replacement(
    manifest: dict[str, Any],
    new_asset_id: str,
    supersedes_id: str,
) -> dict[str, Any]:
    """Link a regenerated asset to the rejected one it replaces."""
    if new_asset_id == supersedes_id:
        raise AssetApprovalError(f"Asset {new_asset_id!r} cannot supersede itself")

    updated = copy.deepcopy(manifest)
    _find(updated, supersedes_id)
    asset = _find(updated, new_asset_id)

    approval = dict(asset.get("approval", {}))
    approval["supersedes"] = supersedes_id
    asset["approval"] = approval
    return updated
