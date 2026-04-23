from __future__ import annotations

from pathlib import Path

from .composer import VideoSegment, render_video, render_video_sequence
from .story_config import (
    StoryConfig,
    StorySegmentConfig,
    ensure_image_file,
    validate_gestures_dir,
)
from .tts import prepare_audio


def render_single_story(
    *,
    background: Path,
    cover: Path,
    gestures_dir: Path,
    text: str,
    output: Path,
    tts_provider: str,
    tts_voice: str,
    audio_file: Path | None = None,
) -> None:
    ensure_image_file(background, label="la imagen de fondo")
    ensure_image_file(cover, label="la portada")
    gesture_paths = validate_gestures_dir(gestures_dir)
    audio_path = output.with_suffix(".wav")
    prepare_audio(
        text=text,
        provider=tts_provider,
        output_path=audio_path,
        audio_file=audio_file,
        voice=tts_voice,
    )
    render_video(
        background_path=background,
        cover_path=cover,
        gesture_paths=gesture_paths,
        text=text,
        audio_path=audio_path,
        output_path=output,
    )


def render_story_batch(
    config: StoryConfig,
    *,
    cli_background: Path | None,
    cli_gestures_dir: Path | None,
    cli_output: Path | None,
    cli_tts_provider: str,
    cli_tts_voice: str,
) -> None:
    background = config.background or cli_background
    gestures_dir = config.gestures_dir or cli_gestures_dir
    if background is None or gestures_dir is None:
        raise ValueError(
            "El story config debe definir `background` y `gestures_dir`, o pasarlos por CLI."
        )

    output_dir = config.output_dir or (cli_output.parent if cli_output else config.config_path.parent / "output")
    output_dir.mkdir(parents=True, exist_ok=True)

    for story in config.stories:
        render_single_story(
            background=background,
            cover=ensure_segment_cover(story),
            gestures_dir=story.gestures_dir or gestures_dir,
            text=story.text,
            output=resolve_batch_output(story=story, output_dir=output_dir),
            tts_provider=story.tts_provider or cli_tts_provider,
            tts_voice=story.tts_voice or cli_tts_voice,
            audio_file=story.audio_file,
        )


def render_story_sequence(
    config: StoryConfig,
    *,
    cli_background: Path | None,
    cli_gestures_dir: Path | None,
    cli_output: Path | None,
    cli_audio_file: Path | None,
    cli_tts_provider: str,
    cli_tts_voice: str,
) -> None:
    background = config.background or cli_background
    if background is None:
        raise ValueError(
            "El story config secuencial debe definir `background`, o pasarlo por CLI."
        )

    fallback_gestures_dir = config.gestures_dir or cli_gestures_dir
    fallback_gesture_paths = (
        validate_gestures_dir(fallback_gestures_dir) if fallback_gestures_dir else []
    )

    segments: list[VideoSegment] = []
    combined_text_parts: list[str] = []
    for story in config.stories:
        segment = normalize_story_segment(
            story,
            fallback_gesture_paths=fallback_gesture_paths,
        )
        segments.append(segment)
        combined_text_parts.append(segment.text)

    output = config.output or cli_output or config.config_path.parent / "output" / "sequence.mp4"
    merged_audio = output.with_suffix(".wav")
    prepare_audio(
        text=" ".join(combined_text_parts),
        provider=cli_tts_provider,
        output_path=merged_audio,
        audio_file=cli_audio_file,
        voice=cli_tts_voice,
    )
    render_video_sequence(
        background_path=background,
        gesture_paths=fallback_gesture_paths,
        segments=segments,
        audio_path=merged_audio,
        output_path=output,
    )


def resolve_batch_output(*, story: StorySegmentConfig, output_dir: Path) -> Path:
    if story.output is not None:
        return story.output
    stem = story.newspaper_name or (story.cover.stem if story.cover else "story")
    safe_stem = stem.replace(" ", "_").lower()
    return output_dir / f"{safe_stem}.mp4"


def ensure_segment_cover(story: StorySegmentConfig) -> Path:
    if story.cover is None:
        raise ValueError("Cada historia debe definir `cover`.")
    return ensure_image_file(story.cover, label="la portada del segmento")


def normalize_story_segment(
    story: StorySegmentConfig,
    *,
    fallback_gesture_paths: list[Path],
) -> VideoSegment:
    cover = ensure_segment_cover(story)
    segment_gesture_paths = (
        validate_gestures_dir(story.gestures_dir)
        if story.gestures_dir is not None
        else fallback_gesture_paths
    )
    if not segment_gesture_paths:
        raise ValueError(
            "Cada segmento debe definir `gestures_dir`, o el story config debe incluir un `gestures_dir` general."
        )
    if not story.text:
        raise ValueError(f"El segmento {cover.stem} debe incluir `text`.")

    return VideoSegment(
        newspaper_name=story.newspaper_name
        or cover.stem.replace("_", " ").replace("-", " ").title(),
        cover_path=cover,
        headline=story.newspaper_name or cover.stem.replace("_", " ").replace("-", " ").title(),
        text=story.text,
        narrator_name=story.narrator_name,
        gesture_paths=segment_gesture_paths,
    )
