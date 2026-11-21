from __future__ import annotations

from typing import Any

import pytest

from app.infraestructura.cache_respuesta import (
    CacheNulo,
    CacheRedis,
    clave_mapa,
    clave_reputacion,
    construir_cache_respuesta,
    invalidar_negocio,
)
from app.infraestructura.redis_cliente import cliente_redis


class _CacheDict:
    """Fake mínimo para probar invalidación sin Redis."""

    def __init__(self) -> None:
        self._d: dict[str, Any] = {}

    def obtener_json(self, clave: str) -> Any | None:
        return self._d.get(clave)

    def guardar_json(self, clave: str, valor: Any, ttl_s: int) -> None:
        if ttl_s > 0:
            self._d[clave] = valor

    def borrar(self, clave: str) -> None:
        self._d.pop(clave, None)

    def borrar_prefijo(self, prefijo: str) -> None:
        for k in [x for x in self._d if x.startswith(prefijo)]:
            del self._d[k]


def test_cache_nulo_no_guarda():
    c = CacheNulo()
    c.guardar_json("k", [1], ttl_s=60)
    assert c.obtener_json("k") is None


def test_construir_cache_nulo_en_test():
    assert isinstance(construir_cache_respuesta(None, activo=False), CacheNulo)


def test_construir_cache_exige_redis_si_activo():
    with pytest.raises(ValueError, match="REDIS_URL"):
        construir_cache_respuesta("", activo=True)


def test_invalidar_negocio_borra_mapa_y_rep():
    from app.infraestructura.cache_respuesta import invalidar_lecturas_publicas

    c = _CacheDict()
    c.guardar_json(clave_mapa({"q": None}), [{"id": "1"}], 60)
    c.guardar_json(clave_reputacion("abc"), {"indice": 3}, 60)
    c.guardar_json("otra", 1, 60)
    invalidar_negocio(c, "abc")
    assert c.obtener_json(clave_mapa({"q": None})) is None
    assert c.obtener_json(clave_reputacion("abc")) is None
    assert c.obtener_json("otra") == 1

    c.guardar_json(clave_mapa({"q": "x"}), [], 60)
    c.guardar_json(clave_reputacion("z"), {"i": 1}, 60)
    invalidar_lecturas_publicas(c)
    assert c.obtener_json(clave_mapa({"q": "x"})) is None
    assert c.obtener_json(clave_reputacion("z")) is None
    assert c.obtener_json("otra") == 1


def test_cache_redis_roundtrip():
    url = "redis://localhost:6379/0"
    try:
        cliente_redis.cache_clear()
        cliente_redis(url).ping()
    except Exception as exc:
        pytest.skip(f"Redis no disponible: {exc}")

    c = CacheRedis(url)
    clave = "sc:test:cache:roundtrip"
    c.borrar(clave)
    assert c.obtener_json(clave) is None
    c.guardar_json(clave, {"ok": True}, ttl_s=30)
    assert c.obtener_json(clave) == {"ok": True}
    c.borrar(clave)
    assert c.obtener_json(clave) is None
