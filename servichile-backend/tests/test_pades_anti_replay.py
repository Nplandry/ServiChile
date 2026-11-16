import uuid

import pytest

from app.servicios.pades_anti_replay import registrar_hash_unico


class _RepoSinMetodo:
    pass


class _RepoOk:
    def __init__(self) -> None:
        self.llamadas: list[str] = []

    def registrar_hash_pades(self, sha256: str, **kwargs) -> bool:
        self.llamadas.append(sha256)
        return True


class _RepoDuplicado:
    def registrar_hash_pades(self, sha256: str, **kwargs) -> bool:
        return False


def test_anti_replay_exige_metodo_en_repo():
    with pytest.raises(AttributeError):
        registrar_hash_unico(
            _RepoSinMetodo(),  # type: ignore[arg-type]
            "a" * 64,
            scope="empresa",
            tipo="patente",
            business_id=uuid.uuid4(),
            al_rechazar=lambda: RuntimeError("rechazo"),
        )


def test_anti_replay_registra_hash():
    repo = _RepoOk()
    registrar_hash_unico(
        repo,
        "b" * 64,
        scope="empresa",
        tipo="patente",
        business_id=uuid.uuid4(),
        al_rechazar=lambda: RuntimeError("rechazo"),
    )
    assert repo.llamadas == ["b" * 64]


def test_anti_replay_rechaza_duplicado():
    with pytest.raises(RuntimeError, match="rechazo"):
        registrar_hash_unico(
            _RepoDuplicado(),
            "c" * 64,
            scope="antecedentes",
            tipo="antecedentes",
            usuario_id=uuid.uuid4(),
            al_rechazar=lambda: RuntimeError("rechazo"),
        )


def test_anti_replay_sin_hash_no_op():
    registrar_hash_unico(
        _RepoOk(),
        None,
        scope="empresa",
        tipo="patente",
        al_rechazar=lambda: RuntimeError("rechazo"),
    )
