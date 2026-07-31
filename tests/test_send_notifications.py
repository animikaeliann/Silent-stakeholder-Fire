"""
Tests for scripts/09_send_notifications.py. Purely additive -- does not
touch any file under output/. Uses a mocked SMTP client; never opens a
real network connection.

Usage: python -m pytest tests/test_send_notifications.py -v
"""
import importlib.util
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _load_module(filename):
    path = ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(filename[:-3], path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def send_module():
    return _load_module("09_send_notifications.py")


class FakeSMTP:
    sent = []

    def __init__(self, host, port):
        self.host, self.port = host, port

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def starttls(self):
        pass

    def login(self, u, p):
        pass

    def send_message(self, msg):
        FakeSMTP.sent.append(dict(msg.items()))


def test_default_is_dry_run_with_no_env(send_module, monkeypatch):
    monkeypatch.delenv("DEMO_SEND_EMAIL", raising=False)
    monkeypatch.delenv("DEMO_RECIPIENT_OVERRIDE", raising=False)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    buf = io.StringIO()
    with redirect_stdout(buf):
        send_module.main()
    assert "DRY RUN" in buf.getvalue()


def test_missing_smtp_host_falls_back_to_dry_run(send_module, monkeypatch):
    monkeypatch.setenv("DEMO_SEND_EMAIL", "tester@example.com")
    monkeypatch.setenv("DEMO_RECIPIENT_OVERRIDE", "override@example.com")
    monkeypatch.delenv("SMTP_HOST", raising=False)
    buf = io.StringIO()
    with redirect_stdout(buf):
        send_module.main()
    assert "DRY RUN" in buf.getvalue()
    assert "SMTP_HOST is not" in buf.getvalue()


def test_invalid_email_falls_back_to_dry_run(send_module, monkeypatch):
    monkeypatch.setenv("DEMO_SEND_EMAIL", "not-an-email")
    monkeypatch.setenv("DEMO_RECIPIENT_OVERRIDE", "override@example.com")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    buf = io.StringIO()
    with redirect_stdout(buf):
        send_module.main()
    assert "DRY RUN" in buf.getvalue()


def test_real_send_only_ever_goes_to_override_address(send_module, monkeypatch):
    FakeSMTP.sent = []
    monkeypatch.setenv("DEMO_SEND_EMAIL", "tester@example.com")
    monkeypatch.setenv("DEMO_RECIPIENT_OVERRIDE", "override@example.com")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    with mock.patch.object(send_module.smtplib, "SMTP", FakeSMTP):
        send_module.main()

    drafts = send_module.load_drafts()
    assert len(FakeSMTP.sent) == len(drafts)
    for msg in FakeSMTP.sent:
        assert msg["To"] == "override@example.com"
        assert msg["Subject"].startswith("[DEMO -- would route to:")
        # never a team address, e.g. "android-client@bluesky-social-app.internal"
        assert "bluesky-social-app.internal" not in msg["To"]


def test_no_drafts_directory_does_not_crash(send_module, monkeypatch, tmp_path):
    monkeypatch.setattr(send_module, "NOTIF_DIR", tmp_path / "nonexistent")
    buf = io.StringIO()
    with redirect_stdout(buf):
        send_module.main()
    assert "No drafts found" in buf.getvalue()
