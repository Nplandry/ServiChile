"""Enviador SMTP respeta SMTP_STARTTLS (Mailhog local sin TLS)."""

from __future__ import annotations

from email.message import EmailMessage

from app.dominio.puertos import MensajeSaliente
from app.infraestructura.correo_plataforma import EnviadorSmtp


def test_enviador_smtp_sin_starttls(monkeypatch):
    calls: list[str] = []

    class _FakeSmtp:
        def __init__(self, host, port, timeout=None):
            calls.append(f"connect:{host}:{port}")

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def starttls(self):
            calls.append("starttls")

        def login(self, user, password):
            calls.append("login")

        def send_message(self, msg: EmailMessage):
            calls.append(f"send:{msg['To']}")

    monkeypatch.setattr(
        "app.infraestructura.correo_plataforma.smtplib.SMTP", _FakeSmtp
    )
    env = EnviadorSmtp(
        "127.0.0.1",
        1025,
        "",
        "",
        "noreply@servichile.local",
        starttls=False,
    )
    assert env.disponible() is True
    env.enviar(
        MensajeSaliente(
            destino="user@example.com",
            asunto="t",
            cuerpo="hola",
        )
    )
    assert "starttls" not in calls
    assert "send:user@example.com" in calls


def test_enviador_smtp_con_starttls(monkeypatch):
    calls: list[str] = []

    class _FakeSmtp:
        def __init__(self, host, port, timeout=None):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def starttls(self):
            calls.append("starttls")

        def login(self, user, password):
            calls.append("login")

        def send_message(self, msg: EmailMessage):
            calls.append("send")

    monkeypatch.setattr(
        "app.infraestructura.correo_plataforma.smtplib.SMTP", _FakeSmtp
    )
    EnviadorSmtp(
        "smtp.ejemplo.cl",
        587,
        "u",
        "p",
        "noreply@servichile.cl",
        starttls=True,
    ).enviar(MensajeSaliente(destino="a@b.cl", asunto="t", cuerpo="c"))
    assert calls == ["starttls", "login", "send"]
