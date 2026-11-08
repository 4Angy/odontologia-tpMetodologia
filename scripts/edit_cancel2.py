p = "backend/app/modules/agenda/router.py"
s = open(p, encoding="utf-8").read()
old = "    fila.senia_pendiente_definicion = resultado.senia_pendiente_definicion\n    if estado_anterior != resultado.estado:"
new = ("    fila.senia_pendiente_definicion = resultado.senia_pendiente_definicion\n"
       "    # C-10: disparar oferta de lista de espera si el turno se cancelo en termino.\n"
       "    if estado_anterior != resultado.estado and resultado.estado == \"cancelado\":\n"
       "        from app.modules.lista_espera.service import Hueco, ListaEsperaService\n\n"
       "        hueco = Hueco(\n"
       "            profesional_id=fila.profesional_id,\n"
       "            inicio=fila.inicio,\n"
       "            fin=fila.fin,\n"
       "            prestacion_id=fila.prestacion_id,\n"
       "        )\n"
       "        svc_le = ListaEsperaService(session, now_utc)\n"
       "        svc_le.ofrecer_por_hueco(user.tenant_id, hueco, now_utc)\n"
       "    if estado_anterior != resultado.estado:")
assert old in s, "old not found"
s = s.replace(old, new)
open(p, "w", encoding="utf-8").write(s)
print("ok")
