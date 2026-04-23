import os
import shutil
from typing import BinaryIO
from pathlib import Path

class LocalStorage:
    def __init__(self, base_path: str = "storage"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)

    def save_file(self, tenant_id: str, file_name: str, file_data: BinaryIO) -> str:
        """
        Saves a file to a tenant-specific directory and returns the relative path.
        """
        # path: storage/tenants/{tenant_id}/documents/{file_name}
        tenant_dir = self.base_path / "tenants" / tenant_id / "documents"
        tenant_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = tenant_dir / file_name
        
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file_data, buffer)
            
        # Return relative path for database storage
        return str(file_path.relative_to(self.base_path))

    def get_file_path(self, relative_path: str) -> str:
        return str(self.base_path / relative_path)

storage_service = LocalStorage()
