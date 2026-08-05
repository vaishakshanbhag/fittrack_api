"""Application configuration, primarily auth/JWT settings.

The signing secret is read from the ``FITTRACK_SECRET_KEY`` environment
variable. Behavior when it is unset depends on ``FITTRACK_ENV``:

* ``FITTRACK_ENV=prod`` — hard failure at import time; the app refuses to boot
  without a real secret.
* anything else (dev, the default) — falls back to a fixed, clearly-labeled
  insecure key and prints a visible warning to stderr. The fixed key keeps
  tokens stable across ``--reload`` restarts while developing; it must never be
  used anywhere reachable.
"""

import os
import sys

ALGORITHM = "HS256"

# 7 days. Longer than 24h for convenience; the tradeoff is that a stateless JWT
# cannot be revoked, so the expiry is the security window. Override via env.
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.environ.get("FITTRACK_ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24 * 7))
)

_DEV_INSECURE_SECRET_KEY = "dev-insecure-secret-key-change-me-do-not-use-in-production"

SECRET_KEY = os.environ.get("FITTRACK_SECRET_KEY")
if not SECRET_KEY:
    if os.environ.get("FITTRACK_ENV", "dev") == "prod":
        raise RuntimeError(
            "FITTRACK_SECRET_KEY must be set when FITTRACK_ENV=prod. "
            "Refusing to start with an insecure default."
        )
    SECRET_KEY = _DEV_INSECURE_SECRET_KEY
    print(
        "WARNING: FITTRACK_SECRET_KEY is not set — using a fixed INSECURE dev key. "
        "Set FITTRACK_SECRET_KEY (and FITTRACK_ENV=prod) before deploying.",
        file=sys.stderr,
    )
