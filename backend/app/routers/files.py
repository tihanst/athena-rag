import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from app.schemas import FileRecord
from app.state import files

router = APIRouter(prefix="/api", tags=["files"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/upload", response_model=FileRecord)
async def upload_file(file: UploadFile) -> FileRecord:
    """Mock ingestion endpoint. Stores the raw file on disk and records its
    metadata in memory; real chunking/embedding will replace this later."""
    file_id = str(uuid.uuid4())
    contents = await file.read()

    dest = UPLOAD_DIR / f"{file_id}_{file.filename}"
    dest.write_bytes(contents)

    record = FileRecord(
        id=file_id,
        name=file.filename or "untitled",
        size=len(contents),
        status="ready",
    )
    files[file_id] = record
    return record


@router.get("/files", response_model=list[FileRecord])
def list_files() -> list[FileRecord]:
    return list(files.values())


@router.delete("/files/{file_id}", status_code=204)
def delete_file(file_id: str) -> None:
    record = files.pop(file_id, None)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found")

    for match in UPLOAD_DIR.glob(f"{file_id}_*"):
        match.unlink(missing_ok=True)
