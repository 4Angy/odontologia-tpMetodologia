
p = "backend/app/main.py"
s = open(p, encoding="utf-8").read()

old_import = "from app.modules.notificaciones.router import router as notificaciones_router"
new_import = old_import + "\nfrom app.modules.lista_espera.router import router as lista_espera_router"
assert old_import in s
s = s.replace(old_import, new_import)

old_include = "    app.include_router(notificaciones_router)\n    return app"
new_include = "    app.include_router(notificaciones_router)\n    app.include_router(lista_espera_router)\n    return app"
assert old_include in s
s = s.replace(old_include, new_include)

open(p, "w", encoding="utf-8").write(s)
print("ok")
