from typing import List, Any
from numpy.typing import NDArray
import numpy as np
# from sklearn.metrics.pairwise import cosine_similarity

from FlagEmbedding import BGEM3FlagModel, FlagModel


class BGEEmbedder:
    """Wrapper for BGE-small-en-v1.5 or BGE-M3 dense embeddings."""

    def __init__(self, small: bool = True):
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


embedder = BGEEmbedder(small=False)


if __name__ == "__main__":
    mode = BGEEmbedder(small=False)
