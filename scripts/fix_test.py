p = r"C:\Users\Cara Palida\Documents\projects\odontologia-tpMetodologia\backend\app\modules\lista_espera\tests\test_lista_espera_core.py"
s = open(p, encoding="utf-8").read()
s = s.replace(
"from app.modules.agenda.models import (\n    ConfigModel,\n",
"from app.modules.agenda.models import (\n    ConfigModel,\n    ProfesionalModel,\n")
s = s.replace(
'    s.add(TenantModel(id=TENANT, nombre="Demo LE", slug="demo-le"))\n    s.flush()\n',
'    s.add(TenantModel(id=TENANT, nombre="Demo LE", slug="demo-le"))\n    s.flush()\n    s.add(ProfesionalModel(id="prof-1", tenant_id=TENANT, nombre="Dr. Test"))\n    s.flush()\n')
open(p, "w", encoding="utf-8").write(s)
print("ok")
