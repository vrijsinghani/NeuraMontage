"""Kinetic brand typography as ASS events (U9).

R10 asks for the runbook's kinetic captions, which are creative typography, not
subtitles. The runbook records three failures this tool has to design against:
phrases merge when alignment carries no real gap between beat lines, the brand
gets split across two events, and the end card starts at the video tail instead
of at VO end.
"""

from __future__ import annotations

import subprocess

import pytest

from tools.subtitle.kinetic_captions import KineticCaptions

BRAND = "iDeal Floors"
ACCENT = "#72bf44"


def _words(spec: list[tuple[str, float, float]]) -> list[dict]:
    return [{"word": w, "start": s, "end": e} for w, s, e in spec]


def _inputs(tmp_path, **overrides) -> dict:
    payload = {
        "alignment": {
            "words": _words(
                [
                    ("This", 0.0, 0.2),
                    ("is", 0.2, 0.4),
                    ("the", 0.4, 0.6),
                    ("before.", 0.6, 1.0),
                ]
            )
        },
        "brand": BRAND,
        "vo_end": 2.0,
        "endcard": {"duration": 6.0, "headline": "Schedule Your Free In-Home Estimate"},
        "colors": {"accent": ACCENT, "text": "#ffffff", "background": "#151515"},
        "output_path": str(tmp_path / "captions.ass"),
    }
    payload.update(overrides)
    return payload


def _run(tmp_path, **overrides):
    result = KineticCaptions().execute(_inputs(tmp_path, **overrides))
    assert result.success, result.error
    return result


def _narration(result) -> list[dict]:
    return [e for e in result.data["events"] if e["kind"] == "narration"]


def _endcard(result) -> list[dict]:
    return [e for e in result.data["events"] if e["kind"] == "endcard"]


# --- brand integrity -------------------------------------------------------


def test_a_multi_word_brand_stays_in_one_event(tmp_path):
    """max_words is 4; the brand must not be split even when it straddles the
    boundary that segmentation would otherwise pick."""
    result = _run(
        tmp_path,
        alignment={
            "words": _words(
                [
                    ("Flooring", 0.0, 0.4),
                    ("done", 0.4, 0.7),
                    ("right", 0.7, 1.0),
                    ("by", 1.0, 1.2),
                    ("iDeal", 1.2, 1.6),
                    ("Floors", 1.6, 2.0),
                ]
            )
        },
        captions={"max_words": 4},
    )

    holding = [e for e in _narration(result) if "iDeal" in e["text"]]
    assert len(holding) == 1
    assert "Floors" in holding[0]["text"]


def test_brand_matching_ignores_case_and_trailing_punctuation(tmp_path):
    result = _run(
        tmp_path,
        alignment={
            "words": _words(
                [
                    ("Call", 0.0, 0.3),
                    ("ideal", 0.3, 0.7),
                    ("floors,", 0.7, 1.1),
                    ("today", 1.1, 1.5),
                ]
            )
        },
        captions={"max_words": 2},
    )

    holding = [e for e in _narration(result) if "ideal" in e["text"].lower()]
    assert len(holding) == 1
    assert "floors" in holding[0]["text"].lower()


# --- gaps between beats ----------------------------------------------------


def test_a_real_gap_between_beats_produces_two_events(tmp_path):
    result = _run(
        tmp_path,
        alignment={
            "words": _words(
                [("The", 0.0, 0.3), ("tear-out.", 0.3, 0.8), ("The", 2.4, 2.7), ("craft.", 2.7, 3.2)]
            )
        },
        vo_end=4.0,
    )

    events = _narration(result)
    assert len(events) == 2
    assert "tear-out" in events[0]["text"]
    assert "craft" in events[1]["text"]


def test_words_without_a_gap_stay_in_one_event(tmp_path):
    """The counterpart to the split above: contiguous speech must not
    fragment, or the captions stop reading as phrases."""
    result = _run(
        tmp_path,
        alignment={
            "words": _words([("The", 0.0, 0.3), ("tear-out.", 0.3, 0.8), ("The", 0.85, 1.1), ("craft.", 1.1, 1.6)])
        },
        captions={"max_words": 8, "min_gap": 0.5},
    )

    assert len(_narration(result)) == 1


def test_explicit_beat_boundaries_are_never_crossed(tmp_path):
    result = _run(
        tmp_path,
        alignment={
            "words": _words([("The", 0.0, 0.3), ("craft.", 0.3, 0.6), ("The", 0.62, 0.9), ("reveal.", 0.9, 1.3)])
        },
        beats=[{"id": "b1", "start": 0.0, "end": 0.61}, {"id": "b2", "start": 0.62, "end": 1.3}],
        captions={"max_words": 8, "min_gap": 5.0},
    )

    events = _narration(result)
    assert len(events) == 2
    assert events[0]["beat"] == "b1"
    assert events[1]["beat"] == "b2"


# --- end card --------------------------------------------------------------


def test_endcard_starts_at_vo_end_not_the_video_tail(tmp_path):
    result = _run(tmp_path, vo_end=29.86)
    card = _endcard(result)

    assert card
    assert min(e["start"] for e in card) == pytest.approx(29.86)


def test_endcard_runs_for_the_declared_duration(tmp_path):
    result = _run(tmp_path, vo_end=29.86, endcard={"duration": 6.0, "headline": "Free Estimate"})

    assert max(e["end"] for e in _endcard(result)) == pytest.approx(35.86)
    assert result.data["final_duration"] == pytest.approx(35.86)


def test_endcard_renders_every_supplied_copy_line(tmp_path):
    result = _run(
        tmp_path,
        endcard={
            "duration": 6.0,
            "headline": "Schedule Your Free In-Home Estimate",
            "website": "idealfloors.com",
            "locations": [{"city": "DFW Showrooms", "address": "Arlington | Garland", "phone": "972-4-FLOORS"}],
        },
    )
    rendered = " ".join(e["text"] for e in _endcard(result))

    assert "Schedule Your Free In-Home Estimate" in rendered
    assert "idealfloors.com" in rendered
    assert "Arlington | Garland" in rendered


def test_narration_never_overlaps_the_endcard(tmp_path):
    result = _run(tmp_path, vo_end=1.0)
    assert max(e["end"] for e in _narration(result)) <= 1.0 + 1e-6


# --- placement and emphasis ------------------------------------------------


def test_narration_sits_inside_the_declared_safe_zone(tmp_path):
    result = _run(tmp_path, frame={"width": 720, "height": 1280, "safe_zone_y": [430, 830]})

    for event in _narration(result):
        assert 430 <= event["y"] <= 830


def test_emphasis_words_get_the_accent_colour(tmp_path):
    result = _run(
        tmp_path,
        alignment={"words": _words([("The", 0.0, 0.3), ("reveal.", 0.3, 0.9)])},
        emphasis_words=["reveal"],
    )
    text = _narration(result)[0]["ass_text"]

    # 72bf44 -> ASS is &HBBGGRR&
    assert "&H0044BF72&" in text


def test_words_outside_the_emphasis_list_are_not_accented(tmp_path):
    result = _run(
        tmp_path,
        alignment={"words": _words([("The", 0.0, 0.3), ("reveal.", 0.3, 0.9)])},
        emphasis_words=[],
    )
    assert "&H0044BF72&" not in _narration(result)[0]["ass_text"]


def test_every_event_has_a_minimum_display_time(tmp_path):
    result = _run(
        tmp_path,
        alignment={"words": _words([("Go.", 0.0, 0.05)])},
        captions={"min_display": 0.7},
        vo_end=5.0,
    )
    event = _narration(result)[0]
    assert event["end"] - event["start"] >= 0.7


# --- file output -----------------------------------------------------------


def test_writes_an_ass_file_with_the_required_sections(tmp_path):
    result = _run(tmp_path)
    content = (tmp_path / "captions.ass").read_text(encoding="utf-8")

    assert "[Script Info]" in content
    assert "[V4+ Styles]" in content
    assert "[Events]" in content
    assert result.artifacts == [str(tmp_path / "captions.ass")]


def test_playres_matches_the_declared_frame(tmp_path):
    _run(tmp_path, frame={"width": 720, "height": 1280, "safe_zone_y": [430, 830]})
    content = (tmp_path / "captions.ass").read_text(encoding="utf-8")

    assert "PlayResX: 720" in content
    assert "PlayResY: 1280" in content


def test_emitted_ass_parses_with_ffprobe(tmp_path):
    _run(tmp_path)
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=codec_name",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(tmp_path / "captions.ass"),
        ],
        capture_output=True,
        text=True,
    )

    assert probe.returncode == 0, probe.stderr
    assert probe.stdout.strip() == "ass"


def test_missing_vo_end_is_rejected(tmp_path):
    result = KineticCaptions().execute(
        {"alignment": {"words": _words([("Hi", 0.0, 0.3)])}, "output_path": str(tmp_path / "c.ass")}
    )
    assert not result.success
    assert "vo_end" in result.error


def test_empty_alignment_is_rejected(tmp_path):
    result = KineticCaptions().execute(
        {"alignment": {"words": []}, "vo_end": 5.0, "output_path": str(tmp_path / "c.ass")}
    )
    assert not result.success


# --- the accepted bathroom cut ---------------------------------------------

BATHROOM_BEATS = [
    ("before", 0.0, 3.2, "Your bathroom shouldn't feel stuck in another decade."),
    ("walk", 3.2, 6.1, "This is the before."),
    ("pry", 6.1, 8.6, "The tear-out."),
    ("tile", 8.6, 11.1, "The craft."),
    ("vanity", 11.1, 13.6, "Every finish, designed together."),
    ("detail", 13.6, 16.7, "Then the crew finishes strong."),
    ("reveal", 16.7, 24.1, "This is the reveal."),
    ("cta_hold", 24.1, 29.86, "Free estimate at idealfloors.com."),
]


def _bathroom_alignment() -> dict:
    """One line per beat, spoken inside its own beat window with real gaps."""
    words = []
    for _, start, end, line in BATHROOM_BEATS:
        tokens = line.split()
        span = (end - start - 0.3) / len(tokens)
        for i, token in enumerate(tokens):
            words.append(
                {"word": token, "start": start + i * span, "end": start + (i + 1) * span}
            )
    return {"words": words}


def test_the_accepted_bathroom_cut_reproduces_its_beat_boundaries(tmp_path):
    result = _run(
        tmp_path,
        alignment=_bathroom_alignment(),
        beats=[{"id": bid, "start": s, "end": e} for bid, s, e, _ in BATHROOM_BEATS],
        vo_end=29.86,
        emphasis_words=["bathroom", "before", "tear-out", "craft", "reveal", "free", "estimate"],
    )
    events = _narration(result)

    # Every beat is spoken, and no event leaks across the cut it belongs to.
    assert {e["beat"] for e in events} == {bid for bid, _, _, _ in BATHROOM_BEATS}
    windows = {bid: (s, e) for bid, s, e, _ in BATHROOM_BEATS}
    for event in events:
        start, end = windows[event["beat"]]
        assert event["start"] >= start - 1e-6
        assert event["end"] <= end + 1e-6


def test_the_accepted_bathroom_cut_ends_the_card_at_35_86(tmp_path):
    result = _run(
        tmp_path,
        alignment=_bathroom_alignment(),
        beats=[{"id": bid, "start": s, "end": e} for bid, s, e, _ in BATHROOM_BEATS],
        vo_end=29.86,
        endcard={"duration": 6.0, "headline": "Schedule Your Free In-Home Estimate"},
    )
    assert result.data["final_duration"] == pytest.approx(35.86)
