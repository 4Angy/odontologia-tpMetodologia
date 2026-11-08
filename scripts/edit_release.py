p = "backend/app/modules/agenda/public_booking.py"
s = open(p, encoding="utf-8").read()
old = """        released += 1
    session.flush()
    return released"""
new = """        from app.modules.lista_espera.service import Hueco, ListaEsperaService

        hueco = Hueco(
            profesional_id=turno.profesional_id,
            inicio=turno.inicio,
            fin=turno.fin,
            prestacion_id=turno.prestacion_id,
        )
        svc_le = ListaEsperaService(session, now)
        svc_le.ofrecer_por_hueco(turno.tenant_id, hueco, now)
        released += 1
    session.flush()
    return released"""
assert old in s
s = s.replace(old, new)
open(p, "w", encoding="utf-8").write(s)
print("ok")
