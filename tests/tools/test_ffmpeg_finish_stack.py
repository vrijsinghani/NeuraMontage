"""The client-ready finish mux (U10).

The ffmpeg render path stopped at concat/trim, so the last mile — logo,
burned captions, VO plus music, the post-VO end card, and paid-social loudness
— had no in-repo implementation. Two runbook traps are encoded as hard errors
rather than prose: `-shortest` silently truncates the end card, and padding
runtime by repeating, freezing, or slowing a clip (R7) fakes coverage.
"""

from __future__ import annotations

import json
import subprocess

import pytest

from tools.video._finish_stack import (
    FinishStackError,
    FinishStackSpec,
    build_finish_command,
    final_duration,
    validate_unique_clips,
)


@pytest.fixture(scope="module")
def media(tmp_path_factory):
    """A tiny real video, VO, music, logo, and ASS so commands can be run.

    Module-scoped: every test in this file only reads these files (writes go
    through the function-scoped `tmp_path`), so the 4 ffmpeg encodes run once
    per module instead of once per test.
    """
    media_dir = tmp_path_factory.mktemp("media")
    video = media_dir / "video-only.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
         "-i", "testsrc=size=720x1280:rate=24:duration=6", "-c:v", "libx264",
         "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(video)],
        check=True,
    )
    vo = media_dir / "vo.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
         "-i", "sine=frequency=220:duration=4", "-c:a", "libmp3lame", str(vo)],
        check=True,
    )
    music = media_dir / "music.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
         "-i", "sine=frequency=440:duration=8", "-c:a", "libmp3lame", str(music)],
        check=True,
    )
    logo = media_dir / "logo.png"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
         "-i", "color=c=white:s=200x60:d=1", "-frames:v", "1", str(logo)],
        check=True,
    )
    ass = media_dir / "captions.ass"
    ass.write_text(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 720\nPlayResY: 1280\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
        "Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, "
        "MarginV, Encoding\n"
        "Style: Narration,Sans,48,&H00FFFFFF&,&H00FFFFFF&,&H00000000&,&H64000000&,"
        "-1,0,0,0,100,100,0,0,1,3,1,5,20,20,20,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
        "Effect, Text\n"
        "Dialogue: 0,0:00:00.00,0:00:03.00,Narration,,0,0,0,,{\\pos(360,630)}Hello\n",
        encoding="utf-8",
    )
    return {"video": video, "vo": vo, "music": music, "logo": logo, "ass": ass}


def _spec(media, tmp_path, **overrides) -> FinishStackSpec:
    payload = {
        "video_path": str(media["video"]),
        "output_path": str(tmp_path / "output.mp4"),
        "vo_path": str(media["vo"]),
        "music_path": str(media["music"]),
        "logo_path": str(media["logo"]),
        "ass_path": str(media["ass"]),
        "vo_end": 4.0,
        "card_duration": 2.0,
        "base_duration": 6.0,
    }
    payload.update(overrides)
    return FinishStackSpec(**payload)


# --- duration contract -----------------------------------------------------


def test_final_duration_is_vo_end_plus_card_duration():
    assert final_duration(29.86, 6.0) == pytest.approx(35.86)


def test_command_sets_the_computed_final_duration(media, tmp_path):
    cmd = build_finish_command(_spec(media, tmp_path, vo_end=29.86, card_duration=6.0))
    assert "-t" in cmd
    assert cmd[cmd.index("-t") + 1] == "35.860"


def test_shortest_is_never_passed_when_an_end_card_is_present(media, tmp_path):
    """`-shortest` ends the mux at the shortest input, which is exactly the VO —
    silently cutting the card the client is paying for."""
    assert "-shortest" not in build_finish_command(_spec(media, tmp_path))


def test_tpad_extends_only_the_declared_card_gap(media, tmp_path):
    """Clone-padding is legitimate for the declared post-VO hold and nothing
    else, so the pad length must equal final duration minus the real footage."""
    cmd = build_finish_command(
        _spec(media, tmp_path, vo_end=4.0, card_duration=2.0, base_duration=5.0)
    )
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "tpad=stop_mode=clone:stop_duration=1.000" in graph


def test_no_tpad_when_the_cut_already_covers_the_card(media, tmp_path):
    cmd = build_finish_command(
        _spec(media, tmp_path, vo_end=4.0, card_duration=2.0, base_duration=9.0)
    )
    assert "tpad=stop_mode=clone" not in cmd[cmd.index("-filter_complex") + 1]


def test_a_card_duration_of_zero_is_rejected(media, tmp_path):
    with pytest.raises(FinishStackError, match="card_duration"):
        build_finish_command(_spec(media, tmp_path, card_duration=0.0))


def test_a_missing_vo_end_is_rejected(media, tmp_path):
    with pytest.raises(FinishStackError, match="vo_end"):
        build_finish_command(_spec(media, tmp_path, vo_end=0.0))


# --- filter graph ----------------------------------------------------------


def test_the_ass_filter_receives_the_caption_engine_output(media, tmp_path):
    cmd = build_finish_command(_spec(media, tmp_path))
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "ass=" in graph
    assert "captions.ass" in graph


def test_ass_paths_with_colons_are_escaped(media, tmp_path):
    odd = tmp_path / "a:b"
    odd.mkdir()
    target = odd / "captions.ass"
    target.write_text(media["ass"].read_text(), encoding="utf-8")

    cmd = build_finish_command(_spec(media, tmp_path, ass_path=str(target)))
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "a\\:b" in graph


def test_the_logo_is_overlaid_for_the_whole_runtime(media, tmp_path):
    cmd = build_finish_command(_spec(media, tmp_path))
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "overlay=" in graph


def test_the_end_card_band_is_drawn_only_after_vo_end(media, tmp_path):
    cmd = build_finish_command(_spec(media, tmp_path, vo_end=4.0, card_duration=2.0))
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "drawbox" in graph
    assert "between(t,4.000,6.000)" in graph


def test_music_is_ducked_under_the_voiceover(media, tmp_path):
    cmd = build_finish_command(_spec(media, tmp_path))
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "amix=inputs=2" in graph


def test_loudness_normalisation_targets_paid_social(media, tmp_path):
    cmd = build_finish_command(_spec(media, tmp_path))
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "loudnorm=I=-14" in graph


def test_music_is_optional(media, tmp_path):
    cmd = build_finish_command(_spec(media, tmp_path, music_path=None))
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "amix" not in graph
    assert "loudnorm=I=-14" in graph


def test_a_missing_input_file_is_rejected(media, tmp_path):
    with pytest.raises(FinishStackError, match="not found"):
        build_finish_command(_spec(media, tmp_path, vo_path=str(tmp_path / "ghost.mp3")))


# --- R7: no faked coverage -------------------------------------------------


def test_a_clip_used_twice_is_rejected(media, tmp_path):
    cuts = [
        {"asset_id": "clip_pry", "duration": 2.6},
        {"asset_id": "clip_tile", "duration": 2.5},
        {"asset_id": "clip_pry", "duration": 2.6},
    ]
    with pytest.raises(FinishStackError, match="clip_pry"):
        validate_unique_clips(cuts)


def test_the_rejection_names_the_rule_so_the_agent_can_act(media, tmp_path):
    with pytest.raises(FinishStackError, match="longer native selects"):
        validate_unique_clips([{"asset_id": "a"}, {"asset_id": "a"}])


def test_unique_clips_pass(media, tmp_path):
    validate_unique_clips([{"asset_id": "a"}, {"asset_id": "b"}, {"asset_id": "c"}])


@pytest.mark.parametrize(
    "cut",
    [
        {"asset_id": "a", "freeze": True},
        {"asset_id": "a", "loop": 2},
        {"asset_id": "a", "speed": 0.5},
    ],
)
def test_padding_a_clip_by_freezing_looping_or_slowing_is_rejected(cut):
    with pytest.raises(FinishStackError):
        validate_unique_clips([cut])


def test_speeding_a_clip_up_is_not_padding(media, tmp_path):
    validate_unique_clips([{"asset_id": "a", "speed": 1.5}])


def test_cuts_without_asset_ids_are_left_alone(media, tmp_path):
    """Some edit_decisions address clips by path only; unique-clip enforcement
    must not crash on them."""
    validate_unique_clips([{"source": "a.mp4"}, {"source": "b.mp4"}])


# --- end-to-end render -----------------------------------------------------


def _probe_duration(path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def test_the_command_actually_renders_to_the_declared_duration(media, tmp_path):
    cmd = build_finish_command(_spec(media, tmp_path, vo_end=4.0, card_duration=2.0))
    subprocess.run(cmd, check=True, capture_output=True)

    assert _probe_duration(tmp_path / "output.mp4") == pytest.approx(6.0, abs=0.2)


def test_the_finish_stack_consumes_the_caption_engine_output(media, tmp_path):
    """U9 -> U10 handoff: the ASS the caption engine writes is the ASS the mux
    burns, with no intermediate format."""
    from tools.subtitle.kinetic_captions import KineticCaptions

    captions = KineticCaptions().execute(
        {
            "alignment": {"words": [{"word": "Hello", "start": 0.0, "end": 0.8}]},
            "vo_end": 4.0,
            "endcard": {"duration": 2.0, "headline": "Free Estimate"},
            "output_path": str(tmp_path / "kinetic.ass"),
        }
    )
    cmd = build_finish_command(
        _spec(
            media,
            tmp_path,
            ass_path=captions.artifacts[0],
            vo_end=captions.data["vo_end"],
            card_duration=2.0,
        )
    )
    subprocess.run(cmd, check=True, capture_output=True)

    assert _probe_duration(tmp_path / "output.mp4") == pytest.approx(
        captions.data["final_duration"], abs=0.2
    )


def test_the_render_lands_near_the_target_loudness(media, tmp_path):
    cmd = build_finish_command(_spec(media, tmp_path, vo_end=4.0, card_duration=2.0))
    subprocess.run(cmd, check=True, capture_output=True)

    measured = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(tmp_path / "output.mp4"),
         "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    payload = measured.stderr[measured.stderr.rindex("{") : measured.stderr.rindex("}") + 1]
    input_i = float(json.loads(payload)["input_i"])

    assert input_i == pytest.approx(-14.0, abs=2.0)


# --- wiring into the compose tool ------------------------------------------


def test_video_compose_advertises_the_finish_stack():
    from tools.video.video_compose import VideoCompose

    assert "finish_stack" in VideoCompose().input_schema["properties"]


def test_the_ffmpeg_render_path_rejects_a_repeated_clip_before_rendering(media, tmp_path):
    """R7 has to fail fast — spending a full encode and then rejecting the
    result wastes the operator's time and the machine's."""
    from tools.video.video_compose import VideoCompose

    result = VideoCompose()._render_via_ffmpeg(
        inputs={},
        edit_decisions={"cuts": []},
        resolved_cuts=[
            {"asset_id": "clip_pry", "source": str(media["video"])},
            {"asset_id": "clip_pry", "source": str(media["video"])},
        ],
        output_path=tmp_path / "out.mp4",
        profile=None,
    )

    assert not result.success
    assert "clip_pry" in result.error
    assert not (tmp_path / "out.mp4").exists()


def test_the_ffmpeg_render_path_runs_the_finish_stack_when_asked(media, tmp_path, monkeypatch):
    from tools.video.video_compose import VideoCompose

    tool = VideoCompose()
    monkeypatch.setattr(
        tool, "_run_final_review", lambda *a, **k: {"status": "pass", "issues_found": []}
    )
    output = tmp_path / "final.mp4"

    result = tool._render_via_ffmpeg(
        inputs={
            "finish_stack": {
                "video_path": str(media["video"]),
                "vo_path": str(media["vo"]),
                "music_path": str(media["music"]),
                "logo_path": str(media["logo"]),
                "ass_path": str(media["ass"]),
                "vo_end": 4.0,
                "card_duration": 2.0,
                "base_duration": 6.0,
            }
        },
        edit_decisions={"cuts": []},
        resolved_cuts=[{"asset_id": "clip_a", "source": str(media["video"])}],
        output_path=output,
        profile=None,
    )

    assert result.success, result.error
    assert output.exists()
    assert _probe_duration(output) == pytest.approx(6.0, abs=0.2)
    assert result.data["final_duration"] == pytest.approx(6.0)
