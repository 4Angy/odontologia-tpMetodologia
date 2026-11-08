p = "backend/app/modules/lista_espera/service.py"
s = open(p, encoding="utf-8").read()

old = """    def aceptar(self, raw_token: str, tenant_slug: str, now: datetime | None = None) -> tuple[ListaEsperaModel, TurnoModel]:
        now = now or self.now
        tenant = self._tenant_by_slug(tenant_slug)
        token = self._token_valido(raw_token, "waitlist_accept", now)
        if token.tenant_id != tenant.id:"""
new = """    def aceptar(self, raw_token: str, tenant_slug: str | None = None, now: datetime | None = None) -> tuple[ListaEsperaModel, TurnoModel]:
        now = now or self.now
        token = self._token_valido(raw_token, "waitlist_accept", now)
        if tenant_slug is None:
            tenant = self.session.get(TenantModel, token.tenant_id)
            if tenant is None:
                raise ListaEsperaError("RN-AU-01", "Tenant no encontrado.", 404)
        else:
            tenant = self._tenant_by_slug(tenant_slug)
        if token.tenant_id != tenant.id:"""
assert old in s
s = s.replace(old, new)

old2 = """    def declinar(self, raw_token: str, tenant_slug: str, now: datetime | None = None) -> ListaEsperaModel:
        now = now or self.now
        tenant = self._tenant_by_slug(tenant_slug)
        token = self._token_valido(raw_token, "waitlist_decline", now)
        if token.tenant_id != tenant.id:"""
new2 = """    def declinar(self, raw_token: str, tenant_slug: str | None = None, now: datetime | None = None) -> ListaEsperaModel:
        now = now or self.now
        token = self._token_valido(raw_token, "waitlist_decline", now)
        if tenant_slug is None:
            tenant = self.session.get(TenantModel, token.tenant_id)
            if tenant is None:
                raise ListaEsperaError("RN-AU-01", "Tenant no encontrado.", 404)
        else:
            tenant = self._tenant_by_slug(tenant_slug)
        if token.tenant_id != tenant.id:"""
assert old2 in s
s = s.replace(old2, new2)

open(p, "w", encoding="utf-8").write(s)
print("ok")
