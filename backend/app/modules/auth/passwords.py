"""Hasheo de passwords con bcrypt (design decisión 4, cost 12).

`verificar` es anti-enumeración: una password contra un hash inexistente usa
el mismo trabajo de CPU que una verificación real, para que no haya fuga de
existencia porm demora.
"""
from __future__ import annotations

import bcrypt

#: Costo del algoritmo (design Open Question: benchmark en dev; default 12).
_BCRYPT_ROUNDS = 12

#: Hash decoy válido (de una password aleatoria no reutilizable) precalculado
#: lazily para comparar cuando el email no existe en la base.
_DECOY_HASH: bytes | None = None


def hash_password(password: str) -> str:
    """Hash bcrypt seguro para guardar en `usuario.password_hash`."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode()


def _decoy_hash() -> bytes:
    """Hash de manual decoy (calculado una vez por proceso)."""
    global _DECOY_HASH
    if _DECOY_HASH is None:
        _DECOY_HASH = bcrypt.hashpw(b"decoy-password-no-existe", bcrypt.gensalt(rounds=_BCRYPT_ROUNDS))
    return _DECOY_HASH


def verificar_password(password: str, password_hash: str | None) -> bool:
    """Verifica contra el hash guardado. Siempre trabajo comparable."""
    if not password_hash:
        bcrypt.checkpw(password.encode("utf-8"), _decoy_hash())
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:  # hash corrupto o formato inválido
        return False
