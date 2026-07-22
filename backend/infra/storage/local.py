import os
import shutil
from typing import BinaryIO
from pathlib import Path
import re

class LocalStorage:
    def __init__(self, base_path: str = "storage"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)

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

storage_service = LocalStorage()
