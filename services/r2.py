from pathlib import Path
from typing import Any, Iterable
import hashlib
import os
import boto3
from botocore.exceptions import ClientError


class S3Service:
    """
    Servicio de gestión y sincronización de archivos S3.

    Compatible con AWS S3 y servicios S3 compatibles,
    como Cloudflare R2.
    """

    def __init__(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        region_name: str = "us-east-1",
        bucket_name: str | None = None,
        endpoint_url: str | None = None,
    ):
        self.bucket_name = bucket_name

        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
            endpoint_url=endpoint_url,
        )

    # --------------------------------------------------
    # UTILIDADES
    # --------------------------------------------------

    def _get_bucket(self, bucket: str | None = None) -> str:
        bucket = bucket or self.bucket_name

        if not bucket:
            raise ValueError("No se ha especificado un bucket.")

        return bucket

    def _handle_error(self, error: ClientError) -> None:
        code = error.response["Error"]["Code"]
        message = error.response["Error"].get("Message", "")

        raise RuntimeError(
            f"Error S3 [{code}]: {message}"
        ) from error

    # --------------------------------------------------
    # ARCHIVOS INDIVIDUALES
    # --------------------------------------------------

    def upload_file(
        self,
        local_path: str | Path,
        key: str,
        bucket: str | None = None,
        extra_args: dict[str, Any] | None = None,
    ) -> bool:
        """Sube un archivo local a S3."""

        bucket = self._get_bucket(bucket)
        local_path = Path(local_path)

        if not local_path.is_file():
            raise FileNotFoundError(local_path)

        try:
            self.s3_client.upload_file(
                str(local_path),
                bucket,
                key,
                ExtraArgs=extra_args,
            )
            return True

        except ClientError as error:
            self._handle_error(error)

    def download_file(
        self,
        key: str,
        local_path: str | Path,
        bucket: str | None = None,
    ) -> bool:
        """Descarga un archivo de S3."""

        bucket = self._get_bucket(bucket)
        local_path = Path(local_path)

        local_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            self.s3_client.download_file(
                bucket,
                key,
                str(local_path),
            )
            return True

        except ClientError as error:
            self._handle_error(error)

    def read_file(
        self,
        key: str,
        bucket: str | None = None,
    ) -> bytes:
        """Lee un archivo remoto y devuelve sus bytes."""

        bucket = self._get_bucket(bucket)

        try:
            response = self.s3_client.get_object(
                Bucket=bucket,
                Key=key,
            )

            return response["Body"].read()

        except ClientError as error:
            self._handle_error(error)

    def read_text(
        self,
        key: str,
        bucket: str | None = None,
        encoding: str = "utf-8",
    ) -> str:
        """Lee un archivo remoto como texto."""

        return self.read_file(key, bucket).decode(encoding)

    def write_file(
        self,
        key: str,
        content: bytes | str,
        bucket: str | None = None,
        content_type: str | None = None,
    ) -> bool:
        """Crea o sobrescribe un archivo remoto."""

        bucket = self._get_bucket(bucket)

        if isinstance(content, str):
            content = content.encode("utf-8")

        args = {}

        if content_type:
            args["ContentType"] = content_type

        try:
            self.s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=content,
                **args,
            )
            return True

        except ClientError as error:
            self._handle_error(error)

    # --------------------------------------------------
    # EDICIÓN Y ORGANIZACIÓN
    # --------------------------------------------------

    def delete_file(
        self,
        key: str,
        bucket: str | None = None,
    ) -> bool:
        """Elimina un archivo remoto."""

        bucket = self._get_bucket(bucket)

        try:
            self.s3_client.delete_object(
                Bucket=bucket,
                Key=key,
            )
            return True

        except ClientError as error:
            self._handle_error(error)

    def copy_file(
        self,
        source_key: str,
        destination_key: str,
        bucket: str | None = None,
    ) -> bool:
        """Copia un archivo dentro del mismo bucket."""

        bucket = self._get_bucket(bucket)

        try:
            self.s3_client.copy_object(
                Bucket=bucket,
                Key=destination_key,
                CopySource={
                    "Bucket": bucket,
                    "Key": source_key,
                },
            )
            return True

        except ClientError as error:
            self._handle_error(error)

    def move_file(
        self,
        source_key: str,
        destination_key: str,
        bucket: str | None = None,
    ) -> bool:
        """Mueve un archivo mediante copia y eliminación."""

        self.copy_file(
            source_key,
            destination_key,
            bucket,
        )

        self.delete_file(
            source_key,
            bucket,
        )

        return True

    def file_exists(
        self,
        key: str,
        bucket: str | None = None,
    ) -> bool:
        """Comprueba si existe un archivo."""

        bucket = self._get_bucket(bucket)

        try:
            self.s3_client.head_object(
                Bucket=bucket,
                Key=key,
            )
            return True

        except ClientError as error:
            code = error.response["Error"]["Code"]

            if code in ("404", "NoSuchKey", "NotFound"):
                return False

            self._handle_error(error)

    def get_metadata(
        self,
        key: str,
        bucket: str | None = None,
    ) -> dict[str, Any]:
        """Obtiene metadatos de un archivo."""

        bucket = self._get_bucket(bucket)

        try:
            return self.s3_client.head_object(
                Bucket=bucket,
                Key=key,
            )

        except ClientError as error:
            self._handle_error(error)

    # --------------------------------------------------
    # LISTADO
    # --------------------------------------------------

    def list_files(
        self,
        prefix: str = "",
        bucket: str | None = None,
    ) -> list[dict[str, Any]]:
        """Lista todos los archivos de un prefijo."""

        bucket = self._get_bucket(bucket)

        try:
            paginator = self.s3_client.get_paginator(
                "list_objects_v2"
            )

            files = []

            for page in paginator.paginate(
                Bucket=bucket,
                Prefix=prefix,
            ):
                files.extend(page.get("Contents", []))

            return files

        except ClientError as error:
            self._handle_error(error)

    # --------------------------------------------------
    # SINCRONIZACIÓN MÚLTIPLE
    # --------------------------------------------------

    def upload_files(
        self,
        files: Iterable[str | Path],
        prefix: str = "",
        bucket: str | None = None,
    ) -> dict[str, Any]:
        """
        Sube múltiples archivos.

        Conserva el nombre de cada archivo dentro del prefijo.
        """

        bucket = self._get_bucket(bucket)

        results = {
            "uploaded": [],
            "failed": [],
        }

        for file_path in files:
            file_path = Path(file_path)

            key = f"{prefix.rstrip('/')}/{file_path.name}"
            key = key.lstrip("/")

            try:
                self.upload_file(
                    file_path,
                    key,
                    bucket,
                )

                results["uploaded"].append(key)

            except Exception as error:
                results["failed"].append({
                    "file": str(file_path),
                    "error": str(error),
                })

        return results

    def download_files(
        self,
        prefix: str,
        local_dir: str | Path,
        bucket: str | None = None,
    ) -> dict[str, Any]:
        """
        Descarga todos los archivos de un prefijo.

        Conserva la estructura de carpetas remota.
        """

        bucket = self._get_bucket(bucket)
        local_dir = Path(local_dir)

        results = {
            "downloaded": [],
            "failed": [],
        }

        files = self.list_files(prefix, bucket)

        for file_info in files:
            key = file_info["Key"]

            if key.endswith("/"):
                continue

            relative_path = key[len(prefix):].lstrip("/")
            local_path = local_dir / relative_path

            try:
                self.download_file(
                    key,
                    local_path,
                    bucket,
                )

                results["downloaded"].append(key)

            except Exception as error:
                results["failed"].append({
                    "key": key,
                    "error": str(error),
                })

        return results

    # --------------------------------------------------
    # SINCRONIZACIÓN DE CARPETAS
    # --------------------------------------------------

    def sync_to_s3(
        self,
        local_dir: str | Path,
        prefix: str = "",
        bucket: str | None = None,
    ) -> dict[str, Any]:
        """
        Sube el contenido de una carpeta completa.

        Conserva la estructura de directorios.
        """

        local_dir = Path(local_dir)
        bucket = self._get_bucket(bucket)

        results = {
            "uploaded": [],
            "failed": [],
        }

        for file_path in local_dir.rglob("*"):

            if not file_path.is_file():
                continue

            relative_path = file_path.relative_to(
                local_dir
            ).as_posix()

            key = f"{prefix.rstrip('/')}/{relative_path}"
            key = key.lstrip("/")

            try:
                self.upload_file(
                    file_path,
                    key,
                    bucket,
                )

                results["uploaded"].append(key)

            except Exception as error:
                results["failed"].append({
                    "file": str(file_path),
                    "error": str(error),
                })

        return results

    def sync_from_s3(
        self,
        prefix: str,
        local_dir: str | Path,
        bucket: str | None = None,
    ) -> dict[str, Any]:
        """
        Descarga el contenido de un prefijo completo.

        Conserva la estructura de directorios.
        """

        return self.download_files(
            prefix=prefix,
            local_dir=local_dir,
            bucket=bucket,
        )

    # --------------------------------------------------
    # COMPARACIÓN E INTEGRIDAD
    # --------------------------------------------------

    @staticmethod
    def calculate_hash(
        file_path: str | Path,
        algorithm: str = "sha256",
    ) -> str:
        """Calcula el hash de un archivo local."""

        hasher = hashlib.new(algorithm)

        with open(file_path, "rb") as file:
            for chunk in iter(
                lambda: file.read(1024 * 1024),
                b"",
            ):
                hasher.update(chunk)

        return hasher.hexdigest()

    def compare_file_size(
        self,
        local_path: str | Path,
        key: str,
        bucket: str | None = None,
    ) -> bool:
        """Compara el tamaño local y remoto."""

        local_size = Path(local_path).stat().st_size

        metadata = self.get_metadata(
            key,
            bucket,
        )

        return local_size == metadata["ContentLength"]
