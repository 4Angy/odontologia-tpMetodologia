from __future__ import annotations

from typing import Protocol

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException, Request

from app.core.config import ConfigError, Settings, get_settings

PRESIGNED_URL_TTL_SECONDS = 300


class AttachmentStorageError(RuntimeError):
    pass


class AttachmentStorage(Protocol):
    def put(self, key: str, content: bytes, content_type: str) -> None: ...

    def delete(self, key: str) -> None: ...

    def presign_get(self, key: str, filename: str) -> str: ...


class S3AttachmentStorage:
    def __init__(self, settings: Settings) -> None:
        if not settings.attachments_s3_bucket:
            raise AttachmentStorageError(
                "Falta configurar ATTACHMENTS_S3_BUCKET para almacenar adjuntos clínicos."
            )
        options: dict[str, str] = {"region_name": settings.attachments_s3_region}
        if settings.attachments_s3_endpoint_url:
            options["endpoint_url"] = settings.attachments_s3_endpoint_url
        if settings.attachments_s3_access_key_id:
            options["aws_access_key_id"] = (
                settings.attachments_s3_access_key_id.get_secret_value()
            )
        if settings.attachments_s3_secret_access_key:
            options["aws_secret_access_key"] = (
                settings.attachments_s3_secret_access_key.get_secret_value()
            )
        self._client = boto3.client("s3", **options)
        self._bucket = settings.attachments_s3_bucket

    def put(self, key: str, content: bytes, content_type: str) -> None:
        try:
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=content,
                ContentType=content_type,
                ServerSideEncryption="AES256",
            )
        except (BotoCoreError, ClientError) as exc:
            raise AttachmentStorageError("No se pudo guardar el adjunto privado.") from exc

    def delete(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except (BotoCoreError, ClientError) as exc:
            raise AttachmentStorageError("No se pudo limpiar el adjunto privado.") from exc

    def presign_get(self, key: str, filename: str) -> str:
        try:
            return str(
                self._client.generate_presigned_url(
                    "get_object",
                    Params={
                        "Bucket": self._bucket,
                        "Key": key,
                        "ResponseContentDisposition": f'attachment; filename="{filename}"',
                    },
                    ExpiresIn=PRESIGNED_URL_TTL_SECONDS,
                )
            )
        except (BotoCoreError, ClientError) as exc:
            raise AttachmentStorageError("No se pudo generar el enlace temporal.") from exc


def get_attachment_storage(request: Request) -> AttachmentStorage:
    storage = getattr(request.app.state, "attachment_storage", None)
    if storage is not None:
        return storage
    try:
        configured = S3AttachmentStorage(get_settings())
    except (AttachmentStorageError, ConfigError) as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "RN-PA-03",
                "message": "El almacenamiento privado de adjuntos no está disponible.",
            },
        ) from exc
    request.app.state.attachment_storage = configured
    return configured


__all__ = [
    "AttachmentStorage",
    "AttachmentStorageError",
    "PRESIGNED_URL_TTL_SECONDS",
    "get_attachment_storage",
]
