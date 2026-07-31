"""Grok tools must reach the runbook's preferred models (U4, U5).

The runbook's proven transformation-ad path is `grok-imagine-image-quality`
for hard spatial room edits and `grok-imagine-video-1.5` for image-to-video.
Both enums were closed to a single older id, so the pipeline could not select
them at all — and the code-level fallbacks were separate string literals that
could drift from the schema, which is the exact failure
`test_provider_model_defaults.py` was written for.
"""

from __future__ import annotations

import pytest

import tools.graphics.grok_image as grok_image_mod
import tools.video.grok_video as grok_video_mod
from tools.graphics.grok_image import GrokImage
from tools.video.grok_video import GrokVideo

IMAGE_QUALITY = "grok-imagine-image-quality"
IMAGE_LEGACY = "grok-imagine-image"
VIDEO_15 = "grok-imagine-video-1.5"
VIDEO_LEGACY = "grok-imagine-video"


def _model_schema(tool) -> dict:
    return tool.input_schema["properties"]["model"]


# --- U4: grok_image --------------------------------------------------------


def test_image_default_is_the_runbook_preferred_model():
    assert _model_schema(GrokImage())["default"] == IMAGE_QUALITY


def test_image_enum_keeps_the_legacy_id_as_an_account_tier_fallback():
    """Outstanding Questions flag that quality may not be enabled on every
    account, so the older id has to stay selectable."""
    assert set(_model_schema(GrokImage())["enum"]) == {IMAGE_QUALITY, IMAGE_LEGACY}


def test_image_code_fallback_matches_schema_default():
    assert grok_image_mod._DEFAULT_MODEL == _model_schema(GrokImage())["default"]


def test_image_payload_with_no_model_names_the_schema_default():
    _, payload = GrokImage()._build_payload({"prompt": "a room"})
    assert payload["model"] == IMAGE_QUALITY


def test_image_payload_honours_an_explicit_legacy_model():
    _, payload = GrokImage()._build_payload({"prompt": "a room", "model": IMAGE_LEGACY})
    assert payload["model"] == IMAGE_LEGACY


def test_image_estimate_cost_default_matches_schema_default():
    tool = GrokImage()
    assert tool.estimate_cost({}) == tool.estimate_cost({"model": IMAGE_QUALITY})


# --- U5: grok_video --------------------------------------------------------


def test_video_default_is_the_runbook_preferred_model():
    assert _model_schema(GrokVideo())["default"] == VIDEO_15


def test_video_enum_keeps_the_broader_reference_model():
    """The runbook still routes broader reference-to-video needs at
    `grok-imagine-video`, so it stays selectable."""
    assert set(_model_schema(GrokVideo())["enum"]) == {VIDEO_15, VIDEO_LEGACY}


def test_video_code_fallback_matches_schema_default():
    assert grok_video_mod._DEFAULT_MODEL == _model_schema(GrokVideo())["default"]


def test_image_to_video_with_no_model_names_the_schema_default():
    payload = GrokVideo()._build_payload(
        {
            "prompt": "one broad pry",
            "operation": "image_to_video",
            "image_url": "https://example.test/still.png",
        }
    )
    assert payload["model"] == VIDEO_15


def test_reference_to_video_still_works_with_the_legacy_model():
    payload = GrokVideo()._build_payload(
        {
            "prompt": "walk into the room",
            "operation": "reference_to_video",
            "model": VIDEO_LEGACY,
            "reference_image_urls": ["https://example.test/ref.png"],
        }
    )
    assert payload["model"] == VIDEO_LEGACY
    assert payload["reference_images"] == [{"url": "https://example.test/ref.png"}]


def test_video_estimates_default_matches_schema_default():
    tool = GrokVideo()
    assert tool.estimate_cost({}) == tool.estimate_cost({"model": VIDEO_15})
    assert tool.estimate_runtime({}) == tool.estimate_runtime({"model": VIDEO_15})


# --- both ------------------------------------------------------------------


@pytest.mark.parametrize("tool_cls", [GrokImage, GrokVideo])
def test_declared_default_is_inside_the_declared_enum(tool_cls):
    schema = _model_schema(tool_cls())
    assert schema["default"] in schema["enum"]
