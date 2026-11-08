
p = "backend/app/modules/agenda/models.py"
s = open(p, encoding="utf-8").read()

old1 = '''    whatsapp_costo_centavos: Mapped[int] = mapped_column(
        Integer(), nullable=False, default=0, server_default="0"
    )

    __table_args__ = ('''
new1 = '''    whatsapp_costo_centavos: Mapped[int] = mapped_column(
        Integer(), nullable=False, default=0, server_default="0"
    )
    lista_espera_ttl_hs: Mapped[int] = mapped_column(
        Integer(), nullable=False, default=2, server_default="2"
    )

    __table_args__ = ('''
assert old1 in s, "old1 not found"
s = s.replace(old1, new1)

old2 = '''        CheckConstraint(
            "whatsapp_costo_centavos >= 0", name="ck_config_whatsapp_costo_ge_0"
        ),
    )'''
new2 = '''        CheckConstraint(
            "whatsapp_costo_centavos >= 0", name="ck_config_whatsapp_costo_ge_0"
        ),
        CheckConstraint(
            "lista_espera_ttl_hs >= 0", name="ck_config_lista_espera_ttl_ge_0"
        ),
    )'''
assert old2 in s, "old2 not found"
s = s.replace(old2, new2)

open(p, "w", encoding="utf-8").write(s)
print("ok")
