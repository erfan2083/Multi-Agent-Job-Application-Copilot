from pathlib import Path
from core.config import settings


class StorageService:
    def write_text(self, subdir: str, filename: str, content: str) -> str:
        path = settings.data_dir / subdir
        path.mkdir(parents=True, exist_ok=True)
        full = path / filename
        full.write_text(content, encoding="utf-8")
        return str(full)


storage_service = StorageService()
