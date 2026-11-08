# New capability: copy delta to main spec
src = r"C:\Users\Cara Palida\Documents\projects\odontologia-tpMetodologia\openspec\changes\c-10-lista-espera-automatica\specs\agenda\lista-espera\spec.md"
dst = r"C:\Users\Cara Palida\Documents\projects\odontologia-tpMetodologia\openspec\specs\agenda\lista-espera\spec.md"
s = open(src, encoding="utf-8").read()
s = s.replace("## ADDED Requirements", "## Requirements", 1)
open(dst, "w", encoding="utf-8").write(s)
print("created lista-espera main spec")

# Modified capability: append added requirement to main spec
src2 = r"C:\Users\Cara Palida\Documents\projects\odontologia-tpMetodologia\openspec\changes\c-10-lista-espera-automatica\specs\agenda\cancelacion-turno\spec.md"
dst2 = r"C:\Users\Cara Palida\Documents\projects\odontologia-tpMetodologia\openspec\specs\agenda\cancelacion-turno\spec.md"
delta = open(src2, encoding="utf-8").read()
main = open(dst2, encoding="utf-8").read()
# extract added requirement block
import re
m = delta.split("## ADDED Requirements", 1)[1]
# append
main = main.rstrip() + "\n\n" + m.strip() + "\n"
open(dst2, "w", encoding="utf-8").write(main)
print("appended cancelacion-turno delta")
