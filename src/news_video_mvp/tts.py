from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
from typing import Any


class TTSGenerationError(RuntimeError):
    """Raised when audio cannot be generated."""


def _normalize_voice_tokens(value: str) -> set[str]:
    normalized = value.casefold().replace("_", " ").replace("-", " ")
    return {token for token in normalized.split() if token}


def _voice_matches_language(voice: Any, preferred_language: str) -> bool:
    preferred = preferred_language.casefold()
    candidates: list[str] = []
    candidate_tokens: set[str] = set()

    for attr in ("name", "id"):
        value = getattr(voice, attr, None)
        if isinstance(value, str):
            candidates.append(value)
            candidate_tokens.update(_normalize_voice_tokens(value))

    languages = getattr(voice, "languages", None) or []
    for entry in languages:
        if isinstance(entry, bytes):
            try:
                decoded = entry.decode("utf-8", errors="ignore")
                candidates.append(decoded)
                candidate_tokens.update(_normalize_voice_tokens(decoded))
            except Exception:
                continue
        elif isinstance(entry, str):
            candidates.append(entry)
            candidate_tokens.update(_normalize_voice_tokens(entry))

    aliases = {
        "es",
        "es-es",
        "es-mx",
        "spa",
        "spanish",
        "castilian",
        "castellano",
        "espanol",
        "español",
    }
    if preferred not in aliases:
        aliases.add(preferred)

    for candidate in candidates:
        lowered = candidate.casefold()
        if lowered in aliases:
            return True
        if any(lowered.startswith(f"{alias}-") for alias in aliases):
            return True
        if any(f"({alias})" in lowered for alias in aliases):
            return True
    if candidate_tokens.intersection(aliases):
        return True
    return False


def _select_system_voice(engine: Any, preferred_language: str, preferred_voice: str | None) -> bool:
    voices = engine.getProperty("voices") or []
    if not voices:
        return False

    if preferred_voice:
        wanted_tokens = _normalize_voice_tokens(preferred_voice)
        for voice in voices:
            searchable = " ".join(
                str(getattr(voice, attr, "")) for attr in ("name", "id")
            ).casefold()
            if wanted_tokens and wanted_tokens.issubset(_normalize_voice_tokens(searchable)):
                engine.setProperty("voice", voice.id)
                return True

    for voice in voices:
        if _voice_matches_language(voice, preferred_language):
            engine.setProperty("voice", voice.id)
            return True

    return False


def synthesize_with_system_tts(
    text: str,
    output_path: Path,
    rate: int = 180,
    preferred_language: str = "es",
    preferred_voice: str | None = None,
) -> Path:
    if os.name == "nt":
        return synthesize_with_windows_speech(
            text=text,
            output_path=output_path,
            preferred_language=preferred_language,
            preferred_voice=preferred_voice,
        )

    try:
        import pyttsx3
    except ImportError as exc:
        raise TTSGenerationError(
            "pyttsx3 no esta instalado. Instala dependencias o usa --audio-file."
        ) from exc

    engine = pyttsx3.init()
    engine.setProperty("rate", rate)
    selected = _select_system_voice(
        engine,
        preferred_language=preferred_language,
        preferred_voice=preferred_voice,
    )
    if not selected:
        raise TTSGenerationError(
            "No se encontro una voz en espanol en el TTS del sistema. "
            "Instala una voz en espanol de Windows, usa --tts-provider kokoro, o pasa --audio-file."
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    engine.save_to_file(text, str(output_path))
    engine.runAndWait()
    engine.stop()

    if not output_path.exists():
        raise TTSGenerationError("El motor TTS del sistema no genero el archivo de audio.")
    return output_path


def synthesize_with_windows_speech(
    text: str,
    output_path: Path,
    preferred_language: str = "es",
    preferred_voice: str | None = None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    escaped_text = (
        text.replace("`", "``")
        .replace('"', '`"')
        .replace("\r", " ")
        .replace("\n", " ")
    )
    escaped_output = str(output_path).replace("'", "''")
    preferred_voice_filter = ""
    if preferred_voice:
        escaped_voice = preferred_voice.replace("'", "''")
        preferred_voice_filter = (
            "$voice = $voices | Where-Object { $_.VoiceInfo.Name -like '*"
            + escaped_voice
            + "*' } | Select-Object -First 1;"
        )

    script = (
        "Add-Type -AssemblyName System.Speech; "
        "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$voices = $synth.GetInstalledVoices(); "
        + preferred_voice_filter
        + "if (-not $voice) { "
        "$voice = $voices | Where-Object { $_.VoiceInfo.Culture.TwoLetterISOLanguageName -eq '"
        + preferred_language
        + "' } | Select-Object -First 1; "
        "} "
        "if (-not $voice) { throw 'NoSpanishVoice'; } "
        "$synth.SelectVoice($voice.VoiceInfo.Name); "
        "$synth.SetOutputToWaveFile('"
        + escaped_output
        + "'); "
        '$synth.Speak("'
        + escaped_text
        + '"); '
        "$synth.Dispose();"
    )

    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or completed.stdout or "").strip()
        if "NoSpanishVoice" in stderr:
            raise TTSGenerationError(
                "No se encontro una voz en espanol en Windows. "
                "Instala una voz en espanol, usa --tts-provider kokoro, o pasa --audio-file."
            )
        raise TTSGenerationError(f"Fallo el TTS de Windows: {stderr or 'sin detalles'}")

    if not output_path.exists():
        raise TTSGenerationError("Windows TTS no genero el archivo de audio.")
    return output_path


def synthesize_with_kokoro(text: str, output_path: Path, voice: str = "af_sarah") -> Path:
    try:
        from kokoro_onnx import Kokoro
        import soundfile as sf
    except ImportError as exc:
        raise TTSGenerationError(
            "Kokoro no esta disponible. Instala `pip install -e .[kokoro]` o usa --audio-file."
        ) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    kokoro = Kokoro()
    samples, sample_rate = kokoro.create(text, voice=voice, speed=1.0, lang="es")
    sf.write(str(output_path), samples, sample_rate)

    if not output_path.exists():
        raise TTSGenerationError("Kokoro no genero el archivo de audio.")
    return output_path


def prepare_audio(
    text: str,
    provider: str,
    output_path: Path,
    audio_file: Path | None = None,
    voice: str = "auto",
) -> Path:
    if audio_file is not None:
        if not audio_file.exists():
            raise TTSGenerationError(f"No existe el archivo de audio: {audio_file}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(audio_file, output_path)
        return output_path

    if provider == "system":
        preferred_voice = None if voice == "auto" else voice
        return synthesize_with_system_tts(
            text=text,
            output_path=output_path,
            preferred_language="es",
            preferred_voice=preferred_voice,
        )
    if provider == "kokoro":
        kokoro_voice = "af_sarah" if voice == "auto" else voice
        return synthesize_with_kokoro(text=text, output_path=output_path, voice=kokoro_voice)

    raise TTSGenerationError(f"Proveedor TTS no soportado: {provider}")
