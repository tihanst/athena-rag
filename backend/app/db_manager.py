from contextlib import contextmanager
from pathlib import Path
from numpy.typing import NDArray
from numpy import float32

import sqlite3
import sqlite_vec

from langchain_core.documents import Document

from .lex_search import process_lexical_query
from .db_types import ChunkRow, ScoredChunkRow

# Testing
from app.sem_search import embedder
from app.config import MARKDOWN_DIR
# from .sem_search import process_semantic_query

DBFILE_PATH = Path(__file__).parent.parent / "databases"

DBFILE = DBFILE_PATH / "uploads.db"


CREATE_DATABASE = """CREATE TABLE IF NOT EXISTS "uploads"
(
    entry INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    start_index INTEGER NOT NULL,
    end_index INTEGER NOT NULL,
    document_chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    source_document_id NVARCHAR(160),
    document_last_chunk_index INTEGER NOT NULL
);
"""

CREATE_VECTOR_TABLE = """CREATE VIRTUAL TABLE IF NOT EXISTS uploads_vec
    using vec0(embedding float[1024] distance_metric=cosine
    );
"""

CREATE_FTS5_TABLE = """CREATE VIRTUAL TABLE IF NOT EXISTS uploads_fts
    USING fts5(
        chunk_text,
        content='uploads',
        content_rowid='entry',
        tokenize='porter unicode61'
    );
    """


# Replace by more comprehensive
# FTS_TABLE_TRIGGER = """CREATE TRIGGER uploads_ai
#     AFTER INSERT ON uploads
#     BEGIN
#         INSERT INTO uploads_fts(rowid, chunk_text)
#         VALUES (new.entry, new.chunk_text);
#     END;"""

FTS_TABLE_TRIGGERS = """CREATE TRIGGER IF NOT EXISTS uploads_ai
AFTER INSERT ON uploads
BEGIN
    INSERT INTO uploads_fts(rowid, chunk_text)
    VALUES (new.entry, new.chunk_text);
END;

CREATE TRIGGER IF NOT EXISTS uploads_ad
AFTER DELETE ON uploads
BEGIN
    INSERT INTO uploads_fts(uploads_fts, rowid, chunk_text)
    VALUES ('delete', old.entry, old.chunk_text);
END;

CREATE TRIGGER IF NOT EXISTS uploads_au
AFTER UPDATE OF chunk_text ON uploads
BEGIN
    INSERT INTO uploads_fts(uploads_fts, rowid, chunk_text)
    VALUES ('delete', old.entry, old.chunk_text);
    INSERT INTO uploads_fts(rowid, chunk_text)
    VALUES (new.entry, new.chunk_text);
END;

CREATE TRIGGER IF NOT EXISTS uploads_vec_ad
AFTER DELETE ON uploads
BEGIN
    DELETE FROM uploads_vec
    WHERE rowid = old.entry;
END;
"""

FTS_SEARCH_QUERY = """SELECT 
    u.*,
    bm25(uploads_fts) as score
    FROM uploads_fts as fts
    join uploads as u on u.entry = fts.rowid
    WHERE uploads_fts MATCH ?
    ORDER BY score  
    LIMIT ?;
    """  ## Note sqlite FTS5 bm25 scores lower (more negative) as better so keep ORDER BY as-is

SEMANTIC_SEARCH_QUERY = """
    SELECT 
    u.*, v.distance 
    FROM uploads as u 
    JOIN uploads_vec as v ON u.entry = v.rowid 
    WHERE v.embedding MATCH ? AND k = ? 
    ORDER BY v.distance;
    """

DATABASE_SOURCE_DOCS_SUMMARY = """
    SELECT 
    source_document_id 
    FROM uploads
    GROUP BY source_document_id;
    """


def init_db():
    with get_connection() as conn:
        # conn = sqlite3.connect(DBFILE.resolve())
        conn.execute(CREATE_DATABASE)
        conn.execute(CREATE_FTS5_TABLE)
        conn.executescript(FTS_TABLE_TRIGGERS)
        conn.execute(CREATE_VECTOR_TABLE)
        conn.commit()
        # conn.close()


@contextmanager
def get_connection():
    conn = sqlite3.connect(DBFILE.resolve())
    try:
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def process_chunks(chunks: list[Document], embeddings: NDArray[float32]):
    ## create a list of tuples to pass in to executemany("INSERT INTO "table name" VALUES (NULL, ?, ?, ..,?)", list_of_tuples)
    with get_connection() as conn:
        next_entry = conn.execute(
            "SELECT COALESCE(MAX(entry), 0) + 1 FROM uploads"
        ).fetchone()[0]

    upload_rows = []
    vector_rows = []

    assert len(chunks) == len(embeddings), (
        f"In process_chunks, embeddings (len={len(embeddings)} not equal in length to chunks (len={len(chunks)})"
    )

    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        entry = next_entry + i

        upload_rows.append((entry, chunk))
        vector_rows.append((entry, sqlite_vec.serialize_float32(embedding)))

    extracted_chunks = [
        (
            x[0],
            x[1].metadata["start_index"],
            x[1].metadata["end_index"],
            x[1].page_content,
            x[1].metadata["source_document_id"],
            x[1].metadata["document_chunk_index"],
            x[1].metadata["document_last_chunk_index"],
        )
        for x in upload_rows
    ]

    with get_connection() as conn:
        try:
            load_string = """INSERT INTO uploads 
            (
                entry,
                start_index,
                end_index,
                chunk_text,
                source_document_id,
                document_chunk_index,
                document_last_chunk_index
            )
            VALUES
            (?, ?, ?, ?, ?, ?, ?)
            """

            conn.executemany(load_string, extracted_chunks)

            conn.executemany(
                """
            INSERT INTO uploads_vec(rowid, embedding)
            VALUES (?, ?)
            """,
                vector_rows,
            )

            conn.commit()
        except Exception:
            conn.rollback()
            raise


def execute_lexical_retrieval(
    queries: dict[str, str], match_limit: int = 100
) -> dict[str, list[ScoredChunkRow]]:
    results: dict[str, list[ScoredChunkRow]] = {}

    with get_connection() as conn:
        for name, search_query in queries.items():
            rows = conn.execute(
                FTS_SEARCH_QUERY,
                (search_query, match_limit),
            ).fetchall()
            results[name] = [ScoredChunkRow(*row) for row in rows]

    return results


def execute_semantic_retrieval(
    query: str, match_limit: int = 100
) -> list[ScoredChunkRow]:
    q = embedder.embed_query(query)

    with get_connection() as conn:
        rows = conn.execute(
            SEMANTIC_SEARCH_QUERY, (sqlite_vec.serialize_float32(q), match_limit)
        ).fetchall()

        return [ScoredChunkRow(*row) for row in rows]


def execute_final_search_retrieval(
    span: tuple[int, int] | tuple[int], document_name: str
) -> list[ChunkRow]:
    """Retrieves all chunk rows within a single contiguous entry span."""

    if len(span) == 1:
        query = """
        SELECT u.* FROM uploads as u
        WHERE u.entry = ? AND u.source_document_id = ?
        ORDER BY u.entry;
        """
        params = (span[0], document_name)
    else:
        start, end = span
        query = """
        SELECT u.* FROM uploads as u
        WHERE u.entry BETWEEN ? AND ? AND u.source_document_id = ?
        ORDER BY u.entry;
        """
        params = (start, end, document_name)

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [ChunkRow(*row) for row in rows]


def query_database_source_documents() -> dict[str, list[str]]:
    with get_connection() as conn:
        sources = conn.execute(DATABASE_SOURCE_DOCS_SUMMARY).fetchall()

    documents = [x[0] for x in sources]

    present_or_not: dict[str, list[str]] = {"exists": [], "missing": []}

    for doc in documents:
        full_filename = Path(MARKDOWN_DIR) / doc
        separator = doc.find("__")
        short_doc = doc[separator + 2 :] if separator != -1 else doc
        if full_filename.exists():
            present_or_not["exists"].append(short_doc)
        else:
            present_or_not["missing"].append(short_doc)

    return present_or_not
    # print(f"Exists or not dict:\n\n{present_or_not}")


def delete_it():
    with get_connection() as conn:
        conn.execute(
            """delete from uploads where source_document_id = 'asdf__chasdf__chumps.pdf';"""
        )
    print("doneit")


if __name__ == "__main__":
    # print(DBFILE.exists())
    # if not DBFILE.exists():
    #     DBFILE.touch
    # print("Initializing ...")
    # init_db()
    # print("done")

    # query = embedder.embed_query(
    #     "How did Shakespear's Antony and Cleopatra achieve supremecy against Hamlet?"
    # )
    # with get_connection() as conn:
    #     rows = conn.execute(
    #         SEMANTIC_SEARCH_QUERY,
    #         (sqlite_vec.serialize_float32(query), 20),
    #     ).fetchall()

    #     for x in rows:
    #         print(f"\n\n{x}\n\n")
    delete_it()
    query_database_source_documents()
