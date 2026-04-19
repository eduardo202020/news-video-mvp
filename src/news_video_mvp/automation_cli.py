from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .automation_pipeline import (
    approve_script_for_job,
    build_story_manifest_from_job,
    compose_job_for_preview,
    create_job_manifest,
    extract_and_classify_job,
    generate_script_from_job,
    generate_voice_and_subtitles_for_job,
    import_script_for_job,
    list_available_voicebox_profiles,
    prepare_script_package_for_job,
    publish_job,
    scrape_pages_for_job,
    transcribe_job_audio,
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
    init_job.add_argument("--supporting-page-url", action="append", default=[])
    init_job.add_argument("--supporting-page-image", type=Path, action="append", default=[])
    init_job.add_argument("--job-id")

    scrape_pages = subparsers.add_parser(
        "scrape-pages",
        help="Adjunta paginas o recortes adicionales al job desde URLs o archivos locales.",
    )
    scrape_pages.add_argument("--job-manifest", type=Path, required=True)
    scrape_pages.add_argument("--page-url", action="append", default=[])
    scrape_pages.add_argument("--page-image", type=Path, action="append", default=[])

    extract_job = subparsers.add_parser(
        "extract-job",
        help="Carga OCR externo y clasifica la portada como noticia o publicidad.",
    )
    extract_job.add_argument("--job-manifest", type=Path, required=True)
    extract_job.add_argument("--editorial-policy", type=Path, required=True)
    extract_job.add_argument("--ocr-text-file", type=Path)
    extract_job.add_argument("--ocr-text")
    extract_job.add_argument("--ocr-confidence", type=float)

    prepare_script = subparsers.add_parser(
        "prepare-script-package",
        help="Prepara un paquete con prompt y contexto para generar el speech manualmente en ChatGPT.",
    )
    prepare_script.add_argument("--job-manifest", type=Path, required=True)
    prepare_script.add_argument("--script-template", type=Path, required=True)
    prepare_script.add_argument("--output-dir", type=Path)
    prepare_script.add_argument("--force", action="store_true")

    generate_script = subparsers.add_parser(
        "generate-script",
        help="Genera un borrador de speech del narrador desde los titulares extraidos.",
    )
    generate_script.add_argument("--job-manifest", type=Path, required=True)
    generate_script.add_argument("--script-template", type=Path, required=True)
    generate_script.add_argument("--force", action="store_true")

    import_script = subparsers.add_parser(
        "import-script",
        help="Importa al job el speech generado externamente y opcionalmente lo aprueba.",
    )
    import_script.add_argument("--job-manifest", type=Path, required=True)
    import_script.add_argument("--generated-text")
    import_script.add_argument("--generated-text-file", type=Path)
    import_script.add_argument("--provider", default="chatgpt_plus_manual")
    import_script.add_argument("--model")
    import_script.add_argument("--approve", action="store_true")

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

    list_voicebox = subparsers.add_parser(
        "list-voicebox-profiles",
        help="Lista los perfiles disponibles en la instancia local de Voicebox.",
    )
    list_voicebox.add_argument("--voice-profile", type=Path)

    transcribe_job = subparsers.add_parser(
        "transcribe-job",
        help="Transcribe un audio del job usando Voicebox local.",
    )
    transcribe_job.add_argument("--job-manifest", type=Path, required=True)
    transcribe_job.add_argument("--voice-profile", type=Path, required=True)
    transcribe_job.add_argument("--audio-file", type=Path)
    transcribe_job.add_argument("--force", action="store_true")

    compose_job = subparsers.add_parser(
        "compose-job",
        help="Sincroniza assets y actualiza generated-story.js para previsualizacion en Remotion.",
    )
    compose_job.add_argument("--job-manifest", type=Path, required=True)
    compose_job.add_argument("--video-template", type=Path, required=True)
    compose_job.add_argument("--story-manifest", type=Path)

    publish_job_parser = subparsers.add_parser(
        "publish-job",
        help="Prepara o registra la publicacion declarativa del job.",
    )
    publish_job_parser.add_argument("--job-manifest", type=Path, required=True)
    publish_job_parser.add_argument("--publishing-profile", type=Path, required=True)
    publish_job_parser.add_argument("--confirm", action="store_true")
    publish_job_parser.add_argument("--platform-post-id")
    publish_job_parser.add_argument("--post-url")

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
                supporting_page_urls=args.supporting_page_url,
                supporting_page_images=args.supporting_page_image,
                job_id=args.job_id,
            )
            print(f"Job manifest creado en: {manifest_path}")
            return

        if args.command == "scrape-pages":
            manifest_path = scrape_pages_for_job(
                job_manifest_path=args.job_manifest,
                page_urls=args.page_url,
                page_images=args.page_image,
            )
            print(f"Job manifest actualizado en: {manifest_path}")
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

        if args.command == "prepare-script-package":
            package_dir = prepare_script_package_for_job(
                job_manifest_path=args.job_manifest,
                script_template_path=args.script_template,
                output_dir=args.output_dir,
                force=args.force,
            )
            print(f"Paquete de speech preparado en: {package_dir}")
            return

        if args.command == "generate-script":
            manifest_path = generate_script_from_job(
                job_manifest_path=args.job_manifest,
                script_template_path=args.script_template,
                force=args.force,
            )
            print(f"Job manifest actualizado en: {manifest_path}")
            return

        if args.command == "import-script":
            manifest_path = import_script_for_job(
                job_manifest_path=args.job_manifest,
                generated_text=args.generated_text,
                generated_text_file=args.generated_text_file,
                provider=args.provider,
                model=args.model,
                approve=args.approve,
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

        if args.command == "list-voicebox-profiles":
            profiles = list_available_voicebox_profiles(voice_profile_path=args.voice_profile)
            if not profiles:
                print("No se encontraron perfiles en Voicebox.")
                return
            for profile in profiles:
                profile_id = profile.get("id") or profile.get("profile_id") or "sin-id"
                name = profile.get("name") or profile.get("display_name") or "sin-nombre"
                language = profile.get("language") or "n/a"
                print(f"{profile_id}\t{name}\t{language}")
            return

        if args.command == "transcribe-job":
            manifest_path = transcribe_job_audio(
                job_manifest_path=args.job_manifest,
                voice_profile_path=args.voice_profile,
                audio_file=args.audio_file,
                force=args.force,
            )
            print(f"Job manifest actualizado en: {manifest_path}")
            return

        if args.command == "compose-job":
            manifest_path = compose_job_for_preview(
                job_manifest_path=args.job_manifest,
                story_manifest_path=args.story_manifest,
                video_template_path=args.video_template,
            )
            print(f"Story manifest compuesto para preview: {manifest_path}")
            return

        if args.command == "publish-job":
            manifest_path = publish_job(
                job_manifest_path=args.job_manifest,
                publishing_profile_path=args.publishing_profile,
                confirm=args.confirm,
                platform_post_id=args.platform_post_id,
                post_url=args.post_url,
            )
            print(f"Job manifest actualizado en: {manifest_path}")
            return

        parser.error(f"Comando no soportado: {args.command}")
    except (FileNotFoundError, ValueError, TTSGenerationError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
