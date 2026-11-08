p = "backend/app/modules/agenda/repository.py"
s = open(p, encoding="utf-8").read()

old_sig = """    def upsert(
        self,
        tenant_id: str,
        antelacion_cancel_hs: int,
        antelacion_reserva_hs: int = 2,
        recordatorio_t_48h: bool | None = None,
        recordatorio_t_24h: bool | None = None,
        recordatorio_1_hs: int | None = None,
        recordatorio_2_hs: int | None = None,
        whatsapp_costo_centavos: int | None = None,
    ) -> ConfigModel:"""
new_sig = """    def upsert(
        self,
        tenant_id: str,
        antelacion_cancel_hs: int,
        antelacion_reserva_hs: int = 2,
        recordatorio_t_48h: bool | None = None,
        recordatorio_t_24h: bool | None = None,
        recordatorio_1_hs: int | None = None,
        recordatorio_2_hs: int | None = None,
        whatsapp_costo_centavos: int | None = None,
        lista_espera_ttl_hs: int | None = None,
    ) -> ConfigModel:"""
assert old_sig in s
s = s.replace(old_sig, new_sig)

old_create = """            if whatsapp_costo_centavos is not None:
                cfg.whatsapp_costo_centavos = whatsapp_costo_centavos
            self.session.add(cfg)"""
new_create = """            if whatsapp_costo_centavos is not None:
                cfg.whatsapp_costo_centavos = whatsapp_costo_centavos
            if lista_espera_ttl_hs is not None:
                cfg.lista_espera_ttl_hs = lista_espera_ttl_hs
            self.session.add(cfg)"""
assert old_create in s
s = s.replace(old_create, new_create)

old_update = """            if whatsapp_costo_centavos is not None:
                cfg.whatsapp_costo_centavos = whatsapp_costo_centavos
        self.session.flush()"""
new_update = """            if whatsapp_costo_centavos is not None:
                cfg.whatsapp_costo_centavos = whatsapp_costo_centavos
            if lista_espera_ttl_hs is not None:
                cfg.lista_espera_ttl_hs = lista_espera_ttl_hs
        self.session.flush()"""
assert old_update in s
s = s.replace(old_update, new_update)

open(p, "w", encoding="utf-8").write(s)
print("ok")
