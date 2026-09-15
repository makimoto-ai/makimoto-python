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


class Job(BaseModel):
    """A transcription job, in whatever state the API last reported.

    ``result`` is only present once ``succeeded``; ``error`` only once
    ``failed``.

    Attributes:
        job_id (str): The job's identifier.
        status (str): Current lifecycle status, e.g. ``"queued"``,
            ``"processing"``, ``"succeeded"``, or ``"failed"``.
        result (TranscriptResult | None): The transcript, once ``succeeded``.
        error (JobError | None): The failure detail, once ``failed``.
    """

    job_id: str
    status: str = "unknown"
    result: TranscriptResult | None = None
    error: JobError | None = None

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

    @property
    def is_terminal(self) -> bool:
        """True once `status` is `"succeeded"` or `"failed"`.

        Returns:
            bool: Whether the job has reached a terminal status.
        """
        return self.status in TERMINAL_STATUSES
