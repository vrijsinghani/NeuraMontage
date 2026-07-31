"""Kinetic brand captions and end card as an ASS file.

These are creative typography, not subtitles: short phrases in the lower-middle
safe zone, accent-coloured emphasis words, and a branded end card that starts
when the voiceover stops. The three rules encoded here come from production
failures — phrases merge across beats when alignment carries no real gap, the
brand gets split across two events, and the end card drifts to the video tail.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Optional

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    ToolResult,
    ToolStability,
    ToolTier,
)
from tools.subtitle._ass import (
    dialogue_line,
    events_block,
    hex_to_ass_colour,
    script_info,
    style_line,
    styles_block,
)
# Single source of truth for the band height: the compose finish stack draws
# it, this tool only needs to avoid placing text inside it.
from tools.video._finish_stack import ENDCARD_BAND_HEIGHT

DEFAULT_FRAME = {"width": 720, "height": 1280, "max_caption_width": 680, "safe_zone_y": [430, 830]}
DEFAULT_CAPTIONS = {
    "max_duration": 3.0,
    "max_words": 4,
    "min_gap": 0.12,
    "min_display": 0.7,
    "fontsize_narration": 48,
    "fontsize_cta": 34,
    "fontsize_location": 25,
    "fontsize_website": 25,
}
DEFAULT_FONTS = {"display": "Anton", "narration": "Montserrat ExtraBold", "body": "Montserrat"}
DEFAULT_COLORS = {"accent": "#72bf44", "text": "#ffffff", "background": "#151515"}


def _normalize(token: str) -> str:
    return token.strip().strip(".,!?;:\"'—-").lower()


class KineticCaptions(BaseTool):
    name = "kinetic_captions"
    version = "0.1.0"
    tier = ToolTier.CORE
    capability = "subtitle"
    provider = "openmontage"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC

    dependencies = []  # pure Python
    install_instructions = "No external dependencies required."
    agent_skills = ["ffmpeg"]

    capabilities = ["generate_ass", "kinetic_typography", "end_card"]
    best_for = [
        "beat-aligned kinetic captions for short-form ads",
        "branded end cards that start at voiceover end",
    ]
    not_good_for = ["long-form dialogue subtitles", "burned-in translation subtitles"]
    fallback_tools = ["subtitle_gen"]

    input_schema = {
        "type": "object",
        "required": ["alignment", "vo_end"],
        "properties": {
            "alignment": {
                "type": "object",
                "description": "Word-level alignment: {words: [{word, start, end}]}",
            },
            "beats": {
                "type": "array",
                "description": "Beat windows [{id, start, end}]; phrases never cross a boundary",
            },
            "brand": {"type": "string", "description": "Brand name kept inside a single event"},
            "vo_end": {"type": "number", "description": "Voiceover end in seconds; the end card starts here"},
            "emphasis_words": {"type": "array", "items": {"type": "string"}},
            "frame": {"type": "object", "description": "width/height/safe_zone_y geometry"},
            "captions": {"type": "object", "description": "max_words/max_duration/min_gap/min_display and font sizes"},
            "fonts": {"type": "object"},
            "colors": {"type": "object"},
            "endcard": {
                "type": "object",
                "description": "duration plus headline/website/locations copy",
            },
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(cpu_cores=1, ram_mb=128, vram_mb=0, disk_mb=10)
    idempotency_key_fields = ["alignment", "beats", "brand", "vo_end", "endcard"]
    side_effects = ["writes an .ass file to output_path"]
    user_visible_verification = [
        "Burn the ASS over the cut and watch that phrases match the beats",
        "Confirm the end card appears when the voiceover stops",
    ]

    # --- segmentation ------------------------------------------------------

    @staticmethod
    def _beat_for(word: dict, beats: list[dict]) -> Optional[str]:
        """Beat owning a word, matched half-open so touching cuts don't tie.

        Consecutive beats share an endpoint (a cut at 3.2s ends one and starts
        the next). A closed match hands that word to the earlier beat, which
        drags the next beat's opening word into the previous phrase.
        """
        last = len(beats) - 1
        for index, beat in enumerate(beats):
            start_ok = word["start"] >= beat["start"] - 1e-6
            within = word["start"] < beat["end"] - 1e-6
            if start_ok and (within or index == last and word["start"] <= beat["end"] + 1e-6):
                return beat["id"]
        return None

    @staticmethod
    def _brand_spans(words: list[dict], brand: str) -> dict[int, int]:
        """Map each word index inside a brand mention to that mention's id.

        Segmentation may not break inside a span, so `iDeal Floors` survives a
        max_words boundary intact.
        """
        tokens = [_normalize(t) for t in (brand or "").split() if _normalize(t)]
        spans: dict[int, int] = {}
        if len(tokens) < 2:
            return spans
        normalized = [_normalize(w["word"]) for w in words]
        span_id = 0
        i = 0
        while i <= len(normalized) - len(tokens):
            if normalized[i : i + len(tokens)] == tokens:
                for offset in range(len(tokens)):
                    spans[i + offset] = span_id
                span_id += 1
                i += len(tokens)
            else:
                i += 1
        return spans

    def _segment(self, words: list[dict], beats: list[dict], brand: str, cfg: dict) -> list[dict]:
        spans = self._brand_spans(words, brand)
        max_words = int(cfg["max_words"])
        max_duration = float(cfg["max_duration"])
        min_gap = float(cfg["min_gap"])

        phrases: list[dict] = []
        current: list[dict] = []
        current_beat: Optional[str] = None

        beat_ends = {b["id"]: b["end"] for b in beats}

        def flush() -> None:
            if current:
                phrases.append(
                    {
                        "words": list(current),
                        "beat": current_beat,
                        "beat_end": beat_ends.get(current_beat),
                    }
                )
                current.clear()

        for index, word in enumerate(words):
            beat = self._beat_for(word, beats) if beats else None
            in_span = index in spans
            continues_span = in_span and (index - 1) in spans and spans[index] == spans.get(index - 1)

            if current and not continues_span:
                gap = word["start"] - current[-1]["end"]
                too_long = len(current) >= max_words
                too_slow = (word["end"] - current[0]["start"]) > max_duration
                if beats and beat != current_beat:
                    flush()
                elif gap >= min_gap or too_long or too_slow:
                    flush()

            if not current:
                current_beat = beat
            current.append(word)

        flush()
        return phrases

    # --- rendering ---------------------------------------------------------

    @staticmethod
    def _phrase_text(phrase: dict, emphasis: set[str], accent: str) -> tuple[str, str]:
        plain: list[str] = []
        styled: list[str] = []
        for word in phrase["words"]:
            token = word["word"].strip()
            plain.append(token)
            if _normalize(token) in emphasis:
                styled.append(f"{{\\c{accent}\\fscx112\\fscy112}}{token}{{\\r}}")
            else:
                styled.append(token)
        return " ".join(plain), " ".join(styled)

    def _narration_events(self, phrases, cfg, frame, emphasis, accent, vo_end) -> list[dict]:
        safe_top, safe_bottom = frame["safe_zone_y"]
        centre_x = frame["width"] // 2
        centre_y = int((safe_top + safe_bottom) / 2)
        min_display = float(cfg["min_display"])

        events = []
        for phrase in phrases:
            start = phrase["words"][0]["start"]
            end = max(phrase["words"][-1]["end"], start + min_display)
            # A caption must not survive its own cut, so the beat boundary
            # outranks the minimum display time.
            for limit in (phrase.get("beat_end"), vo_end):
                if limit is not None:
                    end = min(end, limit)
            plain, styled = self._phrase_text(phrase, emphasis, accent)
            events.append(
                {
                    "kind": "narration",
                    "beat": phrase["beat"],
                    "text": plain,
                    "start": start,
                    "end": end,
                    "y": centre_y,
                    "style": "Narration",
                    "ass_text": f"{{\\pos({centre_x},{centre_y})\\fad(120,120)}}{styled}",
                }
            )
        return events

    def _endcard_events(self, endcard, frame, vo_end, accent) -> list[dict]:
        duration = float(endcard.get("duration", 6.0))
        end = vo_end + duration
        centre_x = frame["width"] // 2
        band_top = frame["height"] - ENDCARD_BAND_HEIGHT

        lines: list[tuple[str, str]] = []
        if endcard.get("headline"):
            lines.append(("CTA", endcard["headline"]))
        for location in endcard.get("locations", []) or []:
            parts = [location.get(k) for k in ("city", "address", "phone") if location.get(k)]
            if parts:
                lines.append(("Location", "   ".join(parts)))
        if endcard.get("website"):
            lines.append(("Website", endcard["website"]))

        events = []
        offset = 70
        for style, text in lines:
            y = band_top + offset
            colour = f"{{\\c{accent}}}" if style == "Website" else ""
            events.append(
                {
                    "kind": "endcard",
                    "beat": None,
                    "text": text,
                    "start": vo_end,
                    "end": end,
                    "y": y,
                    "style": style,
                    "ass_text": f"{{\\pos({centre_x},{y})\\fad(200,0)}}{colour}{text}",
                }
            )
            offset += 78
        return events

    def _render(self, events, frame, fonts, colors, cfg) -> str:
        text_colour = hex_to_ass_colour(colors["text"])
        accent_colour = hex_to_ass_colour(colors["accent"])
        styles = [
            style_line("Narration", fonts["narration"], cfg["fontsize_narration"], text_colour),
            style_line("CTA", fonts["display"], cfg["fontsize_cta"], text_colour),
            style_line("Location", fonts["body"], cfg["fontsize_location"], text_colour),
            style_line("Website", fonts["body"], cfg["fontsize_website"], accent_colour),
        ]
        dialogue = [
            dialogue_line(e["start"], e["end"], e["style"], e["ass_text"]) for e in events
        ]
        lines = [
            *script_info(frame["width"], frame["height"]),
            *styles_block(styles),
            *events_block(dialogue),
        ]
        return "\n".join(lines)

    # --- entry point -------------------------------------------------------

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        start_time = time.time()

        vo_end = inputs.get("vo_end")
        if vo_end is None:
            return ToolResult(success=False, error="vo_end is required to place the end card")

        alignment = inputs.get("alignment") or {}
        words = alignment.get("words") if isinstance(alignment, dict) else alignment
        words = [w for w in (words or []) if str(w.get("word", "")).strip()]
        if not words:
            return ToolResult(success=False, error="alignment contains no words")

        frame = {**DEFAULT_FRAME, **(inputs.get("frame") or {})}
        cfg = {**DEFAULT_CAPTIONS, **(inputs.get("captions") or {})}
        fonts = {**DEFAULT_FONTS, **(inputs.get("fonts") or {})}
        colors = {**DEFAULT_COLORS, **(inputs.get("colors") or {})}
        endcard = inputs.get("endcard") or {}
        emphasis = {_normalize(w) for w in (inputs.get("emphasis_words") or [])}
        accent = hex_to_ass_colour(colors["accent"])

        phrases = self._segment(words, inputs.get("beats") or [], inputs.get("brand", ""), cfg)
        events = self._narration_events(phrases, cfg, frame, emphasis, accent, float(vo_end))
        events += self._endcard_events(endcard, frame, float(vo_end), accent)

        output_path = Path(inputs.get("output_path") or "captions.ass")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self._render(events, frame, fonts, colors, cfg), encoding="utf-8")

        return ToolResult(
            success=True,
            data={
                "events": events,
                "event_count": len(events),
                "final_duration": float(vo_end) + float(endcard.get("duration", 6.0)),
                "vo_end": float(vo_end),
                "output": str(output_path),
            },
            artifacts=[str(output_path)],
            duration_seconds=round(time.time() - start_time, 3),
        )
