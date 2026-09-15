from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

#: A job's lifecycle ends here; `Job.is_terminal` checks membership in this set.
TERMINAL_STATUSES = {"succeeded", "failed"}


class Segment(BaseModel):
    """One speaker-attributed slice of the transcript. Frozen.

    If the API omits ``speaker_alias``, a ``speaker_id``-based default is
    filled in before validation (``"Speaker 0"``, etc.)

    Attributes:
        text (str): The segment's transcribed text.
        time_start (float): Start time of the segment, in seconds.
        time_end (float): End time of the segment, in seconds.
        speaker_id (int): Numeric identifier of the speaker.
        speaker_alias (str): Human-readable speaker label, e.g. ``"Speaker 0"``.
    """

    model_config = ConfigDict(frozen=True)

    text: str = ""
    time_start: float = 0.0
    time_end: float = 0.0
    speaker_id: int = 0
    speaker_alias: str = ""

    @model_validator(mode="before")
    @classmethod
    def _default_speaker_alias(cls, data: Any) -> Any:
        """Fill in a ``speaker_id``-based ``speaker_alias`` if one is missing.

        Args:
            data (Any): The raw input being validated into this model.

        Returns:
            Any: ``data``, with ``speaker_alias`` defaulted if it was
                missing and ``data`` is a dict; otherwise unchanged.
        """
        if isinstance(data, dict) and not data.get("speaker_alias"):
            data = {**data, "speaker_alias": f"Speaker {data.get('speaker_id', 0)}"}
        return data


class TranscriptResult(BaseModel):
    """The ``result`` payload returned once a job succeeds. Frozen.

    ``segments`` reads from the API's ``transcript`` key, the Python-facing
    name stays ``segments`` for readability; the wire format doesn't have to
    match the attribute name.

    Attributes:
        language (str | None): Detected or requested language code.
        duration_seconds (float | None): Duration of the recording, in seconds.
        words_count (int | None): Total number of transcribed words.
        segments (list[Segment]): Speaker-attributed slices of the transcript.
    """

    model_config = ConfigDict(frozen=True)

    language: str | None = None
    duration_seconds: float | None = None
    words_count: int | None = None
    segments: list[Segment] = Field(default_factory=list, validation_alias="transcript")

    @property
    def full_text(self) -> str:
        """Every segment's text, joined with a space.

        Returns:
            str: The full transcript text.
        """
        return " ".join(s.text for s in self.segments).strip()


class SummaryResult(BaseModel):
    """The ``result`` payload for a ``summary`` job. Frozen.

    Attributes:
        topic (str | None): Short label for what the call was about, `None`
            if the model produced none.
        summary (str): Prose summary of the conversation.
        meta_data (dict[str, Any] | None): Generation metadata reported by
            the provider (model, batch size, timing), passed through unread.
    """

    model_config = ConfigDict(frozen=True)

    topic: str | None = None
    summary: str = ""
    meta_data: dict[str, Any] | None = None


class TagsResult(BaseModel):
    """The ``result`` payload for a ``tags`` job. Frozen.

    The tag taxonomy is fixed by the service and isn't configurable per
    account.

    Attributes:
        tags (dict[str, list[str]]): Tag category to selected values, e.g.
            ``{"call_reason": ["billing_issue"]}``.
        meta_data (dict[str, Any] | None): Generation metadata reported by
            the provider, passed through unread.
    """

    model_config = ConfigDict(frozen=True)

    tags: dict[str, list[str]] = Field(default_factory=dict)
    meta_data: dict[str, Any] | None = None


class JobError(BaseModel):
    """The ``error`` payload returned once a job fails.

    Attributes:
        code (str): Machine-readable error code.
        message (str): Human-readable error message.
        provider_error (dict[str, Any] | None): Raw error detail from the
            underlying transcription provider, if any.
    """

    code: str
    message: str
    provider_error: dict[str, Any] | None = None


class Usage(BaseModel):
    """The caller's transcription minute quota, as returned by `KawaClient.usage()`.

    Attributes:
        limit_minutes (float): Total minutes allotted for the billing period.
        used_minutes (float): Minutes already consumed.
        remaining_minutes (float): Minutes left before the limit is reached.
    """

    limit_minutes: float
    used_minutes: float
    remaining_minutes: float


#: Maps a job's `type` to the model its `result` payload validates against;
#: `transcription` is also the fallback for a job with no `type` at all, to
#: keep parsing a plain (pre-`type`) transcription job unchanged.
_RESULT_MODEL_BY_TYPE: dict[str, type[BaseModel]] = {
    "transcription": TranscriptResult,
    "summary": SummaryResult,
    "tags": TagsResult,
}


class Job(BaseModel):
    """A job, in whatever state the API last reported.

    Covers all three job types the API produces: a transcription itself,
    plus a summary or tags job created from one via `KawaClient.create_summary()`
    / `KawaClient.create_tags()`. ``type`` says which, and therefore which
    shape ``result`` takes; ``result`` is only present once ``succeeded``,
    ``error`` only once ``failed``.

    The fields below aren't all present on every response;
    each is only sent by specific endpoints:
    - ``received_at`` only on the response to ``create_transcription()``;
    - ``original_filename``, ``language`` and ``audio_seconds`` only on
        ``list_transcriptions()``/``iter_transcriptions()`` entries;
    - ``created_at`` and ``updated_at`` on those too, plus ``type`` on
        ``get_job()``.

    ``language`` here is the list view's own top-level field (whatever was
    requested at submission), distinct from the detected language on
    ``result.language``, which only exists once a job succeeds.

    ``type`` is always ``"transcription"``, ``"summary"`` or ``"tags"``.

    Attributes:
        job_id (str): The job's identifier. Poll a summary or tags job by
            its own ``job_id``, not the source transcription's.
        type (str | None): ``"transcription"``, ``"summary"``, or
            ``"tags"``. `None` on a response that predates this field, treated
            the same as ``"transcription"`` for parsing `result`.
        status (str): Current lifecycle status, e.g. ``"queued"``,
            ``"processing"``, ``"succeeded"``, or ``"failed"``.
        source_job_id (str | None): The transcription this job was derived
            from, for a ``summary`` or ``tags`` job. `None` for a
            transcription itself, which has no source.
        result (TranscriptResult | SummaryResult | TagsResult | None): The
            job's result, once ``succeeded``; its shape follows ``type``.
        error (JobError | None): The failure detail, once ``failed``.
        received_at (str | None): Submission timestamp, only on
            `KawaClient.create_transcription()`'s response.
        original_filename (str | None): Only on `list_transcriptions()`/
            `iter_transcriptions()` entries.
        language (str | None): Requested/submission-time language code, only
            on `list_transcriptions()`/`iter_transcriptions()` entries;
            distinct from the detected `result.language`.
        audio_seconds (float | None): Only on `list_transcriptions()`/
            `iter_transcriptions()` entries.
        created_at (str | None): Only on `list_transcriptions()`/
            `iter_transcriptions()` entries.
        updated_at (str | None): Only on `list_transcriptions()`/
            `iter_transcriptions()` entries.
    """

    job_id: str
    type: str | None = None
    status: str = "unknown"
    source_job_id: str | None = None
    result: TranscriptResult | SummaryResult | TagsResult | None = None
    error: JobError | None = None
    received_at: str | None = None
    original_filename: str | None = None
    language: str | None = None
    audio_seconds: float | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _job_id_fallback(cls, data: Any) -> Any:
        """Fall back to an `id` key if `job_id` itself is missing.

        If neither key is present, validation fails, a response with no
        identifiable job id at all is genuinely malformed, not just unusual.

        Args:
            data (Any): The raw input being validated into this model.

        Returns:
            Any: ``data``, with ``job_id`` defaulted from ``id`` if it was
                missing and ``data`` is a dict; otherwise unchanged.
        """
        if isinstance(data, dict) and not data.get("job_id") and data.get("id"):
            data = {**data, "job_id": data["id"]}
        return data

    @model_validator(mode="before")
    @classmethod
    def _parse_result_by_type(cls, data: Any) -> Any:
        """Validate a dict `result` against the model matching `type`.

        Left to pydantic's own union handling, a `SummaryResult` or
        `TagsResult` payload would still validate as a `TranscriptResult`
        (every one of its fields has a default, and extra keys are ignored
        by default), silently producing an empty transcript instead of the
        actual summary or tags. Picking the model from `type` up front
        avoids that.

        Args:
            data (Any): The raw input being validated into this model.

        Returns:
            Any: ``data``, with a dict ``result`` replaced by the parsed
                model instance for ``type``; otherwise unchanged.
        """
        if isinstance(data, dict) and isinstance(data.get("result"), dict):
            model = _RESULT_MODEL_BY_TYPE.get(
                data.get("type") or "transcription", TranscriptResult
            )
            data = {**data, "result": model.model_validate(data["result"])}
        return data

    @property
    def is_terminal(self) -> bool:
        """True once `status` is `"succeeded"` or `"failed"`.

        Returns:
            bool: Whether the job has reached a terminal status.
        """
        return self.status in TERMINAL_STATUSES


class TranscriptionPage(BaseModel):
    """One page of `KawaClient.list_transcriptions()`. Frozen.

    ``next_cursor`` is ``None`` once there's nothing left; pass it back as
    ``list_transcriptions(cursor=page.next_cursor)`` to fetch the next page.
    """

    model_config = ConfigDict(frozen=True)

    transcriptions: list[Job] = Field(default_factory=list)
    next_cursor: str | None = None
