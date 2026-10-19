import os
import shutil
from typing import BinaryIO
from pathlib import Path
import re
import asyncio
import hashlib
import tempfile

class LocalStorage:
    def __init__(self, base_path: str = "storage"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True, mode=0o700)

    def original_path(self, organization_id: str, collection_id: str, document_id: str, revision_id: str) -> Path:
        """Resolve server-owned identities, never original filenames or bearer URLs."""
        for value in (organization_id, collection_id, document_id, revision_id):
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
                raise ValueError("Invalid private object identity")
        root = self.base_path.resolve()
        path = root / "organizations" / organization_id / "collections" / collection_id / "documents" / document_id / "revisions" / revision_id / "original"
        if not path.resolve().is_relative_to(root):
            raise ValueError("Private object escaped storage namespace")
        return path

    async def save_original(self, path: Path, stream, size: int, checksum: str) -> None:
        """Bound and hash raw bytes; atomically create an original without overwrite."""
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, temporary = tempfile.mkstemp(prefix=".upload-", dir=path.parent)
        received, digest = 0, hashlib.sha256()
        try:
            with os.fdopen(fd, "wb") as target:
                async with asyncio.timeout(120):
                    async for chunk in stream:
                        received += len(chunk)
                        if received > size:
                            raise ValueError("original_size_mismatch")
                        digest.update(chunk)
                        await asyncio.to_thread(target.write, chunk)
                await asyncio.to_thread(target.flush)
                await asyncio.to_thread(os.fsync, target.fileno())
            if received != size or digest.hexdigest() != checksum:
                raise ValueError("original_checksum_or_size_mismatch")
            os.link(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def validate_original(self, path: Path, size: int, checksum: str) -> None:
        if path.is_symlink() or not path.is_file() or path.stat().st_size != size:
            raise ValueError("original_size_mismatch")
        with path.open("rb") as original:
            if hashlib.file_digest(original, "sha256").hexdigest() != checksum:
                raise ValueError("original_checksum_mismatch")

    def save_file(self, organization_id: str, file_name: str, file_data: BinaryIO) -> str:
        """
        Saves a file to an organization-specific directory and returns the relative path.
        """
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", organization_id):
            raise ValueError("Invalid organization identifier")
        safe_name = Path(file_name).name
        if safe_name != file_name or safe_name in {"", ".", ".."}:
            raise ValueError("Invalid file name")

        # path: storage/organizations/{organization_id}/documents/{file_name}
        organization_dir = self.base_path / "organizations" / organization_id / "documents"
        organization_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = (organization_dir / safe_name).resolve()
        if self.base_path.resolve() not in file_path.parents:
            raise ValueError("Storage path escaped base directory")
        
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file_data, buffer)
            
        # Return relative path for database storage
        return str(file_path.relative_to(self.base_path))

    def get_file_path(self, relative_path: str) -> str:
        file_path = (self.base_path.resolve() / relative_path).resolve()
        if file_path != self.base_path.resolve() and self.base_path.resolve() not in file_path.parents:
            raise ValueError("Storage path escaped base directory")
        return str(file_path)

    def delete_revision_storage(
        self, organization_id: str, collection_id: str, document_id: str, revision_id: str
    ) -> None:
        """Purge private revision directory and original file."""
        try:
            original = self.original_path(
                organization_id, collection_id, document_id, revision_id
            )
            revision_dir = original.parent
            if revision_dir.is_dir():
                shutil.rmtree(revision_dir, ignore_errors=True)
        except Exception:
            pass

    def delete_document_storage(
        self, organization_id: str, collection_id: str, document_id: str
    ) -> None:
        """Purge private document directory containing all revisions and artifacts."""
        for value in (organization_id, collection_id, document_id):
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
                raise ValueError("Invalid private object identity")
        root = self.base_path.resolve()
        path = (
            root
            / "organizations"
            / organization_id
            / "collections"
            / collection_id
            / "documents"
            / document_id
        )
        if not path.resolve().is_relative_to(root):
            raise ValueError("Private object escaped storage namespace")
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)


storage_service = LocalStorage(os.getenv("ASILA_STORAGE_ROOT", "storage"))
