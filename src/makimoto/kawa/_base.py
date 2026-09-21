from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from .exceptions import KawaValidationError

DEFAULT_API_URL = "https://api.makimoto.ai"

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
