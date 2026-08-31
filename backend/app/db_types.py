from typing import NamedTuple


class ChunkRow(NamedTuple):
    """One row of the `uploads` table, in column order."""

    entry: int
    start_index: int
    end_index: int
    document_chunk_index: int
    chunk_text: str
    source_document_id: str
    document_last_chunk_index: int


class ScoredChunkRow(NamedTuple):
    """A ChunkRow plus the single-engine score it was retrieved with
    (BM25 for lexical hits, cosine distance for semantic hits)."""

    entry: int
    start_index: int
    end_index: int
    document_chunk_index: int
    chunk_text: str
    source_document_id: str
    document_last_chunk_index: int
    score: float


class FusedResult(NamedTuple):
    """A chunk plus its Reciprocal Rank Fusion score across search engines."""

    chunk: ScoredChunkRow
    rrf_score: float


class RerankedResult(NamedTuple):
    """A chunk plus its position/score before and after re-ranking, so a
    reader can tell at a glance whether the cross-encoder moved it up,
    down, or left it in place. 1-based: rank 1 is the best result."""

    chunk: ScoredChunkRow
    original_rank: int
    rrf_score: float
    new_rank: int
    rerank_score: float
