# Runbook: rotación manual de secretos (v1)

## Secretos involucrados
- `JWT_SECRET`
- `WHATSAPP_API_TOKEN`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET`
- `MP_ACCESS_TOKEN`, `MP_WEBHOOK_SECRET`
- `SMTP_URL`
- `ATTACHMENTS_S3_ACCESS_KEY_ID`, `ATTACHMENTS_S3_SECRET_ACCESS_KEY`

## Procedimiento
1. Generar el nuevo secreto (ej. `openssl rand -hex 32`).
2. Actualizar la variable en el entorno del deploy (`.env` o secret manager).
3. Reiniciar el contenedor `api` (y `worker` si aplica).
4. Verificar `/health/ready` en verde.
5. Invalidar tokens existentes si se rotó `JWT_SECRET` (los usuarios deberán re-loguearse).

## Notas
- La rotación es manual en v1; no hay automatización.
- No commitear secretos al repo (R12).