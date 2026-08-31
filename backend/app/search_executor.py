from collections import defaultdict
from collections.abc import Callable, Hashable, Sequence
from typing import Any

from .lex_search import process_lexical_query
from .db_types import ScoredChunkRow, FusedResult

from .sem_search import embedder
from app.db_manager import execute_lexical_retrieval, execute_semantic_retrieval
from app.schemas import SearchTerm, SearchRole, SearchTerms


mock_data7 = {
    "terms": SearchTerms(
        terms=[
            SearchTerm(
                text="Q2 slide deck",
                role=SearchRole.SOURCE_REFERENCE,
                is_phrase=True,
                variants=[
                    "Q2 earnings presentation",
                    "Q2 investor deck",
                    "second quarter slide deck",
                ],
            ),
            SearchTerm(
                text="new manufacturing lines",
                role=SearchRole.ESSENTIAL,
                is_phrase=True,
                variants=[
                    "new production lines",
                    "new manufacturing facilities",
                    "new assembly lines",
                ],
            ),
            SearchTerm(
                text="robotics",
                role=SearchRole.IMPORTANT,
                is_phrase=False,
                variants=["robots", "robotic systems", "automation"],
            ),
            SearchTerm(
                text="autos",
                role=SearchRole.IMPORTANT,
                is_phrase=False,
                variants=["automotive", "automobile", "car manufacturing"],
            ),
        ]
    )
}

mock_data8 = {
    "terms": SearchTerms(
        terms=[
            SearchTerm(
                text="Q2 slide deck",
                role=SearchRole.SOURCE_REFERENCE,
                is_phrase=True,
                variants=[
                    "Q2 presentation",
                    "Q2 investor presentation",
                    "second quarter slide deck",
                ],
            ),
            SearchTerm(
                text="decommissioning new manufacturing lines",
                role=SearchRole.ESSENTIAL,
                is_phrase=False,
                variants=[
                    "decommissioning manufacturing lines",
                    "decommissioning production lines",
                    "shutting down new manufacturing lines",
                ],
            ),
            SearchTerm(
                text="robotics",
                role=SearchRole.IMPORTANT,
                is_phrase=False,
                variants=["humanoid robots", "autonomous robots", ""],
            ),
            SearchTerm(
                text="autos",
                role=SearchRole.IMPORTANT,
                is_phrase=False,
                variants=["automotive", "cars", "electric vehicles"],
            ),
        ]
    )
}

mock_data9 = {
    "terms": SearchTerms(
        terms=[
            SearchTerm(
                text="Optimus",
                role=SearchRole.ESSENTIAL,
                is_phrase=False,
                variants=["Optimus robot", "Tesla Optimus", "humanoid robot"],
            ),
            SearchTerm(
                text="robotics manufacturing",
                role=SearchRole.ESSENTIAL,
                is_phrase=False,
                variants=[
                    "robot manufacturing",
                    "robotics production",
                    "manufacturing robots",
                ],
            ),
            SearchTerm(
                text="company",
                role=SearchRole.CONTEXTUAL,
                is_phrase=False,
                variants=["Tesla", "the company", "corporation"],
            ),
        ]
    )
}

mock_data10 = {
    "terms": SearchTerms(
        terms=[
            SearchTerm(
                text="Plutarch",
                role=SearchRole.SOURCE_REFERENCE,
                is_phrase=False,
                variants=["Πλούταρχος", "Plutarchus", "Plutarch's"],
            ),
            SearchTerm(
                text="Lives",
                role=SearchRole.SOURCE_REFERENCE,
                is_phrase=False,
                variants=["Parallel Lives", "Βίοι Παράλληλοι", "Life of Alcibiades"],
            ),
            SearchTerm(
                text="Alcibiades",
                role=SearchRole.TARGET_ENTITY,
                is_phrase=False,
                variants=["Alkibiades", "Ἀλκιβιάδης", "Alcibiades'"],
            ),
            SearchTerm(
                text="main strategic contribution",
                role=SearchRole.ESSENTIAL,
                is_phrase=False,
                variants=[
                    "chief contribution",
                    "principal contribution",
                    "strategic role",
                ],
            ),
            SearchTerm(
                text="Peloponnesian War",
                role=SearchRole.ESSENTIAL,
                is_phrase=True,
                variants=[
                    "Peloponnesian conflict",
                    "war against the Peloponnesians",
                    "Πελοποννησιακός Πόλεμος",
                ],
            ),
        ]
    )
}


mock_data11 = {
    "terms": SearchTerms(
        terms=[
            SearchTerm(
                text="Plutarch",
                role=SearchRole.SOURCE_REFERENCE,
                is_phrase=False,
                variants=["Plutarch's", "Πλουτάρχου"],
            ),
            SearchTerm(
                text="Lives",
                role=SearchRole.SOURCE_REFERENCE,
                is_phrase=False,
                variants=["Parallel Lives", "Βίοι Παράλληλοι"],
            ),
            SearchTerm(
                text="Alcibiades",
                role=SearchRole.TARGET_ENTITY,
                is_phrase=False,
                variants=["Alkibiades", "Ἀλκιβιάδης"],
            ),
            SearchTerm(
                text="Peloponnesian War",
                role=SearchRole.ESSENTIAL,
                is_phrase=True,
                variants=["Peloponnesian", "Πελοποννησιακός πόλεμος"],
            ),
            SearchTerm(
                text="strategic contribution",
                role=SearchRole.ESSENTIAL,
                is_phrase=False,
                variants=["strategy", "strategic", "plan"],
            ),
        ]
    )
}


def lex_reciprocal_rank_fusion(
    ranked_lists: dict[str, Sequence[ScoredChunkRow]],
    *,
    key: Callable[[ScoredChunkRow], Hashable],
    k: int = 60,
) -> list[dict[str, Any]]:
    """Fuse multiple ranked result lists using Reciprocal Rank Fusion.

    Args:
        ranked_lists: Mapping of search names to ranked result lists. Each
            result list must be ordered from most relevant to least relevant.
        key: Function that returns a unique identifier for a result.
        k: Rank constant used in the RRF calculation. Defaults to 60.

    Returns:
        All unique results sorted by descending RRF score. Each result
        contains the original item, its RRF score, and its rank in each
        search in which it appeared.

    """
    scores: dict[Hashable, float] = defaultdict(float)
    items: dict[Hashable, ScoredChunkRow] = {}
    ranks: dict[Hashable, dict[str, int]] = defaultdict(dict)

    for search_name, ranked_list in ranked_lists.items():
        seen = set()

        for rank, item in enumerate(ranked_list, start=1):
            item_id = key(item)

            if item_id in seen:
                continue

            seen.add(item_id)
            items.setdefault(item_id, item)

            ranks[item_id][search_name] = rank
            scores[item_id] += 1.0 / (k + rank)

    fused = [
        {
            "item": items[item_id],
            "rrf_score": scores[item_id],
            "ranks": ranks[item_id],
        }
        for item_id in scores
    ]

    fused.sort(key=lambda x: x["rrf_score"], reverse=True)

    return fused


def sem_lex_final_RRF(
    ranked_lists: dict[str, Sequence[ScoredChunkRow]],
    key: Callable[[ScoredChunkRow], int] = lambda row: row.entry,
    k: int = 60,
) -> list[FusedResult]:
    """Takes semantic and lexical lists and produces final RRF list"""

    scores: dict[int, float] = defaultdict(float)
    items: dict[int, ScoredChunkRow] = {}

    for search_type, ranked_list in ranked_lists.items():
        seen: set[int] = set()

        for rank, item in enumerate(ranked_list):
            item_id: int = key(item)
            if item_id in seen:
                continue
            seen.add(item_id)
            items.setdefault(item_id, item)
            scores[item_id] += 1.0 / (k + rank)

    fused_ids = sorted(scores, key=lambda item_id: scores[item_id], reverse=True)
    return [
        FusedResult(chunk=items[item_id], rrf_score=scores[item_id])
        for item_id in fused_ids
    ]


def run_search(
    query: str,
    lex_search_terms: SearchTerms,
    lex_k: int = 100,
    sem_k: int = 100,
) -> list[FusedResult]:
    """Takes in query and SearchTerms nand executes both searches returning results"""
    """Needs to have executed llm that parses semantic terms.
    Returns each retrieved chunk paired with its fused RRF score, highest to lowest."""

    lexical_search_queries = process_lexical_query(
        lex_search_terms.model_dump()["terms"]
    )
    lexical_results = execute_lexical_retrieval(lexical_search_queries)
    rrf_lexical = lex_reciprocal_rank_fusion(
        lexical_results, key=lambda row: row.entry, k=30
    )
    # Take top k
    lex_final = rrf_lexical[:lex_k]
    # print(f"Lexical looks like:\n\n{lex_final[0]}\n\n")
    # print(f"Lexical looks like:\n\n{lex_final[1]}\n\n")

    semantic_results = execute_semantic_retrieval(query)
    sem_final = semantic_results[:sem_k]

    # print(f"Semantic looks like:\n\n{sem_final[0]}\n\n")
    # print(f"Semantic looks like:\n\n{sem_final[1]}\n\n")

    final: list[FusedResult] = sem_lex_final_RRF(
        {"lexical": [x["item"] for x in lex_final], "semantic": [x for x in sem_final]}
    )

    return final
    # print("Final list looks like:\n")
    # for x in final[:30]:
    #     print(f"\n\n{x}\n\n")


if __name__ == "__main__":
    data = mock_data11["terms"]
    # data = mock_data["terms"]
    p = process_lexical_query([x.model_dump() for x in data.terms])
    print(f"\n\np is:\n{p}\n\n")
    e = execute_lexical_retrieval(p)
    # print(e)
    print(f"Done lexical retrieval, now RRF\n")
    ranks = lex_reciprocal_rank_fusion(e, key=lambda row: row.entry, k=30)

    # print(f"\n\n{ranks}\n\n")
    for x in enumerate(ranks):
        print(x)
        # print(f"\n{x[1]}\n")

    print(len(ranks))

    # print(f"type of e is {type(e)}")
    # for k, v in e.items():
    #     print(k, len(v))

    # for k, v in e.items():
    #     print(f"{'-' * 35}\n\n{k}")
    #     for x in v:
    #         print(f"{x}\n\n")

    print("done")
