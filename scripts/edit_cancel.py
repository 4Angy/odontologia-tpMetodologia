
p = "backend/app/modules/agenda/router.py"
s = open(p, encoding="utf-8").read()

old = """    # Persistir transici��n + auditor��a (R1: la fila ya viene filtrada por tenant).
    fila.estado = resultado.estado
    fila.cancelled_by = resultado.cancelled_by
    fila.cancelled_at = resultado.cancelled_at
    fila.motivo = resultado.motivo
    fila.senia_pendiente_definicion = resultado.senia_pendiente_definicion
    if estado_anterior != resultado.estado:"""
new = """    # Persistir transici��n + auditor��a (R1: la fila ya viene filtrada por tenant).
    fila.estado = resultado.estado
    fila.cancelled_by = resultado.cancelled_by
    fila.cancelled_at = resultado.cancelled_at
    fila.motivo = resultado.motivo
    fila.senia_pendiente_definicion = resultado.senia_pendiente_definicion
    # C-10: disparar oferta de lista de espera si el turno se cancelo en termino.
    if estado_anterior != resultado.estado and resultado.estado == "cancelado":
        from app.modules.lista_espera.service import Hueco, ListaEsperaService

        hueco = Hueco(
            profesional_id=fila.profesional_id,
            inicio=fila.inicio,
            fin=fila.fin,
            prestacion_id=fila.prestacion_id,
        )
        svc_le = ListaEsperaService(session, now_utc)
        svc_le.ofrecer_por_hueco(user.tenant_id, hueco, now_utc)
    if estado_anterior != resultado.estado:"""
assert old in s, "old block not found"
s = s.replace(old, new)

open(p, "w", encoding="utf-8").write(s)
print("ok")
