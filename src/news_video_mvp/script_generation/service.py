from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..automation_models import read_json, write_json
from ..project import get_project_dir


def collect_script_inputs(job: dict) -> dict[str, object]:
    input_assets = job.get("input_assets", {})
    extraction = job.get("extraction", {})
    return {
        "source_id": job.get("source_id"),
        "front_page_image": input_assets.get("front_page_image"),
        "pages": input_assets.get("pages", []),
        "headline_candidates": extraction.get("headline_candidates", []),
        "ocr_blocks": extraction.get("ocr_blocks", []),
        "classification": job.get("classification", {}),
    }


def _resolve_repo_path(path_value: str | None) -> Path | None:
    if not path_value:
        return None
    return get_project_dir() / Path(path_value)


def _build_asset_lines(pages: list[dict[str, object]]) -> list[str]:
    if not pages:
        return ["- No hay imagenes registradas en `input_assets.pages`."]

    lines: list[str] = []
    for page in pages:
        label = str(page.get("label") or "Imagen")
        role = str(page.get("role") or "asset")
        page_number = page.get("page_number")
        local_path = str(page.get("local_path") or "")
        source_url = page.get("source_url")
        suffix = f"pagina {page_number}" if page_number is not None else role
        line = f"- {label} ({suffix}): `{local_path}`"
        if source_url:
            line += f" | origen: {source_url}"
        lines.append(line)
    return lines


def _build_ocr_excerpt(blocks: list[dict[str, object]], *, max_items: int = 12) -> list[str]:
    texts = [str(block.get("text", "")).strip() for block in blocks]
    selected = [text for text in texts if text][:max_items]
    if not selected:
        return ["- No hay OCR cargado en el job."]
    return [f"- {text}" for text in selected]


def _build_headline_lines(headlines: list[object]) -> list[str]:
    if not headlines:
        return ["- No hay titulares extraidos todavia."]
    return [f"- {str(headline)}" for headline in headlines]


def build_chatgpt_prompt(
    *,
    job: dict,
    template: dict,
    package_payload: dict[str, object],
) -> str:
    script = job.get("script", {})
    classification = job.get("classification", {})
    source_name = str(package_payload.get("source_name") or job.get("source_id") or "Fuente")
    lines = [
        "# Prompt para ChatGPT",
        "",
        "Adjunta las imagenes listadas abajo en este chat antes de pedir la redaccion.",
        "",
        "## Rol",
        "Actua como guionista de un video vertical de noticias para redes sociales.",
        "",
        "## Objetivo",
        f"Escribe un speech breve en espanol para narrar la portada de {source_name}.",
        "",
        "## Reglas",
    ]
    for rule in template.get("system_rules", []):
        lines.append(f"- {rule}")

    lines.extend(
        [
            "",
            "## Restricciones de salida",
            f"- Idioma: {template.get('output_constraints', {}).get('language', 'es')}",
            f"- Maximo de oraciones: {template.get('output_constraints', {}).get('max_sentences', 3)}",
            f"- Duracion objetivo: {template.get('output_constraints', {}).get('target_duration_seconds', [18, 26])}",
            "- No incluyas encabezados, notas del editor, ni explicaciones.",
            "- Devuelve solo el speech final listo para narracion.",
            "",
            "## Contexto del job",
            f"- job_id: `{job.get('job_id')}`",
            f"- source_id: `{job.get('source_id')}`",
            f"- clasificacion is_news: `{classification.get('is_news')}`",
            f"- prioridad: `{classification.get('priority')}`",
            "",
            "## Titulares detectados",
        ]
    )
    lines.extend(_build_headline_lines(list(package_payload.get("headline_candidates", []))))
    lines.extend(["", "## OCR resumido"])
    lines.extend(_build_ocr_excerpt(list(package_payload.get("ocr_blocks", []))))
    lines.extend(["", "## Imagenes a subir"])
    lines.extend(_build_asset_lines(list(package_payload.get("pages", []))))
    lines.extend(
        [
            "",
            "## Instruccion final",
            "Con las imagenes adjuntas y el contexto anterior, redacta un speech corto, claro y natural para el narrador.",
        ]
    )
    if script.get("review_notes"):
        lines.extend(["", "## Notas editoriales existentes", str(script["review_notes"])])
    return "\n".join(lines) + "\n"


def prepare_chatgpt_script_package(
    *,
    job_manifest_path: Path,
    script_template_path: Path,
    output_dir: Path | None = None,
    force: bool = False,
) -> Path:
    project_dir = get_project_dir()
    job = read_json(job_manifest_path)
    template = read_json(script_template_path)
    package_dir = output_dir or job_manifest_path.parent / "review" / "script-package"
    if package_dir.exists() and any(package_dir.iterdir()) and not force:
        raise ValueError(
            "El directorio del paquete ya existe y contiene archivos. Usa `--force` para regenerarlo."
        )
    package_dir.mkdir(parents=True, exist_ok=True)

    script_inputs = collect_script_inputs(job)
    package_payload = {
        "job_id": job.get("job_id"),
        "source_name": str(job.get("source_id", "")).replace("-", " ").title(),
        "template_id": template.get("template_id"),
        "template_description": template.get("description"),
        "structure": template.get("structure", []),
        **script_inputs,
    }

    prompt_text = build_chatgpt_prompt(job=job, template=template, package_payload=package_payload)
    request_path = package_dir / "script-request.json"
    prompt_path = package_dir / "chatgpt-prompt.md"
    upload_list_path = package_dir / "images-to-upload.txt"

    write_json(request_path, package_payload)
    prompt_path.write_text(prompt_text, encoding="utf-8")
    upload_list_path.write_text(
        "\n".join(
            str(_resolve_repo_path(page.get("local_path")).resolve())
            for page in package_payload.get("pages", [])
            if page.get("local_path")
        )
        + "\n",
        encoding="utf-8",
    )

    timestamp = datetime.now().isoformat(timespec="seconds")
    job["script"] = {
        **job.get("script", {}),
        "template_id": template.get("template_id", job.get("script", {}).get("template_id")),
        "provider": "chatgpt_plus_manual",
        "package_dir": package_dir.resolve().relative_to(project_dir).as_posix(),
        "request_payload_path": request_path.resolve().relative_to(project_dir).as_posix(),
        "prompt_path": prompt_path.resolve().relative_to(project_dir).as_posix(),
    }
    job["audit"]["updated_at"] = timestamp
    job["audit"].setdefault("events", []).append(
        {
            "stage": "script_package",
            "status": "prepared",
            "timestamp": timestamp,
            "details": "Paquete preparado para generar speech con ChatGPT a partir de imagenes del job.",
        }
    )
    write_json(job_manifest_path, job)
    return package_dir


def import_generated_script(
    *,
    job_manifest_path: Path,
    generated_text: str | None = None,
    generated_text_file: Path | None = None,
    provider: str = "chatgpt_plus_manual",
    model: str | None = None,
    approve: bool = False,
) -> Path:
    if generated_text_file is not None:
        if not generated_text_file.exists():
            raise FileNotFoundError(f"No existe el archivo de speech: {generated_text_file}")
        resolved_text = generated_text_file.read_text(encoding="utf-8")
    else:
        resolved_text = generated_text or ""

    final_text = " ".join(resolved_text.split()).strip()
    if not final_text:
        raise ValueError("Debes proporcionar `--generated-text` o `--generated-text-file` con contenido.")

    project_dir = get_project_dir()
    job = read_json(job_manifest_path)
    draft_output_path = job_manifest_path.parent / "review" / "generated-script.txt"
    draft_output_path.parent.mkdir(parents=True, exist_ok=True)
    draft_output_path.write_text(final_text + "\n", encoding="utf-8")

    timestamp = datetime.now().isoformat(timespec="seconds")
    job["script"] = {
        **job.get("script", {}),
        "provider": provider,
        "model": model,
        "draft": final_text,
        "draft_path": draft_output_path.resolve().relative_to(project_dir).as_posix(),
        "approved_text": final_text if approve else job.get("script", {}).get("approved_text", ""),
    }
    job["status"] = "approved" if approve else "review_pending"
    job["audit"]["updated_at"] = timestamp
    job["audit"].setdefault("events", []).append(
        {
            "stage": "script_import",
            "status": "approved" if approve else "completed",
            "timestamp": timestamp,
            "details": "Speech importado desde proveedor externo."
            if not approve
            else "Speech importado y aprobado automaticamente.",
        }
    )
    return write_json(job_manifest_path, job)
