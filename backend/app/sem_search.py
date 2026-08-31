from typing import List, Any
from numpy.typing import NDArray
import numpy as np
# from sklearn.metrics.pairwise import cosine_similarity

from FlagEmbedding import BGEM3FlagModel, FlagModel
from app.config import embedder_settings


class BGEEmbedder:
    """Wrapper for BGE-small-en-v1.5 or BGE-M3 dense embeddings."""

    def __init__(self, small: bool = embedder_settings.embedder_use_small):
        self.small = small

        if self.small:
            self.model_name = "BAAI/bge-small-en-v1.5"

            self.model: Any = FlagModel(
                self.model_name,
                query_instruction_for_retrieval=(
                    "Represent this sentence for searching relevant passages:"
                ),
                use_fp16=True,
            )

        else:
            self.model_name = "BAAI/bge-m3"

            self.model: Any = BGEM3FlagModel(
                self.model_name,
                use_fp16=True,
            )

    def embed_documents(
        self,
        texts: List[str],
    ) -> List[List[float]]:
        """Embed document/passages for retrieval.

        Args:
            texts: Document chunks to embed.

        Returns:
            Dense embedding for each document.
        """
        if self.small:
            vecs: NDArray = self.model.encode(texts)

        else:
            vecs: NDArray = self.model.encode(
                texts,
                return_dense=True,
                return_sparse=False,
                return_colbert_vecs=False,
            )["dense_vecs"]

        return vecs.tolist()

    def embed_query(
        self,
        text: str,
    ) -> List[float]:
        """Embed a retrieval query.

        Args:
            text: Query to embed.

        Returns:
            Dense embedding for the query.
        """
        if self.small:
            vec: NDArray = self.model.encode_queries([text])[0]

        else:
            # BGE-M3 does not need to encode query_instruction_for_retrieval
            # for performance unlike small model due to training regime
            vec: NDArray = self.model.encode(
                [text],
                return_dense=True,
                return_sparse=False,
                return_colbert_vecs=False,
            )["dense_vecs"][0]

        return vec.tolist()


# Replace with lazy load
# embedder = BGEEmbedder()

_embedder: BGEEmbedder | None = None


def get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = BGEEmbedder()
    return _embedder


if __name__ == "__main__":
    mode = BGEEmbedder(small=False)
