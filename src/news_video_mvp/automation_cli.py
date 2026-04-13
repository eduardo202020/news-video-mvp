from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .automation_pipeline import (
    approve_script_for_job,
    build_story_manifest_from_job,
    create_job_manifest,
    extract_and_classify_job,
    generate_script_from_job,
    generate_voice_and_subtitles_for_job,
)
from .tts import TTSGenerationError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CLI para la capa declarativa de automatizacion del proyecto."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_job = subparsers.add_parser(
        "init-job",
        help="Crea un job declarativo desde una fuente configurada.",
    )
    init_job.add_argument("--source-config", type=Path, required=True)
    init_job.add_argument("--date", required=True, dest="job_date")
    init_job.add_argument(
        "--approval-mode",
        choices=["manual", "semi_auto", "full_auto"],
        default="semi_auto",
    )
    init_job.add_argument("--voice-profile", type=Path, required=True)
    init_job.add_argument("--video-template", type=Path, required=True)
    init_job.add_argument("--script-template-id", default="default-anchor")
    init_job.add_argument("--publish-profile-id", default="tiktok")
    init_job.add_argument("--subtitle-policy-id", default="default-2-lines")
    init_job.add_argument("--front-page-image", type=Path)
    init_job.add_argument("--front-page-url")
    init_job.add_argument("--download-front-page", action="store_true")
    init_job.add_argument("--job-id")

    extract_job = subparsers.add_parser(
        "extract-job",
        help="Carga OCR externo y clasifica la portada como noticia o publicidad.",
    )
    extract_job.add_argument("--job-manifest", type=Path, required=True)
    extract_job.add_argument("--editorial-policy", type=Path, required=True)
    extract_job.add_argument("--ocr-text-file", type=Path)
    extract_job.add_argument("--ocr-text")
    extract_job.add_argument("--ocr-confidence", type=float)

    generate_script = subparsers.add_parser(
        "generate-script",
        help="Genera un borrador de speech del narrador desde los titulares extraidos.",
    )
    generate_script.add_argument("--job-manifest", type=Path, required=True)
    generate_script.add_argument("--script-template", type=Path, required=True)
    generate_script.add_argument("--force", action="store_true")

    approve_script = subparsers.add_parser(
        "approve-script",
        help="Aprueba el guion del job y opcionalmente reemplaza el texto final.",
    )
    approve_script.add_argument("--job-manifest", type=Path, required=True)
    approve_script.add_argument("--approved-text")
    approve_script.add_argument("--review-notes")

    voice_job = subparsers.add_parser(
        "voice-job",
        help="Genera audio y subtitulos desde el texto aprobado del job.",
    )
    voice_job.add_argument("--job-manifest", type=Path, required=True)
    voice_job.add_argument("--voice-profile", type=Path, required=True)
    voice_job.add_argument("--subtitle-policy", type=Path, required=True)
    voice_job.add_argument("--audio-file", type=Path)
    voice_job.add_argument("--force", action="store_true")

    build_story = subparsers.add_parser(
        "build-story-manifest",
        help="Construye el story-manifest a partir de un job-manifest.",
    )
    build_story.add_argument("--job-manifest", type=Path, required=True)
    build_story.add_argument("--voice-profile", type=Path, required=True)
    build_story.add_argument("--video-template", type=Path, required=True)
    build_story.add_argument("--output", type=Path)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "init-job":
            manifest_path = create_job_manifest(
                source_config_path=args.source_config,
                job_date=args.job_date,
                approval_mode=args.approval_mode,
                voice_profile_path=args.voice_profile,
                video_template_path=args.video_template,
                script_template_id=args.script_template_id,
                publish_profile_id=args.publish_profile_id,
                subtitle_policy_id=args.subtitle_policy_id,
                front_page_image=args.front_page_image,
                front_page_url=args.front_page_url,
                download_front_page=args.download_front_page,
                job_id=args.job_id,
            )
            print(f"Job manifest creado en: {manifest_path}")
            return

        if args.command == "build-story-manifest":
            manifest_path = build_story_manifest_from_job(
                job_manifest_path=args.job_manifest,
                voice_profile_path=args.voice_profile,
                video_template_path=args.video_template,
                output_path=args.output,
            )
            print(f"Story manifest creado en: {manifest_path}")
            return

        if args.command == "extract-job":
            manifest_path = extract_and_classify_job(
                job_manifest_path=args.job_manifest,
                editorial_policy_path=args.editorial_policy,
                ocr_text=args.ocr_text,
                ocr_text_file=args.ocr_text_file,
                ocr_confidence=args.ocr_confidence,
            )
            print(f"Job manifest actualizado en: {manifest_path}")
            return

        if args.command == "generate-script":
            manifest_path = generate_script_from_job(
                job_manifest_path=args.job_manifest,
                script_template_path=args.script_template,
                force=args.force,
            )
            print(f"Job manifest actualizado en: {manifest_path}")
            return

        if args.command == "approve-script":
            manifest_path = approve_script_for_job(
                job_manifest_path=args.job_manifest,
                approved_text=args.approved_text,
                review_notes=args.review_notes,
            )
            print(f"Job manifest actualizado en: {manifest_path}")
            return

        if args.command == "voice-job":
            manifest_path = generate_voice_and_subtitles_for_job(
                job_manifest_path=args.job_manifest,
                voice_profile_path=args.voice_profile,
                subtitle_policy_path=args.subtitle_policy,
                audio_file=args.audio_file,
                force=args.force,
            )
            print(f"Job manifest actualizado en: {manifest_path}")
            return

        parser.error(f"Comando no soportado: {args.command}")
    except (FileNotFoundError, ValueError, TTSGenerationError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
