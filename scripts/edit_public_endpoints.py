p = "backend/app/modules/lista_espera/router.py"
s = open(p, encoding="utf-8").read()
s = s.replace('    tenant_slug: str = Query(..., alias="tenant_slug"),', '    tenant_slug: str | None = Query(default=None, alias="tenant_slug"),')
open(p, "w", encoding="utf-8").write(s)
print("ok")
