"""ASS/libass formatting primitives.

Kept separate from the caption tool so the segmentation logic can be read
without wading through subtitle-format trivia.
"""

from __future__ import annotations

WHITE = "&H00FFFFFF&"


def hex_to_ass_colour(value: str) -> str:
    """Convert `#RRGGBB` to the `&HAABBGGRR&` byte order libass expects."""
    raw = (value or "").lstrip("#")
    if len(raw) != 6:
        return WHITE
    r, g, b = raw[0:2], raw[2:4], raw[4:6]
    return f"&H00{b}{g}{r}&".upper().replace("&H00", "&H00", 1)


def ass_timestamp(seconds: float) -> str:
    """Format seconds as ASS `H:MM:SS.cc`."""
    seconds = max(0.0, seconds)
    hours, rem = divmod(int(seconds), 3600)
    minutes, secs = divmod(rem, 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis == 100:  # rounding carried into the next second
        centis = 0
        secs += 1
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def script_info(width: int, height: int) -> list[str]:
    return [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "ScaledBorderAndShadow: yes",
        "WrapStyle: 0",
        "",
    ]


_STYLE_FORMAT = (
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
    "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
    "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding"
)


def style_line(name: str, font: str, size: int, colour: str) -> str:
    return (
        f"Style: {name},{font},{size},{colour},{colour},&H00000000&,&H64000000&,"
        "-1,0,0,0,100,100,0,0,1,3,1,5,20,20,20,1"
    )


def styles_block(styles: list[str]) -> list[str]:
    return ["[V4+ Styles]", _STYLE_FORMAT, *styles, ""]


def events_block(dialogue: list[str]) -> list[str]:
    return [
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        *dialogue,
        "",
    ]


def dialogue_line(start: float, end: float, style: str, text: str) -> str:
    return (
        f"Dialogue: 0,{ass_timestamp(start)},{ass_timestamp(end)},{style},,0,0,0,,{text}"
    )
