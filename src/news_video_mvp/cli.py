from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .pipeline import render_single_story, render_story_batch, render_story_sequence
from .project import find_default_cover, get_project_dir
from .story_config import load_story_config, validate_gestures_dir
from .tts import TTSGenerationError


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


def run_story_batch(args: argparse.Namespace) -> None:
    config = load_story_config(args.story_config)
    render_story_batch(
        config,
        cli_background=args.background,
        cli_gestures_dir=args.gestures_dir,
        cli_output=args.output,
        cli_tts_provider=args.tts_provider,
        cli_tts_voice=args.tts_voice,
    )


def run_story_sequence(args: argparse.Namespace) -> None:
    config = load_story_config(args.story_config)
    render_story_sequence(
        config,
        cli_background=args.background,
        cli_gestures_dir=args.gestures_dir,
        cli_output=args.output,
        cli_audio_file=args.audio_file,
        cli_tts_provider=args.tts_provider,
        cli_tts_voice=args.tts_voice,
    )


def main() -> None:
    args = parse_args()
    project_dir = get_project_dir()

    try:
        if args.story_config:
            config = load_story_config(args.story_config)
            if config.render_mode == "sequence":
                run_story_sequence(args)
            else:
                run_story_batch(args)
        else:
            if args.cover is None:
                args.cover = find_default_cover(project_dir)
            if not args.text or not args.output:
                raise ValueError("Para modo simple debes indicar --text, --output y --gestures-dir.")
            if args.gestures_dir is None:
                raise FileNotFoundError("Debes indicar --gestures-dir o usar --story-config.")
            validate_gestures_dir(args.gestures_dir)
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
