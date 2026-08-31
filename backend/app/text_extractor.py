"""Module for extracting original text from transformed .txt or .md files in uploads/markdowns/"""

from pathlib import Path

from app.schemas import ContextLoadChunk
from app.db_types import ChunkRow
from app.config import MARKDOWN_DIR


def extract_original_text(
    doc_reference: tuple[str, list[ChunkRow]],
) -> ContextLoadChunk:
    """Given a file name and list of tuples of start/stop indices, return list of tuples of extracted context"""

    doc = doc_reference[0]
    rows = doc_reference[1]

    file = Path(MARKDOWN_DIR / doc).read_text()
    start_db_entry_id = rows[0].entry
    end_db_entry_id = rows[-1].entry
    start = rows[0].start_index
    end = rows[-1].end_index

    chunk = ContextLoadChunk(
        document_id=doc,
        start_db_entry_id=start_db_entry_id,
        end_db_entry_id=end_db_entry_id,
        start_char=start,
        end_char=end,
        content=file[start:end],
    )

    return chunk
