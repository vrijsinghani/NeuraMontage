"""Lock the transformation-ad pipeline's spine (U12).

The still-first gate is the pipeline's whole point: it is the only thing
standing between an unapproved plate and real motion spend. A later edit that
drops `human_approval_default` from `stills` would leave every other file
looking correct while the gate silently disappears, so the order, the gates,
and the tool surface are asserted here rather than trusted to review.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lib.checkpoint import (
    CheckpointValidationError,
    get_completed_stages,
    get_next_stage,
    write_checkpoint,
)
from lib.pipeline_loader import (
    get_stage_human_approval_default,
    get_stage_order,
    get_stage_skill,
    get_required_tools,
    load_pipeline_readonly,
)

PIPELINE = "transformation-ad"
ROOT = Path(__file__).resolve().parent.parent.parent
SKILLS_DIR = ROOT / "skills"

# KTD-1: assets is split into two gated stages so the gate lands on a stage
# boundary, which is the only place lib/checkpoint.py enforces approval.
EXPECTED_STAGES = [
    "research",
    "proposal",
    "idea",
    "script",
    "scene_plan",
    "stills",
    "motion",
    "edit",
    "compose",
    "publish",
]
GATED_STAGES = {"proposal", "stills", "motion", "compose"}


@pytest.fixture(scope="module")
def manifest():
    return load_pipeline_readonly(PIPELINE)


# --- shape -----------------------------------------------------------------


def test_the_manifest_loads_and_validates(manifest):
    assert manifest["name"] == PIPELINE
    assert manifest["stability"] == "beta"
    assert manifest["default_checkpoint_policy"] == "guided"


def test_stage_order_matches_the_planned_spine(manifest):
    assert get_stage_order(manifest) == EXPECTED_STAGES


def test_motion_comes_after_stills(manifest):
    order = get_stage_order(manifest)
    assert order.index("stills") < order.index("motion")


@pytest.mark.parametrize("stage", sorted(GATED_STAGES))
def test_the_operator_gates_are_declared(manifest, stage):
    assert get_stage_human_approval_default(manifest, stage) is True, (
        f"Stage {stage!r} lost its human_approval_default. Without it "
        f"lib/checkpoint.py will happily write it 'completed' unapproved."
    )


@pytest.mark.parametrize(
    "stage", [s for s in EXPECTED_STAGES if s not in GATED_STAGES]
)
def test_ungated_stages_stay_ungated(manifest, stage):
    """Gating everything is the same as gating nothing — the operator stops
    reading. Only the four spend/quality boundaries gate."""
    assert get_stage_human_approval_default(manifest, stage) is False


def test_both_asset_stages_produce_the_asset_manifest(manifest):
    for stage in manifest["stages"]:
        if stage["name"] in {"stills", "motion"}:
            assert "asset_manifest" in stage["produces"]


def test_motion_requires_the_approved_stills_manifest(manifest):
    motion = next(s for s in manifest["stages"] if s["name"] == "motion")
    assert "asset_manifest" in motion["required_artifacts_in"]


# --- reference input -------------------------------------------------------


def test_reference_video_is_a_first_class_input(manifest):
    reference = manifest["reference_input"]
    assert reference["supported"] is True
    assert reference["analysis_depth"] == "deep"
    assert "video_analyzer" in reference["analysis_tools"]


def test_research_produces_the_reference_grounding_artifact(manifest):
    research = next(s for s in manifest["stages"] if s["name"] == "research")
    assert "video_analysis_brief" in research["produces"]


# --- tools -----------------------------------------------------------------


def test_the_runbook_provider_tools_are_reachable(manifest):
    tools = get_required_tools(manifest)
    for expected in ("grok_image", "grok_video", "veo_video", "kinetic_captions", "video_compose"):
        assert expected in tools, f"{expected} is not available to any stage"


def test_stills_can_reach_the_image_provider_and_motion_cannot_skip_ahead(manifest):
    stills = next(s for s in manifest["stages"] if s["name"] == "stills")
    motion = next(s for s in manifest["stages"] if s["name"] == "motion")

    assert "grok_image" in stills["tools_available"]
    assert "grok_video" in motion["tools_available"]
    # The still stage has no video generator: motion spend cannot happen there,
    # before the gate.
    assert "grok_video" not in stills["tools_available"]
    assert "veo_video" not in stills["tools_available"]


def test_compose_can_reach_the_caption_engine_and_the_finish_mux(manifest):
    compose = next(s for s in manifest["stages"] if s["name"] == "compose")
    assert "kinetic_captions" in compose["tools_available"]
    assert "video_compose" in compose["tools_available"]


def test_every_tool_the_manifest_names_is_discoverable(manifest):
    """A manifest may only name tools that exist. A typo here surfaces as a
    mid-run failure after the operator has already approved two gates."""
    from tools.tool_registry import registry

    registry.ensure_discovered()
    unresolvable = sorted(t for t in get_required_tools(manifest) if registry.get(t) is None)
    assert not unresolvable, f"Manifest names tools the registry cannot resolve: {unresolvable}"


# --- skills ----------------------------------------------------------------


def test_every_stage_has_a_director_skill_that_exists(manifest):
    for stage_name in get_stage_order(manifest):
        skill = get_stage_skill(manifest, stage_name)
        assert skill, f"Stage {stage_name!r} has no skill reference"
        assert (SKILLS_DIR / f"{skill}.md").is_file(), f"Missing skill file for {skill}"


def test_declared_required_skills_all_exist(manifest):
    for skill in manifest["required_skills"]:
        assert (SKILLS_DIR / f"{skill}.md").is_file(), f"Missing required skill {skill}"


def test_the_stills_director_states_the_gate_in_checkpoint_protocol_terms(manifest):
    body = (SKILLS_DIR / f"{get_stage_skill(manifest, 'stills')}.md").read_text(encoding="utf-8")
    assert "awaiting_human" in body
    assert "human_approved=True" in body


def test_the_stills_director_forbids_motion_off_a_rejected_still(manifest):
    body = (SKILLS_DIR / f"{get_stage_skill(manifest, 'stills')}.md").read_text(encoding="utf-8")
    assert "quarantine" in body.lower()


def test_the_motion_director_records_the_veo_escalation_as_a_decision(manifest):
    """KTD-7: a silent provider swap hides the failure signal the operator
    needs, so escalation is a logged decision, not a retry."""
    body = (SKILLS_DIR / f"{get_stage_skill(manifest, 'motion')}.md").read_text(encoding="utf-8")
    assert "veo_video" in body
    assert "decision_log" in body


def test_the_spine_stays_genre_neutral(manifest):
    """KTD-10/R11: another short-form ad genre reuses this spine by swapping
    director skills, which only works if the manifest carries no craft vocabulary."""
    spine = " ".join(
        [stage["name"] for stage in manifest["stages"]]
        + [artifact for stage in manifest["stages"] for artifact in stage.get("produces", [])]
    ).lower()
    for word in ("bathroom", "kitchen", "flooring", "remodel", "renovation"):
        assert word not in spine


# --- the gate, end to end --------------------------------------------------


def _asset_manifest(asset_id: str, state: str) -> dict:
    return {
        "version": "1.0",
        "assets": [
            {
                "id": asset_id,
                "type": "image",
                "path": f"assets/images/{asset_id}.png",
                "source_tool": "grok_image",
                "scene_id": "s01",
                "approval": {"state": state},
            }
        ],
    }


@pytest.fixture()
def project(tmp_path):
    (tmp_path / "proj").mkdir()
    return tmp_path


def test_stills_cannot_complete_without_operator_approval(project):
    with pytest.raises(CheckpointValidationError, match="GATE VIOLATION"):
        write_checkpoint(
            project, "proj", "stills", "completed",
            {"asset_manifest": _asset_manifest("still_01", "approved")},
            pipeline_type=PIPELINE,
        )


def test_motion_cannot_complete_without_operator_approval(project):
    with pytest.raises(CheckpointValidationError, match="GATE VIOLATION"):
        write_checkpoint(
            project, "proj", "motion", "completed",
            {"asset_manifest": _asset_manifest("clip_01", "approved")},
            pipeline_type=PIPELINE,
        )


def test_stills_awaiting_review_does_not_count_as_done(project):
    """`awaiting_human` is the state the operator is looking at. It must not
    satisfy the stage, or motion becomes reachable while review is open."""
    write_checkpoint(
        project, "proj", "stills", "awaiting_human",
        {"asset_manifest": _asset_manifest("still_01", "pending")},
        pipeline_type=PIPELINE,
    )
    assert "stills" not in get_completed_stages(project, "proj", PIPELINE)
    assert get_next_stage(project, "proj", PIPELINE) != "motion"

    write_checkpoint(
        project, "proj", "stills", "completed",
        {"asset_manifest": _asset_manifest("still_01", "approved")},
        pipeline_type=PIPELINE,
        human_approved=True,
    )
    assert "stills" in get_completed_stages(project, "proj", PIPELINE)


def test_an_approved_stills_checkpoint_keeps_its_approval_evidence(project):
    from lib.checkpoint import read_checkpoint

    write_checkpoint(
        project, "proj", "stills", "completed",
        {"asset_manifest": _asset_manifest("still_01", "approved")},
        pipeline_type=PIPELINE,
        human_approved=True,
    )
    checkpoint = read_checkpoint(project, "proj", "stills")
    asset = checkpoint["artifacts"]["asset_manifest"]["assets"][0]

    assert asset["approval"]["state"] == "approved"
