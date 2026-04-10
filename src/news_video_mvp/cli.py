from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .composer import VideoSegment, render_video, render_video_sequence
from .tts import TTSGenerationError, prepare_audio


def get_project_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def find_default_cover(project_dir: Path) -> Path:
    covers_dir = project_dir / "input" / "periodicos"
    if not covers_dir.exists() or not covers_dir.is_dir():
        raise FileNotFoundError(
            f"No se encontro el directorio de portadas: {covers_dir}"
        )

    candidates = sorted(
        path
        for path in covers_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    )
    if not candidates:
        raise FileNotFoundError(
            f"No se encontraron portadas en: {covers_dir}"
        )

    preferred_names = ("trome.png", "trome.jpg", "trome.jpeg", "trome.webp")
    by_name = {path.name.casefold(): path for path in candidates}
    for preferred_name in preferred_names:
        match = by_name.get(preferred_name)
        if match is not None:
            return match

    return candidates[0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera un video vertical de noticias con fondo, portada, narrador por gestos y TTS."
    )
    parser.add_argument("--background", type=Path, help="Imagen de fondo urbano.")
    parser.add_argument("--cover", type=Path, help="Imagen de portada del periodico.")
    parser.add_argument(
        "--gestures-dir",
        type=Path,
        help="Directorio con las poses del narrador.",
    )
    parser.add_argument("--text", help="Texto narrado.")
    parser.add_argument("--output", type=Path, help="Ruta del video final .mp4")
    parser.add_argument(
        "--audio-file",
        type=Path,
        default=None,
        help="Audio preexistente. Si se pasa, no se genera TTS.",
    )
    parser.add_argument(
        "--tts-provider",
        choices=["system", "kokoro"],
        default="system",
        help="Proveedor de TTS. `system` funciona mejor para prueba rapida en Windows.",
    )
    parser.add_argument(
        "--tts-voice",
        default="auto",
        help="Voz del TTS. En `system`, `auto` intenta elegir una voz en espanol.",
    )
    parser.add_argument(
        "--story-config",
        type=Path,
        help="JSON con varios casos de prueba para render por lote.",
    )
    return parser.parse_args()


def validate_inputs(args: argparse.Namespace) -> list[Path]:
    missing = []
    for required_path in [args.background, args.cover]:
        if required_path is None:
            continue
        if not required_path.exists():
            missing.append(str(required_path))

    if missing:
        joined = "\n".join(missing)
        raise FileNotFoundError(f"Faltan archivos requeridos:\n{joined}")

    if args.gestures_dir is None:
        raise FileNotFoundError("Debes indicar --gestures-dir o usar --story-config.")

    if not args.gestures_dir.exists() or not args.gestures_dir.is_dir():
        raise FileNotFoundError(f"No existe el directorio de gestos: {args.gestures_dir}")

    gesture_paths = sorted(
        [
            path
            for path in args.gestures_dir.iterdir()
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
        ]
    )
    if not gesture_paths:
        raise FileNotFoundError(
            f"No se encontraron imagenes de gesto en: {args.gestures_dir}"
        )
    return gesture_paths


def load_story_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(f"No existe el archivo de configuracion: {config_path}")
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if "stories" not in data or not isinstance(data["stories"], list) or not data["stories"]:
        raise ValueError("El archivo de configuracion debe incluir una lista `stories` con al menos un item.")
    return data


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
    args = argparse.Namespace(background=background, cover=cover, gestures_dir=gestures_dir)
    gesture_paths = validate_inputs(args)
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


def run_story_batch(args: argparse.Namespace) -> None:
    data = load_story_config(args.story_config)
    base_dir = args.story_config.parent
    background = Path(data.get("background", args.background)) if data.get("background", args.background) else None
    gestures_dir = Path(data.get("gestures_dir", args.gestures_dir)) if data.get("gestures_dir", args.gestures_dir) else None
    output_dir = Path(data.get("output_dir", args.output.parent if args.output else base_dir / "output"))

    if background is None or gestures_dir is None:
        raise ValueError("El story config debe definir `background` y `gestures_dir`, o pasarlos por CLI.")

    if not background.is_absolute():
        background = (base_dir / background).resolve()
    if not gestures_dir.is_absolute():
        gestures_dir = (base_dir / gestures_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    for story in data["stories"]:
        cover = Path(story["cover"])
        if not cover.is_absolute():
            cover = (base_dir / cover).resolve()

        output_name = story.get("output", f"{story['name']}.mp4")
        output = Path(output_name)
        if not output.is_absolute():
            output = (output_dir / output).resolve()

        audio_file = story.get("audio_file")
        resolved_audio = None
        if audio_file:
            resolved_audio = Path(audio_file)
            if not resolved_audio.is_absolute():
                resolved_audio = (base_dir / resolved_audio).resolve()

        render_single_story(
            background=background,
            cover=cover,
            gestures_dir=gestures_dir,
            text=story["text"],
            output=output,
            tts_provider=story.get("tts_provider", args.tts_provider),
            tts_voice=story.get("tts_voice", args.tts_voice),
            audio_file=resolved_audio,
        )


def run_story_sequence(args: argparse.Namespace) -> None:
    data = load_story_config(args.story_config)
    base_dir = args.story_config.parent
    background = Path(data.get("background", args.background)) if data.get("background", args.background) else None
    gestures_dir = Path(data.get("gestures_dir", args.gestures_dir)) if data.get("gestures_dir", args.gestures_dir) else None
    output = Path(data.get("output", args.output if args.output else base_dir / "output" / "sequence.mp4"))

    if background is None:
        raise ValueError("El story config secuencial debe definir `background`, o pasarlo por CLI.")

    if not background.is_absolute():
        background = (base_dir / background).resolve()
    if gestures_dir and not gestures_dir.is_absolute():
        gestures_dir = (base_dir / gestures_dir).resolve()
    if not output.is_absolute():
        output = (base_dir / output).resolve()

    fallback_gesture_paths: list[Path] = []
    if gestures_dir is not None:
        args_for_validation = argparse.Namespace(background=background, cover=background, gestures_dir=gestures_dir)
        fallback_gesture_paths = validate_inputs(args_for_validation)

    segments: list[VideoSegment] = []
    combined_text_parts: list[str] = []
    for story in data["stories"]:
        cover = Path(story["cover"])
        if not cover.is_absolute():
            cover = (base_dir / cover).resolve()
        if not cover.exists():
            raise FileNotFoundError(f"No existe la portada del segmento: {cover}")

        segment_text = story["text"].strip()
        segment_gestures_dir = story.get("gestures_dir")
        segment_gesture_paths = fallback_gesture_paths
        if segment_gestures_dir:
            resolved_gestures_dir = Path(segment_gestures_dir)
            if not resolved_gestures_dir.is_absolute():
                resolved_gestures_dir = (base_dir / resolved_gestures_dir).resolve()
            gesture_args = argparse.Namespace(
                background=background,
                cover=cover,
                gestures_dir=resolved_gestures_dir,
            )
            segment_gesture_paths = validate_inputs(gesture_args)
        elif not segment_gesture_paths:
            raise ValueError(
                "Cada segmento debe definir `gestures_dir`, o el story config debe incluir un `gestures_dir` general."
            )

        segments.append(
            VideoSegment(
                newspaper_name=story.get("newspaper_name", cover.stem.replace("_", " ").replace("-", " ").title()),
                cover_path=cover,
                text=segment_text,
                narrator_name=story.get("narrator_name"),
                gesture_paths=segment_gesture_paths,
            )
        )
        combined_text_parts.append(segment_text)

    merged_audio = output.with_suffix(".wav")
    prepare_audio(
        text=" ".join(combined_text_parts),
        provider=args.tts_provider,
        output_path=merged_audio,
        audio_file=args.audio_file,
        voice=args.tts_voice,
    )
    render_video_sequence(
        background_path=background,
        gesture_paths=fallback_gesture_paths,
        segments=segments,
        audio_path=merged_audio,
        output_path=output,
    )


def main() -> None:
    args = parse_args()
    project_dir = get_project_dir()

    try:
        if args.story_config:
            data = load_story_config(args.story_config)
            if data.get("render_mode") == "sequence":
                run_story_sequence(args)
            else:
                run_story_batch(args)
        else:
            if args.cover is None:
                args.cover = find_default_cover(project_dir)
            if not args.text or not args.output:
                raise ValueError("Para modo simple debes indicar --text, --output y --gestures-dir.")
            render_single_story(
                background=args.background,
                cover=args.cover,
                gestures_dir=args.gestures_dir,
                text=args.text,
                output=args.output,
                tts_provider=args.tts_provider,
                tts_voice=args.tts_voice,
                audio_file=args.audio_file,
            )
    except (FileNotFoundError, TTSGenerationError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
