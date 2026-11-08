p = "backend/app/worker/main.py"
s = open(p, encoding="utf-8").read()

old = """    # Sender
    sender = SenderService(
        session,
        whatsapp=whatsapp_client,
        email=email_client,
        now=now,
        public_base_url=settings.public_base_url,
    )
    procesados = sender.ejecutar()
    session.commit()"""
new = """    # Sender
    sender = SenderService(
        session,
        whatsapp=whatsapp_client,
        email=email_client,
        now=now,
        public_base_url=settings.public_base_url,
    )
    procesados = sender.ejecutar()

    # C-10: vencer ofertas expiradas y avanzar.
    from app.modules.lista_espera.service import ListaEsperaService

    ListaEsperaService(session, now).vencer_y_avanzar(now)

    session.commit()"""
assert old in s
s = s.replace(old, new)
open(p, "w", encoding="utf-8").write(s)
print("ok")
