from sentence_transformers import CrossEncoder
from app.config import xencoder_settings
from app.db_types import FusedResult, RerankedResult


class ReRanker:
    """
    ReRanker class for re-ranking

    """

    def __init__(self):
        self.model = CrossEncoder(xencoder_settings.cross_encoder_model)
        self.top_k = xencoder_settings.cross_encoder_top_k

    def rerank_list(
        self, query: str, data_list: list[FusedResult]
    ) -> list[RerankedResult]:
        """Re-scores each chunk with the cross-encoder and returns them
        sorted best-first, recording each chunk's rank before and after
        so a mover from e.g. RRF rank 40 to rerank rank 2 is visible."""

        rerank_scores = self.model.predict(
            [(query, fused.chunk.chunk_text) for fused in data_list]
        )

        scored = [
            (fused, original_rank, score)
            for original_rank, (fused, score) in enumerate(
                zip(data_list, rerank_scores), start=1
            )
        ]
        scored.sort(key=lambda item: item[2], reverse=True)

        return [
            RerankedResult(
                chunk=fused.chunk,
                original_rank=original_rank,
                rrf_score=fused.rrf_score,
                new_rank=new_rank,
                rerank_score=score,
            )
            for new_rank, (fused, original_rank, score) in enumerate(scored, start=1)
        ][: self.top_k]


# Replace with lazy eval
# cross_encoder = ReRanker()

_cross_encoder: ReRanker | None = None


def get_cross_encoder():
    global _cross_encoder
    if _cross_encoder is None:
        _cross_encoder = ReRanker()
    return _cross_encoder


# def rerank(
#     self,
#     query: str,
#     rrf_ranks: List[int],
#     retrieved_corpus_info: List[Corpus_Retrieval],
#     top_k: int,
# ) -> List[Tuple[int, str, Corpus_Retrieval]]:
#     """
#     Re-rank the documents using the CrossEncoder model.

#     Args:
#         query (str): The query string.
#         rrf_ranks (List[int]): The list of document indices from reciprocal rank fusion process from best to worst.
#         retrieved_corpus_info (List[Corpus_Retrieval]): The list of full data (chunk_id, ner_entities, norm_doc, compressed_doc, metadata) from the database for document access.
#         top_k (Settings.CROSS_ENCODER_TOP_K): The number of documents to return, or 0 if whole list is to be returned.
#     Returns:
#         List[Tuple[int, str, Corpus_Retrieval]]: The list of tuples containing the document, the document id, and the full data from the database.
#     """
#     rerank_scores: List[float] = self.model.predict(
#         [(query, retrieved_corpus_info[x]["norm_doc"]) for x in rrf_ranks]
#     ).tolist()

#     sorted_reranks = sorted(
#         zip(rrf_ranks, rerank_scores), key=lambda x: x[1], reverse=True
#     )

#     return_reranks = sorted_reranks if top_k == 0 else sorted_reranks[:top_k]

#     return [
#         (x[0], retrieved_corpus_info[x[0]]["norm_doc"], retrieved_corpus_info[x[0]])
#         for x in return_reranks
#     ]
