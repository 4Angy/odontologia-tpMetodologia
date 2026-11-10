# Checklist de lanzamiento (C-13)

## Métricas de éxito (01_vision_y_objetivos.md)
- [ ] Tasa de ausentismo: instrumentación base por tenant.
- [ ] Agenda diaria < 5 min: validado con recepcionista real.
- [ ] Cobro de señas > 50% donde se exige: medición activa.
- [ ] Adopción papel→sistema: 100% turnos cargados a 30 días.
- [ ] Time-to-value: primer turno < 24h post-alta.
- [ ] Transparencia: precio ARS + costo WhatsApp visibles in-app.

## Seguridad y auditoría
- [ ] Rate limit en rutas públicas y login verificado.
- [ ] Security headers presentes (HSTS, X-Frame-Options, etc.).
- [ ] `/auditoria` accesible solo por dueño.
- [ ] Backups Postgres diarios configurados.
- [ ] Rotación de secretos documentada y probada.

## Seed demo
- [ ] `SEED_DEMO=true` levanta tenant operable.
- [ ] Onboarding en el día validado.