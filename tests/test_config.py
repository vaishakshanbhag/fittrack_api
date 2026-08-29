"""Tests for config.py's import-time secret-key handling.

config.py raises (in prod, no secret set) or falls back with a stderr warning
(otherwise) as a side effect of being imported. Re-triggering that requires
`importlib.reload` after changing env vars.

Each test explicitly calls `monkeypatch.undo()` *before* the final reload,
rather than relying on monkeypatch's automatic end-of-test teardown: if we
instead just reloaded in a `finally` while the env vars were still patched,
the prod/no-secret test would re-raise RuntimeError inside its own cleanup
(the failing condition hasn't gone away yet). Calling `undo()` ourselves
first restores the real environment immediately, so the final reload always
succeeds and leaves `config` back in its normal state for every test that
runs after this one in the same process. `monkeypatch.undo()` is safe to
call more than once, so pytest's own automatic undo-at-teardown is a no-op.
"""

import importlib

import pytest

import config


def test_prod_without_secret_key_raises(monkeypatch):
    monkeypatch.delenv("FITTRACK_SECRET_KEY", raising=False)
    monkeypatch.setenv("FITTRACK_ENV", "prod")
    try:
        with pytest.raises(RuntimeError):
            importlib.reload(config)
    finally:
        monkeypatch.undo()
        importlib.reload(config)


def test_prod_with_secret_key_succeeds(monkeypatch):
    monkeypatch.setenv("FITTRACK_ENV", "prod")
    monkeypatch.setenv("FITTRACK_SECRET_KEY", "a-real-production-secret")
    try:
        importlib.reload(config)
        assert config.SECRET_KEY == "a-real-production-secret"
    finally:
        monkeypatch.undo()
        importlib.reload(config)


def test_dev_mode_falls_back_to_insecure_key_with_warning(monkeypatch, capsys):
    monkeypatch.delenv("FITTRACK_SECRET_KEY", raising=False)
    monkeypatch.delenv("FITTRACK_ENV", raising=False)
    try:
        importlib.reload(config)
        assert config.SECRET_KEY == config._DEV_INSECURE_SECRET_KEY
        captured = capsys.readouterr()
        assert "INSECURE" in captured.err
    finally:
        monkeypatch.undo()
        importlib.reload(config)
