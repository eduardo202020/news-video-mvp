from __future__ import annotations

from dataclasses import dataclass
import math
import textwrap


@dataclass(slots=True)
class SubtitleSegment:
    text: str
    start: float
    end: float


def split_sentences(text: str) -> list[str]:
    normalized = " ".join(text.replace("\n", " ").split())
    if not normalized:
        return []

    sentences: list[str] = []
    current = []
    for char in normalized:
        current.append(char)
        if char in ".!?;":
            sentence = "".join(current).strip()
            if sentence:
                sentences.append(sentence)
            current = []

    if current:
        remaining = "".join(current).strip()
        if remaining:
            sentences.extend(textwrap.wrap(remaining, width=90))

    return [s for s in sentences if s]


def build_subtitle_segments(text: str, total_duration: float, max_chars: int = 75) -> list[SubtitleSegment]:
    sentences = split_sentences(text)
    if not sentences:
        return []

    chunks: list[str] = []
    for sentence in sentences:
        if len(sentence) <= max_chars:
            chunks.append(sentence)
        else:
            chunks.extend(textwrap.wrap(sentence, width=max_chars))

    total_chars = sum(max(len(chunk), 1) for chunk in chunks)
    segments: list[SubtitleSegment] = []
    cursor = 0.0

    for index, chunk in enumerate(chunks):
        weight = max(len(chunk), 1) / total_chars
        duration = max(1.6, total_duration * weight)
        if index == len(chunks) - 1:
            end = total_duration
        else:
            end = min(total_duration, cursor + duration)
        segments.append(SubtitleSegment(text=chunk, start=cursor, end=end))
        cursor = end

    return rebalance_segments(segments, total_duration)


def rebalance_segments(segments: list[SubtitleSegment], total_duration: float) -> list[SubtitleSegment]:
    if not segments:
        return []

    balanced: list[SubtitleSegment] = []
    cursor = 0.0
    for index, segment in enumerate(segments):
        remaining = len(segments) - index
        remaining_time = max(total_duration - cursor, 0.2 * remaining)
        min_slice = remaining_time / remaining
        segment_duration = max(segment.end - segment.start, min(1.4, min_slice))
        end = min(total_duration, cursor + segment_duration)
        balanced.append(SubtitleSegment(text=segment.text, start=cursor, end=end))
        cursor = end

    if balanced:
        balanced[-1].end = total_duration
    return balanced


def compute_gesture_switches(duration: float, interval: float = 2.0) -> int:
    return max(1, math.ceil(duration / interval))
