import uuid
from pathlib import Path
from datetime import datetime
import asyncio
import numpy as np

from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document

from fastapi import APIRouter, HTTPException, UploadFile, status

from app.schemas import FileRecord
from app.state import files
from app.config import UPLOAD_DIR, MARKDOWN_DIR

from ..uploader import file_uploader
from ..db_manager import process_chunks, query_database_source_documents
from ..chunker import chunk_text
from ..sem_search import embedder

router = APIRouter(prefix="/api", tags=["files"])

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
        document_text, file_name = await asyncio.to_thread(
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
        document_id=file_name,
    )

    files[file_id] = record

    print(f"---{record.model_dump()}---")
    # print(f"\n\n****{files}***\n\n")

    document = Document(document_text, metadata=record.model_dump())

    chunks = chunk_text(
        [document],
        document_id=record.document_id if record.document_id is not None else "",
    )
    # print(chunks)
    embeddings = embedder.embed_documents([x.page_content for x in chunks])
    embedding_f32 = np.asarray(embeddings, dtype=np.float32)

    process_chunks(chunks=chunks, embeddings=embedding_f32)

    [print(f"\n\n****{chunks[x].page_content}***\n\n") for x in range(3, 5)]

    [print(f"\n\n****{chunks[x].metadata}***\n\n") for x in range(3, 5)]
    print(len(chunks))
    return record


@router.get("/files", response_model=list[FileRecord])
def list_files() -> list[FileRecord]:
    return list(files.values())


@router.get("/files/status", response_model=dict[str, list[str]])
def get_files_status() -> dict[str, list[str]]:
    """Cross-references documents recorded in the database against the
    markdown uploads directory, so files missing on disk (but still
    referenced by the database) can be flagged for re-upload."""
    return query_database_source_documents()


@router.delete("/files/{file_id}", status_code=204)
def delete_file(file_id: str) -> None:
    record = files.pop(file_id, None)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found")

    for match in UPLOAD_DIR.glob(f"{file_id}_*"):
        match.unlink(missing_ok=True)
