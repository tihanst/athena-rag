"""In-memory store standing in for the future SQLite-backed corpus.

Replace this with real persistence once the RAG ingestion pipeline is built.
"""

from app.schemas import FileRecord

files: dict[str, FileRecord] = {}
