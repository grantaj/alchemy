from pydantic import BaseModel, Field

from alchemy.speech_to_text import TranscriptSegment, TranscriptWord


class ChunkingConfig(BaseModel):
    max_seconds: float = Field(default=8.0, gt=0)
    max_words: int = Field(default=35, gt=0)
    min_words: int = Field(default=5, ge=1)
    min_silence_gap: float = Field(default=0.7, ge=0)
    prefer_sentence_boundary: bool = True
    sentence_punctuation: str = ".?!;:"


class TranscriptChunk(BaseModel):
    text: str
    start: float | None = None
    end: float | None = None
    word_count: int

    @property
    def duration(self) -> float | None:
        if self.start is None or self.end is None:
            return None
        return max(0.0, self.end - self.start)


def chunk_segments(
    segments: list[TranscriptSegment],
    config: ChunkingConfig,
) -> list[TranscriptChunk]:
    words = _flatten_words(segments)
    if words:
        return _normalize_chunks(_chunk_words(words, config), config)

    return _normalize_chunks(
        _chunk_plain_text(" ".join(segment.text.strip() for segment in segments), config),
        config,
    )


def _flatten_words(segments: list[TranscriptSegment]) -> list[TranscriptWord]:
    words: list[TranscriptWord] = []
    for segment in segments:
        words.extend(segment.words)
    return words


def _chunk_words(words: list[TranscriptWord], config: ChunkingConfig) -> list[TranscriptChunk]:
    chunks: list[TranscriptChunk] = []
    current: list[TranscriptWord] = []
    pending_boundary: int | None = None

    for word in words:
        gap = _gap(current[-1], word) if current else 0.0
        if current and gap >= config.min_silence_gap and len(current) >= config.min_words:
            chunks.append(_word_chunk(current))
            current = []
            pending_boundary = None

        current.append(word)

        if _is_sentence_boundary(word.word, config):
            pending_boundary = len(current)

        should_flush = _should_flush_words(current, config)
        if not should_flush:
            continue

        if (
            config.prefer_sentence_boundary
            and pending_boundary is not None
            and pending_boundary >= config.min_words
        ):
            chunks.append(_word_chunk(current[:pending_boundary]))
            current = current[pending_boundary:]
            pending_boundary = None
            continue

        if len(current) >= config.min_words:
            chunks.append(_word_chunk(current))
            current = []
            pending_boundary = None

    if current:
        if chunks and len(current) < config.min_words:
            previous = chunks.pop()
            chunks.append(_merge_chunk_words(previous, current))
        else:
            chunks.append(_word_chunk(current))

    return chunks


def _chunk_plain_text(text: str, config: ChunkingConfig) -> list[TranscriptChunk]:
    words = text.split()
    if not words:
        return []

    chunks: list[TranscriptChunk] = []
    current: list[str] = []
    pending_boundary: int | None = None

    for word in words:
        current.append(word)
        if _is_sentence_boundary(word, config):
            pending_boundary = len(current)

        if len(current) < config.max_words:
            continue

        if (
            config.prefer_sentence_boundary
            and pending_boundary is not None
            and pending_boundary >= config.min_words
        ):
            chunks.append(_text_chunk(current[:pending_boundary]))
            current = current[pending_boundary:]
            pending_boundary = None
        else:
            chunks.append(_text_chunk(current))
            current = []
            pending_boundary = None

    if current:
        if chunks and len(current) < config.min_words:
            previous = chunks.pop()
            chunks.append(
                TranscriptChunk(
                    text=f"{previous.text} {' '.join(current)}",
                    start=previous.start,
                    end=previous.end,
                    word_count=previous.word_count + len(current),
                )
            )
        else:
            chunks.append(_text_chunk(current))

    return chunks


def _should_flush_words(words: list[TranscriptWord], config: ChunkingConfig) -> bool:
    if len(words) >= config.max_words:
        return True

    start = words[0].start
    end = words[-1].end
    return start is not None and end is not None and end - start >= config.max_seconds


def _gap(previous: TranscriptWord, current: TranscriptWord) -> float:
    if previous.end is None or current.start is None:
        return 0.0
    return max(0.0, current.start - previous.end)


def _is_sentence_boundary(text: str, config: ChunkingConfig) -> bool:
    return text.strip().endswith(tuple(config.sentence_punctuation))


def _word_chunk(words: list[TranscriptWord]) -> TranscriptChunk:
    return TranscriptChunk(
        text=_join_word_text(words),
        start=words[0].start,
        end=words[-1].end,
        word_count=sum(1 for word in words if not _is_punctuation(word.word)),
    )


def _merge_chunk_words(previous: TranscriptChunk, words: list[TranscriptWord]) -> TranscriptChunk:
    return TranscriptChunk(
        text=f"{previous.text} {_join_word_text(words)}",
        start=previous.start,
        end=words[-1].end,
        word_count=previous.word_count + sum(1 for word in words if not _is_punctuation(word.word)),
    )


def _text_chunk(words: list[str]) -> TranscriptChunk:
    return TranscriptChunk(text=" ".join(words).strip(), word_count=len(words))


def _join_word_text(words: list[TranscriptWord]) -> str:
    text = "".join(word.word for word in words).strip()
    return " ".join(text.split())


def _is_punctuation(text: str) -> bool:
    stripped = text.strip()
    return bool(stripped) and all(not char.isalnum() for char in stripped)


def _normalize_chunks(chunks: list[TranscriptChunk], config: ChunkingConfig) -> list[TranscriptChunk]:
    normalized: list[TranscriptChunk] = []

    for chunk in chunks:
        if normalized and _starts_with_punctuation(chunk.text):
            previous = normalized.pop()
            normalized.append(_merge_chunks(previous, chunk))
            continue

        if normalized and chunk.word_count <= config.min_words:
            previous = normalized.pop()
            normalized.append(_merge_chunks(previous, chunk))
            continue

        normalized.append(chunk)

    return normalized


def _starts_with_punctuation(text: str) -> bool:
    stripped = text.lstrip()
    return bool(stripped) and not stripped[0].isalnum()


def _merge_chunks(left: TranscriptChunk, right: TranscriptChunk) -> TranscriptChunk:
    joiner = "" if _starts_with_punctuation(right.text) else " "
    return TranscriptChunk(
        text=f"{left.text}{joiner}{right.text}".strip(),
        start=left.start,
        end=right.end or left.end,
        word_count=left.word_count + right.word_count,
    )
