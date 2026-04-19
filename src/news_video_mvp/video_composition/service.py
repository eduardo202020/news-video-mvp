from __future__ import annotations

from pathlib import Path

from ..composer import VideoSegment, VideoSpec, compose_video_props, render_video_sequence


def compose_preview(
    *,
    background_path: Path,
    gesture_paths: list[Path],
    segments: list[VideoSegment],
    audio_path: Path,
    output_stem: str,
    spec: VideoSpec,
) -> tuple[dict, Path]:
    return compose_video_props(
        background_path=background_path,
        gesture_paths=gesture_paths,
        segments=segments,
        audio_path=audio_path,
        output_stem=output_stem,
        spec=spec,
    )


def render_story_video(
    *,
    background_path: Path,
    gesture_paths: list[Path],
    segments: list[VideoSegment],
    audio_path: Path,
    output_path: Path,
    spec: VideoSpec,
) -> Path:
    return render_video_sequence(
        background_path=background_path,
        gesture_paths=gesture_paths,
        segments=segments,
        audio_path=audio_path,
        output_path=output_path,
        spec=spec,
    )
