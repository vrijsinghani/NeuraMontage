"""The client-ready finish mux: logo, captions, VO + music, end card, loudness.

Split out of `video_compose.py` so the filter graph is testable without
constructing the whole tool, and so the compose module doesn't grow further.

Two rules are enforced here rather than left to prose, because both fail
silently in the output:

* `-shortest` ends the mux at the shortest input — normally the voiceover —
  which quietly drops the end card. The final duration is computed instead.
* Padding runtime by repeating, freezing, or slowing a clip fakes coverage
  (R7). `tpad=stop_mode=clone` is allowed only for the declared post-VO hold.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

ENDCARD_BAND_HEIGHT = 340
LOUDNESS_TARGET = "loudnorm=I=-14:TP=-1.5:LRA=11"


class FinishStackError(ValueError):
    """Raised when a finish-stack request would truncate or fake the output."""


@dataclass
class FinishStackSpec:
    video_path: str
    output_path: str
    vo_end: float
    card_duration: float
    base_duration: float
    vo_path: Optional[str] = None
    music_path: Optional[str] = None
    logo_path: Optional[str] = None
    ass_path: Optional[str] = None
    width: int = 720
    height: int = 1280
    fps: int = 24
    accent: str = "72bf44"
    background: str = "151515"
    fonts_dir: Optional[str] = None
    music_volume: float = 0.28
    music_duck: float = 0.55


def final_duration(vo_end: float, card_duration: float) -> float:
    """Total runtime. The end card starts at VO end, so the tail is additive."""
    return round(float(vo_end) + float(card_duration), 3)


def validate_unique_clips(cuts: list[dict[str, Any]]) -> None:
    """Reject edits that pad runtime instead of using real coverage (R7).

    Raises:
        FinishStackError: on a repeated clip, or a cut that freezes, loops, or
            slows a clip down.
    """
    seen: set[str] = set()
    for cut in cuts or []:
        asset_id = cut.get("asset_id")
        if asset_id:
            if asset_id in seen:
                raise FinishStackError(
                    f"Clip {asset_id!r} is used more than once. Use longer native "
                    "selects from unique clips, or a declared after-still hold for "
                    "CTA space — never repeats to fake coverage."
                )
            seen.add(asset_id)

        if cut.get("freeze"):
            raise FinishStackError(
                f"Cut {asset_id or cut!r} freezes a clip to pad runtime. Use longer "
                "native selects from unique clips instead."
            )
        if int(cut.get("loop") or 0) > 1:
            raise FinishStackError(
                f"Cut {asset_id or cut!r} loops a clip to pad runtime. Use longer "
                "native selects from unique clips instead."
            )
        speed = cut.get("speed")
        if speed is not None and float(speed) < 1.0:
            raise FinishStackError(
                f"Cut {asset_id or cut!r} slows a clip to pad runtime. Use longer "
                "native selects from unique clips instead."
            )


def _escape_filter_path(path: str) -> str:
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _require(path: Optional[str], label: str) -> Optional[Path]:
    if not path:
        return None
    resolved = Path(path)
    if not resolved.exists():
        raise FinishStackError(f"{label} not found: {resolved}")
    return resolved


def _video_chain(spec: FinishStackSpec, total: float, has_logo: bool) -> list[str]:
    chain = [f"[0:v]fps={spec.fps},format=yuv420p,setsar=1[basev]"]

    pad = round(total - float(spec.base_duration), 3)
    label = "basev"
    if pad > 0.001:
        # Only ever the declared post-VO hold — never a substitute for footage.
        chain.append(f"[basev]tpad=stop_mode=clone:stop_duration={pad:.3f}[vext]")
        label = "vext"

    if has_logo:
        chain.append("[1:v]scale=160:-1,format=rgba,colorchannelmixer=aa=0.90[logo]")
        chain.append(f"[{label}][logo]overlay={spec.width - 188}:24[vl]")
        label = "vl"

    band_y = spec.height - ENDCARD_BAND_HEIGHT
    window = f"between(t,{spec.vo_end:.3f},{total:.3f})"
    chain.append(
        f"[{label}]drawbox=x=0:y={band_y}:w={spec.width}:h={ENDCARD_BAND_HEIGHT}:"
        f"color=0x{spec.background}@0.72:t=fill:enable='{window}'[vb]"
    )
    chain.append(
        f"[vb]drawbox=x=0:y={band_y}:w={spec.width}:h=4:"
        f"color=0x{spec.accent}@0.95:t=fill:enable='{window}'[vc]"
    )
    label = "vc"

    if spec.ass_path:
        ass = _escape_filter_path(str(Path(spec.ass_path).resolve()))
        fonts = f":fontsdir='{_escape_filter_path(spec.fonts_dir)}'" if spec.fonts_dir else ""
        chain.append(f"[{label}]ass='{ass}'{fonts}[vout]")
    else:
        chain.append(f"[{label}]null[vout]")
    return chain


def _audio_chain(spec: FinishStackSpec, total: float, vo_index: int, music_index: int) -> list[str]:
    fmt = "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
    chain: list[str] = []

    if vo_index is None and music_index is None:
        return chain

    if vo_index is not None:
        chain.append(f"[{vo_index}:a]{fmt},volume=1.2,apad=whole_dur={total:.3f}[vo]")
    if music_index is not None:
        duck = (
            f"volume='if(lt(t,{spec.vo_end:.3f}),{spec.music_duck},1.25)':eval=frame"
            if vo_index is not None
            else "volume=1.0"
        )
        chain.append(
            f"[{music_index}:a]{fmt},atrim=0:{total:.3f},asetpts=PTS-STARTPTS,"
            f"volume={spec.music_volume},afade=t=in:st=0:d=0.5,"
            f"afade=t=out:st={max(0.0, total - 2.0):.3f}:d=2.0,{duck}[mus]"
        )

    if vo_index is not None and music_index is not None:
        chain.append(f"[vo][mus]amix=inputs=2:duration=longest:dropout_transition=0,{LOUDNESS_TARGET}[aout]")
    elif vo_index is not None:
        chain.append(f"[vo]{LOUDNESS_TARGET}[aout]")
    else:
        chain.append(f"[mus]{LOUDNESS_TARGET}[aout]")
    return chain


def _add_input(
    cmd: list[str],
    index: int,
    path: Optional[Path],
    *pre_args: str,
) -> tuple[Optional[int], int]:
    """Append an optional `-i` input and return (input_index, next_index)."""
    if path is None:
        return None, index
    cmd.extend([*pre_args, "-i", str(path)])
    return index, index + 1


def build_finish_command(spec: FinishStackSpec) -> list[str]:
    """Build the ffmpeg command for the finish mux.

    Raises:
        FinishStackError: if an input is missing or the declared timings
            cannot produce an end card.
    """
    if float(spec.vo_end) <= 0:
        raise FinishStackError("vo_end must be greater than 0; the end card starts there")
    if float(spec.card_duration) <= 0:
        raise FinishStackError("card_duration must be greater than 0 to render an end card")

    video = _require(spec.video_path, "video")
    if video is None:
        raise FinishStackError("video_path is required")
    logo = _require(spec.logo_path, "logo")
    vo = _require(spec.vo_path, "voiceover")
    music = _require(spec.music_path, "music")
    _require(spec.ass_path, "captions")

    total = final_duration(spec.vo_end, spec.card_duration)

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video)]
    index = 1
    logo_index, index = _add_input(cmd, index, logo)
    vo_index, index = _add_input(cmd, index, vo)
    # Loop so a short bed still covers the full runtime.
    music_index, index = _add_input(cmd, index, music, "-stream_loop", "-1")

    graph = _video_chain(spec, total, logo_index is not None)
    graph += _audio_chain(spec, total, vo_index, music_index)

    cmd.extend(["-filter_complex", ";".join(graph), "-map", "[vout]"])
    if vo_index is not None or music_index is not None:
        cmd.extend(["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"])

    # Duration is set explicitly. `-shortest` would end at the voiceover and
    # silently drop the end card.
    cmd.extend([
        "-t", f"{total:.3f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", str(spec.fps),
        str(spec.output_path),
    ])
    return cmd
