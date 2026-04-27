from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import urlopen, Request, urlretrieve
import time

from ..tts import TTSGenerationError, prepare_audio


def _get_voicebox_api_url(provider_settings: dict[str, object] | None = None) -> str:
    settings = provider_settings or {}
    configured = str(settings.get("api_url") or os.environ.get("VOICEBOX_API_URL") or "http://localhost:17493")
    return configured.rstrip("/")


def _voicebox_request(
    *,
    method: str,
    api_url: str,
    path: str,
    payload: dict[str, object] | None = None,
) -> dict[str, object] | list[dict[str, object]]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(
        urljoin(api_url + "/", path.lstrip("/")),
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=180) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore").strip()
        raise TTSGenerationError(
            f"Voicebox respondio con error HTTP {exc.code} en `{path}`: {details or exc.reason}"
        ) from exc
    except URLError as exc:
        raise TTSGenerationError(
            f"No se pudo conectar con Voicebox en {api_url}. Verifica que la app o backend este corriendo."
        ) from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise TTSGenerationError(f"Voicebox devolvio una respuesta no JSON en `{path}`.") from exc


def list_voicebox_profiles(provider_settings: dict[str, object] | None = None) -> list[dict[str, object]]:
    api_url = _get_voicebox_api_url(provider_settings)
    response = _voicebox_request(method="GET", api_url=api_url, path="/profiles")
    if not isinstance(response, list):
        raise TTSGenerationError("Voicebox devolvio un formato inesperado para `/profiles`.")
    return [profile for profile in response if isinstance(profile, dict)]


def transcribe_with_voicebox(
    *,
    audio_path: Path,
    provider_settings: dict[str, object] | None = None,
) -> dict[str, object]:
    if not audio_path.exists():
        raise TTSGenerationError(f"No existe el archivo de audio para transcribir: {audio_path}")

    api_url = _get_voicebox_api_url(provider_settings)
    boundary = f"----CodexVoicebox{int(time.time() * 1000)}"
    file_name = audio_path.name
    file_bytes = audio_path.read_bytes()
    body_prefix = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{file_name}"\r\n'
        f"Content-Type: audio/wav\r\n\r\n"
    ).encode("utf-8")
    body_suffix = f"\r\n--{boundary}--\r\n".encode("utf-8")
    body = body_prefix + file_bytes + body_suffix

    request = Request(
        urljoin(api_url + "/", "transcribe"),
        data=body,
        headers={
            "Accept": "application/json",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=300) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore").strip()
        raise TTSGenerationError(
            f"Voicebox respondio con error HTTP {exc.code} en `/transcribe`: {details or exc.reason}"
        ) from exc
    except URLError as exc:
        raise TTSGenerationError(
            f"No se pudo conectar con Voicebox en {api_url}. Verifica que la app o backend este corriendo."
        ) from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise TTSGenerationError("Voicebox devolvio una respuesta no JSON en `/transcribe`.") from exc

    if not isinstance(payload, dict):
        raise TTSGenerationError("Voicebox devolvio un formato inesperado para `/transcribe`.")
    return payload


def _copy_voicebox_audio(audio_reference: str, output_path: Path, api_url: str) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if audio_reference.startswith(("http://", "https://")):
        urlretrieve(audio_reference, output_path)
        return output_path

    audio_path = Path(audio_reference)
    if audio_path.exists():
        shutil.copy2(audio_path, output_path)
        return output_path

    candidate_url = urljoin(api_url + "/", audio_reference.lstrip("/"))
    try:
        urlretrieve(candidate_url, output_path)
        return output_path
    except Exception as exc:
        raise TTSGenerationError(
            "Voicebox genero audio, pero no se pudo copiar desde "
            f"`{audio_reference}`. Si el backend esta remoto, configura un `audio_path` accesible por URL."
        ) from exc


def _download_voicebox_audio_by_generation_id(
    *,
    generation_id: str,
    output_path: Path,
    api_url: str,
    timeout_seconds: int = 600,
    poll_interval_seconds: float = 2.0,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout_seconds
    audio_url = urljoin(api_url + "/", f"audio/{generation_id}")

    while time.monotonic() < deadline:
        try:
            with urlopen(audio_url, timeout=60) as response:
                content_type = response.headers.get_content_type()
                if content_type not in {"audio/wav", "audio/x-wav", "application/octet-stream"}:
                    body = response.read().decode("utf-8", errors="ignore").strip()
                    raise TTSGenerationError(
                        f"Voicebox devolvio un tipo inesperado al descargar audio: {content_type}. Respuesta: {body}"
                    )
                output_path.write_bytes(response.read())
                if output_path.exists() and output_path.stat().st_size > 0:
                    return output_path
        except HTTPError as exc:
            if exc.code in {404, 425, 500}:
                time.sleep(poll_interval_seconds)
                continue
            details = exc.read().decode("utf-8", errors="ignore").strip()
            raise TTSGenerationError(
                f"Fallo al consultar el audio de Voicebox para `{generation_id}`: HTTP {exc.code} {details}"
            ) from exc
        except URLError as exc:
            time.sleep(poll_interval_seconds)
            continue

        time.sleep(poll_interval_seconds)

    raise TTSGenerationError(
        "Voicebox no termino de generar el audio para "
        f"`{generation_id}` dentro de {timeout_seconds} segundos. "
        "Puedes subir `generation_timeout_seconds` en `provider_settings` si esa voz tarda mas."
    )


def synthesize_with_voicebox(
    *,
    text: str,
    output_path: Path,
    profile_id: str,
    language: str = "es",
    provider_settings: dict[str, object] | None = None,
) -> Path:
    if not profile_id or profile_id == "auto":
        raise TTSGenerationError(
            "Para `voicebox_local` debes definir `tts_voice` con el `profile_id` de Voicebox."
        )

    settings = provider_settings or {}
    api_url = _get_voicebox_api_url(settings)
    payload: dict[str, object] = {
        "profile_id": profile_id,
        "text": text,
        "language": str(settings.get("language") or language or "es"),
    }
    if settings.get("model_size"):
        payload["model_size"] = settings["model_size"]
    if settings.get("speed") is not None:
        payload["speed"] = float(settings["speed"])
    if settings.get("seed") is not None:
        payload["seed"] = settings["seed"]

    response = _voicebox_request(
        method="POST",
        api_url=api_url,
        path="/generate",
        payload=payload,
    )
    if not isinstance(response, dict):
        raise TTSGenerationError("Voicebox devolvio un formato inesperado para `/generate`.")

    audio_reference = response.get("audio_path")
    if isinstance(audio_reference, str) and audio_reference.strip():
        return _copy_voicebox_audio(audio_reference.strip(), output_path, api_url)

    generation_id = response.get("id")
    if isinstance(generation_id, str) and generation_id.strip():
        return _download_voicebox_audio_by_generation_id(
            generation_id=generation_id.strip(),
            output_path=output_path,
            api_url=api_url,
            timeout_seconds=int(settings.get("generation_timeout_seconds", 600)),
            poll_interval_seconds=float(settings.get("generation_poll_seconds", 2.0)),
        )

    raise TTSGenerationError(
        "Voicebox no devolvio `audio_path` ni `id` en la respuesta de generacion."
    )


def generate_voice_track(
    *,
    text: str,
    provider: str,
    output_path: Path,
    audio_file: Path | None = None,
    voice: str = "auto",
    language: str = "es",
    provider_settings: dict[str, object] | None = None,
) -> Path:
    if provider == "voicebox_local":
        return synthesize_with_voicebox(
            text=text,
            output_path=output_path,
            profile_id=voice,
            language=language,
            provider_settings=provider_settings,
        )

    return prepare_audio(
        text=text,
        provider=provider,
        output_path=output_path,
        audio_file=audio_file,
        voice=voice,
        provider_settings=provider_settings,
    )
