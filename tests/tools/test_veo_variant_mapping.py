"""Veo's fast aliases must reach the fast model (U6).

The runbook's alternate motion path is `veo-3.1-fast-generate-preview` on the
Google GenAI backend. Google-backend resolution collapsed every `veo3*` alias
onto the non-fast preview, so asking for `veo3.1/fast` silently generated the
slower, ~2.7x more expensive model — and the quoted cost was wrong in the same
direction, which is a Decision-Communication failure, not just a perf miss.
"""

from __future__ import annotations

import pytest

from tools.video.veo_video import VeoVideo

FAST_PREVIEW = "veo-3.1-fast-generate-preview"
FAST_VERTEX = "veo-3.1-fast-generate-001"
STANDARD_PREVIEW = "veo-3.1-generate-preview"
STANDARD_VERTEX = "veo-3.1-generate-001"


@pytest.fixture()
def tool():
    return VeoVideo()


# --- model resolution ------------------------------------------------------


@pytest.mark.parametrize("alias", ["veo3.1/fast", "veo3/fast"])
def test_fast_aliases_resolve_to_the_fast_model(tool, alias):
    assert tool.resolve_google_model(alias) == FAST_PREVIEW


@pytest.mark.parametrize("alias", ["veo3.1", "veo3"])
def test_standard_aliases_still_resolve_to_the_non_fast_model(tool, alias):
    assert tool.resolve_google_model(alias) == STANDARD_PREVIEW


def test_vertex_gets_the_ga_model_ids(tool):
    assert tool.resolve_google_model("veo3.1/fast", is_vertex=True) == FAST_VERTEX
    assert tool.resolve_google_model("veo3.1", is_vertex=True) == STANDARD_VERTEX


@pytest.mark.parametrize("verbatim", [FAST_PREVIEW, STANDARD_PREVIEW, "veo-4-experimental"])
def test_explicit_model_ids_pass_through_unchanged(tool, verbatim):
    """`model_variant` is deliberately enum-free so the runbook's exact model
    id reaches the API without a schema change."""
    assert tool.resolve_google_model(verbatim) == verbatim
    assert tool.resolve_google_model(verbatim, is_vertex=True) == verbatim


def test_model_variant_stays_enum_free(tool):
    assert "enum" not in tool.input_schema["properties"]["model_variant"]


def test_schema_default_resolves_to_the_standard_model(tool):
    default = tool.input_schema["properties"]["model_variant"]["default"]
    assert tool.resolve_google_model(default) == STANDARD_PREVIEW


# --- cost / runtime --------------------------------------------------------


@pytest.mark.parametrize("variant", ["veo3.1/fast", FAST_PREVIEW])
def test_google_cost_uses_the_fast_tier_for_both_spellings(tool, variant):
    inputs = {"backend": "google", "duration": "8s", "model_variant": variant}
    standard = {"backend": "google", "duration": "8s", "model_variant": "veo3.1"}

    assert tool.estimate_cost(inputs) < tool.estimate_cost(standard)


@pytest.mark.parametrize("variant", ["veo3.1/fast", FAST_PREVIEW])
def test_google_cost_is_identical_for_both_fast_spellings(tool, variant):
    alias = tool.estimate_cost(
        {"backend": "google", "duration": "8s", "model_variant": "veo3.1/fast"}
    )
    assert (
        tool.estimate_cost({"backend": "google", "duration": "8s", "model_variant": variant})
        == alias
    )


def test_google_standard_cost_is_unchanged(tool):
    cost = tool.estimate_cost(
        {"backend": "google", "duration": "8s", "model_variant": "veo3.1"}
    )
    assert cost == pytest.approx(8 * 0.40)


@pytest.mark.parametrize("variant", ["veo3.1/fast", FAST_PREVIEW])
def test_google_runtime_is_faster_for_fast_variants(tool, variant):
    fast = tool.estimate_runtime(
        {"backend": "google", "duration": "8s", "model_variant": variant}
    )
    standard = tool.estimate_runtime(
        {"backend": "google", "duration": "8s", "model_variant": "veo3.1"}
    )
    assert fast < standard


def test_fal_cost_tiering_is_unchanged(tool):
    """U6 touches the Google branch only; fal keeps its own slugs and tiers."""
    fast = tool.estimate_cost(
        {"backend": "fal", "duration": "8s", "model_variant": "veo3.1/fast"}
    )
    standard = tool.estimate_cost(
        {"backend": "fal", "duration": "8s", "model_variant": "veo3.1"}
    )
    assert fast == pytest.approx(8 * 0.20)
    assert standard == pytest.approx(8 * 0.40)
