import uuid
from pathlib import Path
from datetime import datetime
import asyncio

from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document

from fastapi import APIRouter, HTTPException, UploadFile, status

from app.schemas import FileRecord
from app.state import files

from ..uploader import file_uploader
from ..chunker import chunk_text

router = APIRouter(prefix="/api", tags=["files"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
MARKDOWN_DIR = UPLOAD_DIR / "markdowns"
MARKDOWN_DIR.mkdir(exist_ok=True)
MAX_PDF_SIZE = 100 * 1024 * 1024

ALLOWED_MIME_TYPES = {
    "application/pdf": "pdf",
    "text/plain": "txt",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/markdown": "md",
}


@router.post("/upload", response_model=FileRecord)
async def upload_file(file: UploadFile) -> FileRecord:
    """Mock ingestion endpoint. Stores the raw file on disk and records its
    metadata in memory; real chunking/embedding will replace this later."""

    if file.size is not None and file.size > MAX_PDF_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File too large. Maximum allowed size is {MAX_PDF_SIZE // (1024 * 1024)}MB",
        )

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {file.content_type}\nSupported types are: {', '.join(ALLOWED_MIME_TYPES.values())}",
        )

    file_id = str(uuid.uuid4())

    contents = await file.read()

    id_based_filename = (
        f"{file_id + '__' + file.filename}"
        if file.filename is not None
        else f"{file_id + '__' + datetime.now().strftime('%d_%m_%Y__%H_%M_%S') + ALLOWED_MIME_TYPES[file.content_type]}"
    )

    dest = UPLOAD_DIR / id_based_filename

    dest.write_bytes(contents)

    # Upload file, offload in case OCR runs so not to block server
    try:
        document_text = await asyncio.to_thread(
            file_uploader, id_based_filename, UPLOAD_DIR, MARKDOWN_DIR
        )
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"'{file.filename}' could not be decoded as UTF-8 text.",
        )

    record = FileRecord(
        id=file_id,
        name=file.filename or "untitled",
        size=len(contents),
        status="ready",
    )

    files[file_id] = record

    print(f"---{record.model_dump()}---")
    # print(f"\n\n****{files}***\n\n")

    document = Document(document_text, matadata=record.model_dump())

    chunks = chunk_text([document], document_id=id_based_filename)
    [print(f"\n\n****{chunks[x].page_content}***\n\n") for x in range(99, 102)]

    [print(f"\n\n****{chunks[x].metadata}***\n\n") for x in range(99, 102)]

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
