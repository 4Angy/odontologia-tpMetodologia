p = "backend/app/worker/main.py"
s = open(p, encoding="utf-8").read()
old = 'JOBS: tuple[str, ...] = ("notificaciones.scheduler", "notificaciones.sender")'
new = 'JOBS: tuple[str, ...] = ("notificaciones.scheduler", "notificaciones.sender", "lista_espera.expiry")'
assert old in s
s = s.replace(old, new)
open(p, "w", encoding="utf-8").write(s)
print("ok")
