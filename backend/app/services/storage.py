"""T3 – StorageAdapter + LocalFSAdapter.

Provides atomic writes, streaming reads, and a deterministic path builder
that follows the specification directory layout.

    DATA_ROOT/
    ├── originals/{doc_id}/original.pdf
    ├── pages/{doc_id}/v{version_id}/{page_no}.png  /  {page_no}_thumb.jpg
    ├── ocr/{doc_id}/v{version_id}/{page_no}.json  /  pages.jsonl
    ├── artifacts/{doc_id}/v{version_id}/tables.json  metrics.json  llm_output.json
    ├── exports/{export_id}/export.docx  export.pdf
    └── uploads/{upload_id}/parts/part_0 …
"""

from __future__ import annotations

import abc
import os
import shutil
import tempfile
from pathlib import Path
from typing import BinaryIO

from app.core.config import settings


class StorageAdapter(abc.ABC):
    """Abstract storage interface (LocalFS now, S3 reserved)."""

    @abc.abstractmethod
    def write(self, rel_path: str, data: bytes | BinaryIO) -> str: ...

    @abc.abstractmethod
    def read(self, rel_path: str) -> bytes: ...

    @abc.abstractmethod
    def read_stream(self, rel_path: str) -> BinaryIO: ...

    @abc.abstractmethod
    def exists(self, rel_path: str) -> bool: ...

    @abc.abstractmethod
    def delete(self, rel_path: str) -> None: ...

    @abc.abstractmethod
    def abs_path(self, rel_path: str) -> str: ...


class LocalFSAdapter(StorageAdapter):
    """Filesystem-backed storage with atomic writes."""

    def __init__(self, root: str | None = None):
        self._root = Path(root or settings.DATA_ROOT).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    # ── write (atomic: write to tmp then rename) ────────
    def write(self, rel_path: str, data: bytes | BinaryIO) -> str:
        target = self._root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)

        fd, tmp = tempfile.mkstemp(dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as f:
                if isinstance(data, bytes):
                    f.write(data)
                else:
                    shutil.copyfileobj(data, f)
            os.replace(tmp, target)
        except Exception:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
        return str(target)

    def read(self, rel_path: str) -> bytes:
        return (self._root / rel_path).read_bytes()

    def read_stream(self, rel_path: str) -> BinaryIO:
        return open(self._root / rel_path, "rb")

    def exists(self, rel_path: str) -> bool:
        return (self._root / rel_path).exists()

    def delete(self, rel_path: str) -> None:
        p = self._root / rel_path
        if p.is_file():
            p.unlink()
        elif p.is_dir():
            shutil.rmtree(p)

    def abs_path(self, rel_path: str) -> str:
        return str((self._root / rel_path).resolve())


# ── Path builder helpers ─────────────────────────────────
class StoragePaths:
    """Deterministic relative path builder."""

    @staticmethod
    def original_pdf(doc_id: str) -> str:
        return f"originals/{doc_id}/original.pdf"

    @staticmethod
    def page_image(doc_id: str, version_id: str, page_no: int) -> str:
        return f"pages/{doc_id}/v{version_id}/{page_no}.png"

    @staticmethod
    def page_thumb(doc_id: str, version_id: str, page_no: int) -> str:
        return f"pages/{doc_id}/v{version_id}/{page_no}_thumb.jpg"

    @staticmethod
    def ocr_page_json(doc_id: str, version_id: str, page_no: int) -> str:
        return f"ocr/{doc_id}/v{version_id}/{page_no}.json"

    @staticmethod
    def ocr_pages_jsonl(doc_id: str, version_id: str) -> str:
        return f"ocr/{doc_id}/v{version_id}/pages.jsonl"

    @staticmethod
    def artifact(doc_id: str, version_id: str, name: str) -> str:
        return f"artifacts/{doc_id}/v{version_id}/{name}"

    @staticmethod
    def export_file(export_id: str, ext: str) -> str:
        return f"exports/{export_id}/export.{ext}"

    @staticmethod
    def upload_part(upload_id: str, part_no: int) -> str:
        return f"uploads/{upload_id}/parts/part_{part_no}"


# ── Singleton ────────────────────────────────────────────
def get_storage() -> StorageAdapter:
    """Factory – returns the configured backend (currently only localfs)."""
    return LocalFSAdapter()
