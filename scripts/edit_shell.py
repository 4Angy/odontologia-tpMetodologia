p = r"C:\Users\Cara Palida\Documents\projects\odontologia-tpMetodologia\frontend\src\shared\ui\AppShell.tsx"
s = open(p, encoding="utf-8").read()
s = s.replace(
'{ to: "/consumo", label: "Consumo" },',
'{ to: "/consumo", label: "Consumo" },\n  { to: "/lista-espera", label: "Lista de espera" },')
s = s.replace(
'      "/consumo": "notificaciones",\n',
'      "/consumo": "notificaciones",\n      "/lista-espera": "agenda",\n')
open(p, "w", encoding="utf-8").write(s)
print("ok")
