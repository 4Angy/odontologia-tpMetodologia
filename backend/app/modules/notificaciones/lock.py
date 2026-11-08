"""Lock del tick del scheduler (D3).

Redis con degradación a Postgres (`pg_try_advisory_lock`). El lock es
coordinación, no estado: perderlo no apaga los recordatorios.
"""
from __future__ import annotations

from sqlalchemy import text

TTL_TICK = 840  # segundos


def redis_key(tenant_id: str) -> str:
    return f"tick:notificaciones:{tenant_id}"


class TickLock:
    def __init__(self, redis_client: object | None, session) -> None:
        self.redis_client = redis_client
        self.session = session

    def acquire(self, tenant_id: str) -> bool:
        key = redis_key(tenant_id)
        if self.redis_client is not None:
            try:
                adquirido = self.redis_client.set(key, "1", nx=True, ex=TTL_TICK)
                if adquirido:
                    return True
                return False
            except Exception:  # noqa: BLE001 - degradación a Postgres
                pass
        try:
            result = self.session.execute(
                text("SELECT pg_try_advisory_lock(hashtext('notificaciones:' || :tid))"),
                {"tid": tenant_id},
            ).scalar()
            return bool(result)
        except Exception:  # noqa: BLE001
            return True

    def release(self, tenant_id: str) -> None:
        if self.redis_client is not None:
            try:
                self.redis_client.delete(redis_key(tenant_id))
            except Exception:  # noqa: BLE001
                pass
        try:
            self.session.execute(
                text("SELECT pg_advisory_unlock(hashtext('notificaciones:' || :tid))"),
                {"tid": tenant_id},
            )
        except Exception:  # noqa: BLE001
            pass


__all__ = ["TickLock", "TTL_TICK", "redis_key"]
