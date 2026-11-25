from __future__ import annotations

import html
import json
import mimetypes
import re
import time
from pathlib import Path
from typing import Any, TypeVar

import httpx2
from pydantic import BaseModel, ValidationError

from .exceptions import KawaError, KawaValidationError

DEFAULT_API_URL = "https://api.makimoto.ai"

# Files above this size use a presigned upload rather than a direct one.
MULTIPART_MAX_BYTES = 4 * 1024 * 1024

# After an hour with no traffic the models shut down, and the next job waits
# several minutes for them to start again.
POLL_TIMEOUT_SECONDS = 1200.0
MAX_POLL_INTERVAL_SECONDS = 15.0
_POLL_BACKOFF = 1.5


def _now() -> float:
    return time.monotonic()


def _retry_after_seconds(headers: dict[str, str]) -> float | None:
    """A ``Retry-After`` header given in seconds; ``None`` if absent or a date."""
    for name, value in headers.items():
        if name.lower() == "retry-after":
            try:
                return max(0.0, float(value))
            except ValueError:
                return None
    return None


_TRANSIENT_STATUSES = frozenset({429, 500, 502, 503, 504})


def _is_transient(exc: Exception) -> bool:
    """A network error, 429 or gateway-type 5xx: worth retrying ``get_job``."""
    if isinstance(exc, httpx2.TransportError):
        return True
    return isinstance(exc, KawaError) and exc.status_code in _TRANSIENT_STATUSES


class _PollSchedule:
    """How long `poll()` waits between checks, and when it stops.

    Shared by both clients so the sync and async loops can't drift apart.
    The wait starts at ``interval`` and grows by half each check up to
    ``max_interval``. ``max_interval=None`` means 15 s, or a fixed
    ``interval`` when ``max_attempts`` is given, so a caller who sized
    ``max_attempts`` for a fixed wait still gets one. ``timeout`` (seconds,
    or ``None`` for no limit) and ``max_attempts`` (or ``None``) both end
    the loop, whichever comes first.
    """

    def __init__(
        self,
        interval: float,
        max_interval: float | None,
        timeout: float | None,
        max_attempts: int | None,
    ) -> None:
        if max_interval is None:
            max_interval = (
                interval if max_attempts is not None else MAX_POLL_INTERVAL_SECONDS
            )
        self._interval = interval
        self._max_interval = max(max_interval, interval)
        self._max_attempts = max_attempts
        self._started = _now()
        self._deadline = None if timeout is None else self._started + timeout
        self.attempts = 0

    @property
    def elapsed(self) -> float:
        return _now() - self._started

    def _next_wait(self) -> float:
        wait = self._interval
        self._interval = min(self._interval * _POLL_BACKOFF, self._max_interval)
        return wait

    def _out_of_attempts(self) -> bool:
        return self._max_attempts is not None and self.attempts >= self._max_attempts

    def _fit_to_deadline(self, wait: float) -> float | None:
        if self._deadline is None:
            return wait
        remaining = self._deadline - _now()
        # One last check at the deadline itself, then stop.
        return min(wait, remaining) if remaining > 0 else None

    def after_check(self) -> float | None:
        """Seconds to wait before the next check, or ``None`` to stop."""
        self.attempts += 1
        if self._out_of_attempts():
            return None
        return self._fit_to_deadline(self._next_wait())

    def after_error(self, exc: Exception) -> float | None:
        """Seconds to wait before retrying a failed check, or ``None`` to raise."""
        self.attempts += 1
        if not _is_transient(exc) or self._out_of_attempts():
            return None
        wait = self._next_wait()
        if isinstance(exc, KawaError):
            retry_after = _retry_after_seconds(exc.headers)
            if retry_after is not None:
                wait = retry_after
        return self._fit_to_deadline(wait)


class _UploadForm(BaseModel):
    url: str
    fields: dict[str, str]


class _Upload(BaseModel):
    """``POST /v1/uploads``'s response."""

    upload_id: str
    upload: _UploadForm
    max_bytes: int | None = None


ModelT = TypeVar("ModelT", bound=BaseModel)


class _BaseKawaClient:
    """Shared, transport-agnostic state and helpers for `KawaClient` and
    `AsyncKawaClient`.

    Holds the credential/URL/timeout state and the pure (no I/O) helpers
    both clients need identically: building the request URL, building the
    Authorization header, and validating a response body against a
    pydantic model. Each subclass owns its own HTTP session (an
    ``httpx2.Client`` or ``httpx2.AsyncClient``) and its own ``_request()``,
    since those genuinely differ between sync and async, everything else
    lives here to keep the two clients from drifting apart.

    Attributes:
        api_key (str): API key, stripped of surrounding whitespace.
        api_url (str): Base URL for the API, trailing slash removed.
        timeout (float): Default per-request timeout, in seconds.
        last_status (int | None): HTTP status code of the most recent
            response, or ``None`` before any request has been made.
        last_headers (dict[str, str]): Headers of the most recent response.
        last_url (str | None): URL of the most recent response, or ``None``
            before any request has been made.
    """

    def __init__(self, api_key: str, api_url: str, timeout: float) -> None:
        """Set credential/URL/timeout state; subclasses resolve `api_key`
        (env var fallback, logging) and set up their own session before
        calling this.

        Args:
            api_key (str): API key, already resolved (env var fallback, if
                any, applied by the caller).
            api_url (str): Base URL for the API.
            timeout (float): Default per-request timeout, in seconds.
        """
        self.api_key = api_key.strip()
        self.api_url = (api_url or DEFAULT_API_URL).rstrip("/")
        self.timeout = timeout
        # Metadata of the most recent HTTP response, for debugging.
        self.last_status: int | None = None
        self.last_headers: dict[str, str] = {}
        self.last_url: str | None = None

    def _url(self, path: str) -> str:
        """Join `api_url` and a path into a full request URL.

        Args:
            path (str): Path to append to ``api_url``.

        Returns:
            str: The joined request URL.
        """
        return f"{self.api_url}{path}"

    def _headers(self) -> dict[str, str]:
        """Build the Authorization header; raises if there's no API key.

        Returns:
            dict[str, str]: Headers containing ``Authorization: Bearer <api_key>``.

        Raises:
            ValueError: If no API key is available.
        """
        if not self.api_key:
            raise ValueError("A Makimoto API key is required.")
        return {"Authorization": f"Bearer {self.api_key}"}

    def _parse(self, model: type[ModelT], body: Any) -> ModelT:
        """Validate `body` against a pydantic model.

        Wraps a `pydantic.ValidationError` as `KawaValidationError` (a
        `KawaError` subclass), so a caller catching `KawaError` gets this
        too, a 2xx response that doesn't match the expected shape is the
        same practical problem as a bad status code, just found later.

        Args:
            model (type[ModelT]): The pydantic model class to validate against.
            body (Any): The raw response body to validate.

        Returns:
            ModelT: The validated model instance.

        Raises:
            KawaValidationError: If ``body`` doesn't match ``model``'s shape.
        """
        try:
            return model.model_validate(body)
        except ValidationError as exc:
            raise KawaValidationError(
                self.last_status or 0, body, self.last_url or self.api_url, exc
            ) from exc

    # -- create_transcription helpers --------------------------------------- #

    @staticmethod
    def _content_type(path: Path) -> str:
        return mimetypes.guess_type(path.name)[0] or "application/octet-stream"

    @staticmethod
    def _multipart_fields(
        language: str | None, metadata: dict[str, Any] | None
    ) -> dict[str, str]:
        fields: dict[str, str] = {}
        if language and language.strip():
            fields["language"] = language.strip()
        if metadata:
            fields["metadata"] = json.dumps(metadata, separators=(",", ":"))
        return fields

    @staticmethod
    def _upload_job_body(
        upload_id: str, language: str | None, metadata: dict[str, Any] | None
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"upload_id": upload_id}
        if language and language.strip():
            body["language"] = language.strip()
        if metadata:
            body["metadata"] = metadata
        return body

    @staticmethod
    def _check_upload_size(path: Path, upload: _Upload) -> None:
        """Refuse a file the upload form won't accept, before sending it."""
        size = path.stat().st_size
        if upload.max_bytes is not None and size > upload.max_bytes:
            raise ValueError(
                f"{path.name} is {size} bytes, over the {upload.max_bytes}-byte "
                "upload limit."
            )

    def _check_storage_response(self, response: httpx2.Response) -> None:
        """Record a storage upload's response; raise `KawaError` if it failed."""
        self.last_status = response.status_code
        self.last_headers = dict(response.headers)
        self.last_url = str(response.url)
        if response.status_code >= 300:
            raise KawaError(
                response.status_code,
                {"error": _storage_error(response.text), "raw": response.text},
                self.last_url,
                headers=self.last_headers,
            )


def _storage_error(text: str) -> dict[str, str]:
    """Storage's XML error body as ``{"code", "message"}``."""
    code = re.search(r"<Code>([^<]*)</Code>", text)
    message = re.search(r"<Message>([^<]*)</Message>", text)
    return {
        "code": code.group(1) if code else "",
        "message": "Upload to storage failed"
        + (f": {html.unescape(message.group(1))}" if message else ""),
    }
