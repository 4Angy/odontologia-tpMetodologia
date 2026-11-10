# Guía de onboarding en el día (v1)

1. Alta del consultorio: crear tenant (slug kebab-case) y usuario dueño.
2. Ejecutar seed demo o importar pacientes por CSV (`POST /pacientes/import-csv`).
3. Configurar profesionales, prestaciones y horarios semanales.
4. Configurar antelación de cancelación (default 24h) y seña MP (opcional).
5. Compartir link público `/r/:slug` por WhatsApp/redes.
6. Probar reserva pública sin tarjeta (turno `pendiente_confirmacion`).
7. Registrar un cobro de prueba y cerrar caja del día.