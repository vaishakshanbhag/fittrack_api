"""Domain error types shared across the app.

These are storage/transport-agnostic: services raise them, and the web layer
maps them to HTTP responses via a single exception handler registered in
``main.py``. Keeping the base here (rather than in any one service module) lets
every resource share the same not-found semantics without import cycles.
"""


class NotFoundError(Exception):
    """A requested resource does not exist. Mapped to HTTP 404.

    ``detail`` is a human-readable message safe to return to the client.
    """

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)
