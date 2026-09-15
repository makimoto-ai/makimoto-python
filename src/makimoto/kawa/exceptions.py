from __future__ import annotations

from typing import Any


class KawaError(RuntimeError):
    """Raised when the API returns a non-2xx response.

    ``status_code``, ``body`` and ``headers`` are kept so callers can branch on,
    for example, a 401 (token missing/expired) versus a 404 (unknown job), and
    inspect response headers (such as ``Retry-After`` on a 429, or the ``Server``
    header that reveals whether a 413 came from the API or a proxy in front of it).

    Attributes:
        status_code (int): The response's HTTP status code.
        body (Any): The parsed response body (or ``{"raw": ...}`` if it
            wasn't valid JSON).
        url (str): The request URL that produced this response.
        headers (dict[str, str]): The response headers.
    """

    def __init__(self, status_code: int, body: Any, url: str, headers: dict[str, str] | None = None):
        """Initialise the error.

        Args:
            status_code (int): The response's HTTP status code.
            body (Any): The parsed response body.
            url (str): The request URL that produced this response.
            headers (dict[str, str] | None): The response headers, if any.
        """
        self.status_code = status_code
        self.body = body
        self.url = url
        self.headers = dict(headers or {})
        detail = ""
        if isinstance(body, dict):
            err = body.get("error")
            if isinstance(err, dict):
                detail = str(err.get("message") or err.get("code") or "")
            else:
                detail = str(body.get("message") or err or "")
        super().__init__(detail or f"HTTP {status_code}")


class KawaValidationError(KawaError):
    """Raised when a successful response doesn't match the expected shape.

    A subclass of ``KawaError``, so ``except KawaError`` catches
    this too.

    Attributes:
        validation_error (Exception): The underlying `pydantic.ValidationError`.
        status_code (int): The response's HTTP status code.
        body (Any): The parsed response body.
        url (str): The request URL that produced this response.
        headers (dict[str, str]): The response headers.
    """

    def __init__(
        self,
        status_code: int,
        body: Any,
        url: str,
        validation_error: Exception,
        headers: dict[str, str] | None = None,
    ):
        """Initialise the error.

        Args:
            status_code (int): The response's HTTP status code.
            body (Any): The parsed response body that failed validation.
            url (str): The request URL that produced this response.
            validation_error (Exception): The underlying
                `pydantic.ValidationError` this wraps.
            headers (dict[str, str] | None): The response headers, if any.
        """
        self.validation_error = validation_error
        self.status_code = status_code
        self.body = body
        self.url = url
        self.headers = dict(headers or {})
        RuntimeError.__init__(self, f"Response from {url} did not match the expected shape: {validation_error}")
