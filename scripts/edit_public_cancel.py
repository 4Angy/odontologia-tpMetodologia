p = "backend/app/modules/agenda/public_router.py"
s = open(p, encoding="utf-8").read()
old = "        turno.estado, turno.cancelled_by, turno.cancelled_at, turno.motivo = result.estado, result.cancelled_by, result.cancelled_at, result.motivo\n        session.commit()\n        return PublicActionResponse(turno_id=turno.id, estado=turno.estado)"
new = ("        turno.estado, turno.cancelled_by, turno.cancelled_at, turno.motivo = result.estado, result.cancelled_by, result.cancelled_at, result.motivo\n"
       "        if result.estado == \"cancelado\":\n"
       "            from app.modules.lista_espera.service import Hueco, ListaEsperaService\n\n"
       "            hueco = Hueco(\n"
       "                profesional_id=turno.profesional_id,\n"
       "                inicio=turno.inicio,\n"
       "                fin=turno.fin,\n"
       "                prestacion_id=turno.prestacion_id,\n"
       "            )\n"
       "            svc_le = ListaEsperaService(session, now)\n"
       "            svc_le.ofrecer_por_hueco(turno.tenant_id, hueco, now)\n"
       "        session.commit()\n"
       "        return PublicActionResponse(turno_id=turno.id, estado=turno.estado)")
assert old in s
s = s.replace(old, new)
open(p, "w", encoding="utf-8").write(s)
print("ok")
