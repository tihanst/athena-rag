import asyncio
from pprint import pprint
import json
from collections import defaultdict

from pydantic import ValidationError

from app.schemas import (
    ChatRequest,
    ChatSystem,
    ChatResponse,
    ChatHistoryItem,
    SearchTerms,
    ContextLoadChunk,
)
from app.memory import chat_history, ChatHistory
from app.db_types import RerankedResult
from app.llm import llms
from app.prompts import SEARCH_TERMS_SYSTEM_PROMPT, RAG_USER_PROMPT
from app.db_manager import execute_final_search_retrieval
from app.rerank import cross_encoder
from app.db_types import ChunkRow, FusedResult
from app.text_extractor import extract_original_text
from app.prompt_constructor import construct_rag_chat_user_prompt


from app.search_executor import run_search

"""
This will eventually decidee RAG or not, but just run RAG every time to start
Takes a ChatRequest, parses for search in lexical and semantic using llm 
"""


async def run_chat(request: ChatRequest):
    query = request.content

    try:
        lex_search_terms: SearchTerms = await generate_lexical_search_terms(request)
    except Exception as e:
        yield f"Error getting lexical search terms: {str(e)}"
        return

    context_chunks_dict = search_and_retrieve_chunks(
        query=query, lexical_search_terms=lex_search_terms
    )

    context_string = construct_rag_chat_user_prompt(context_dict=context_chunks_dict)

    full_user_prompt = RAG_USER_PROMPT.format(
        user_question=query, source_material=context_string
    )

    yield "Awaiting answer....\n\n"
    answer = await generate_chat_completion(full_context_query=full_user_prompt)

    print("Full model answer is:")
    print(answer)
    yield answer

    yield "Yo there"

    return


def search_and_retrieve_chunks(
    query: str, lexical_search_terms: SearchTerms
) -> dict[str, list[ContextLoadChunk]]:
    retrieved: list[FusedResult] = run_search(
        query=query, lex_search_terms=lexical_search_terms
    )

    # Rerank
    reranked_list: list[RerankedResult] = cross_encoder.rerank_list(
        query=query, data_list=retrieved
    )

    # The below holds the key database entry numbers of the sections that need to be selected from.
    # Must take the start_index of the first of a contiguous, through to the end_index of the last of a contiguous.
    compiled_retrieved = compile_retrieved_indices(reranked_list)

    # for x in reranked_list:
    #     yield repr(x)
    #     yield "\n\n"

    # Group documents by document_id based on max score of retrieved docs
    grouped_context_docs: defaultdict[str, list[RerankedResult]] = defaultdict(list)

    for x in reranked_list:
        grouped_context_docs[x.chunk.source_document_id].append(x)

    # Group by document id and sort where last doc has highest score
    # Could try other approaches such as rank by avg top 3 in each list
    grouped_context_docs = {
        k: v
        for k, v in sorted(
            grouped_context_docs.items(),
            key=lambda x: max([y.rerank_score for y in x[1]]),
        )
    }

    # Now have a dictionary of docs to build the context from in grouped_context_docs
    # and a dict of doc id's and lists of database entries that need to be retrieved
    # in compiled_retrieved. Take compiled_retrieved list of tuples and replace the longer
    # lists in grouped_context_docs

    # Merge both into new dictionary to go back to query the database

    context_references_for_db_query: dict[str, list[int]] = defaultdict(list)

    for key, value in grouped_context_docs.items():
        # print(f"Old for {key} = {value}\n")

        context_references_for_db_query[key] = compiled_retrieved[key]

    # print(f"Context ref for dbquery dict is:\n\n{context_references_for_db_query}\n\n")

    final_context_list = retrieve_full_context(context_references_for_db_query)
    # print("\n\n\n\n\n\n")
    # print(f"Final context list is:\n\n{final_context_list}")

    context_dict: dict[str, list[ContextLoadChunk]] = defaultdict(list)

    for doc, spans in final_context_list.items():
        context_load_chunks = []
        for span in spans:
            context_load_chunks.append(extract_original_text((doc, span)))
        context_dict[doc] = context_load_chunks

    # print(f"\n\n\nContext load chunks are:\n\n{context_dict}\n\n")
    print("\n\n\n")
    for doc, entries in context_dict.items():
        print(f"Document is: {doc}\n\n")
        for entry in entries:
            print(
                f"Entry between {entry.start_db_entry_id} and {entry.end_db_entry_id}:\n\n{entry.content}\n\n"
            )
    return context_dict


async def generate_lexical_search_terms(request: ChatRequest) -> SearchTerms:
    search_planner = llms["search_planner_llm"]

    chat_request = ChatRequest(
        role="user",
        content=request.content,
    )
    lex_search_system_msg = ChatSystem(content=SEARCH_TERMS_SYSTEM_PROMPT)

    # Don't pollute chat memory for the lexical search (can log those later)
    history = ChatHistory(history=[lex_search_system_msg, chat_request])

    lex_search_plan = await search_planner.acompletion_call(
        messages=history,
        response_format=SearchTerms,
        temperature=0.0,
        top_p=1.0,
        timeout=5,
        num_retries=2,
        drop_params=True,
        # This line overrides the UnsupportedParamsError validation check
        allowed_openai_params=["response_format"],
    )

    raw = lex_search_plan.choices[0].message.content

    try:
        valid_data = SearchTerms.model_validate_json(raw)
        print("\n\nValidated Search Terms are:\n\n")
        print(valid_data)
        return valid_data
    except (ValidationError, json.JSONDecodeError) as e:
        raise ValueError(f"Returned payload malformed as {raw!r} for error: {e}") from e


def _compress_to_spans(sorted_indices: list[int]) -> list[tuple[int, int] | tuple[int]]:
    """Takes sorted list and collapses any continuous indices into (first, last) tuples
    or just (first) if a single index without any contiguous neighbours."""
    if not sorted_indices:
        return []

    spans: list[tuple[int, int] | tuple[int]] = []
    start = prev = sorted_indices[0]

    for x in sorted_indices[1:]:
        if x == prev + 1:
            prev = x
            continue
        span = (start, prev) if prev != start else (start,)
        spans.append(span)
        start = prev = x
    span = (start, prev) if prev != start else (start,)
    spans.append(span)
    return spans


def compile_retrieved_indices(
    retrieved_items: list[RerankedResult],
) -> dict[str, list[int]]:
    """Takes hybrid search results, expands by adding adjacent chunks, sorts in dictionary
    by document id and sorted list of chunks for database retrieval"""
    documents_retrieved_and_indices: dict[str, set[int]] = defaultdict(set)
    chunks = [item.chunk for item in retrieved_items]

    for chunk in chunks:
        doc = documents_retrieved_and_indices[chunk.source_document_id]
        if (
            chunk.document_chunk_index == 0
            and chunk.document_chunk_index == chunk.document_last_chunk_index
        ):  # singleton entry
            doc.add(chunk.entry)
        elif chunk.document_chunk_index == 0:  # First chunk of a document, no previous
            doc.update([chunk.entry, chunk.entry + 1])
        elif (
            chunk.document_chunk_index == chunk.document_last_chunk_index
        ):  # Last chunk of a document, no next
            doc.update([chunk.entry, chunk.entry - 1])
        else:
            doc.update([chunk.entry, chunk.entry - 1, chunk.entry + 1])
    sorted_documents_retrieved_and_indices = {
        k: sorted(v) for k, v in documents_retrieved_and_indices.items()
    }

    return {
        k: _compress_to_spans(v)
        for k, v in sorted_documents_retrieved_and_indices.items()
    }


# Don't need this any longer since we now will go to the original files
# and use the start,end tuples
def retrieve_full_context(
    compiled_entries: dict[str, list[tuple[int, int] | tuple[int]]],
) -> dict[str, list[list[ChunkRow]]]:
    """Retrieves from database the final context, grouped per contiguous span
    so start_index/end_index can be read directly off each spans' first/last row."""
    final_chunks_dict: dict[str, list[list[ChunkRow]]] = {}

    for doc_name, spans in compiled_entries.items():
        final_chunks_dict[doc_name] = [
            execute_final_search_retrieval(span, doc_name) for span in spans
        ]

    return final_chunks_dict


async def generate_chat_completion(full_context_query: str) -> str:
    # Note chat_history is imported with the system prompt already included
    chat_request = ChatRequest(role="user", content=full_context_query)
    chat_history.add_message(chat_request)

    chat_model = llms["chat_llm"]

    response = await chat_model.acompletion_call(messages=chat_history)

    message = response.choices[0].message.content

    chat_history.add_message(ChatResponse(role="assistant", content=message))

    return message


# Testing below


async def main():
    chat_request = ChatRequest(
        role="user",
        message="In Meditations what did Marcus Aurelius say about facing fear in life?",  # "In Meditations, what did Marcus Aurelius say was the most important thing to leading a happy life?",  # "In his personal memoirs, what tactics did Ulyssees S. Grant use at the battle of Bull Run, and how did they differ from his strategy at Gettysburg in terms of deciding victory or defeat?",  # "What does Plutarch state in his 'Lives' book was Alcibiades main strategic contribution to the Peloponnesian War?",
        history=[ChatHistoryItem(role="system", content=SEARCH_TERMS_SYSTEM_PROMPT)],
    )
    run_chat(chat_request)
    # async for chunk in run_chat(chat_request):
    #     print(chunk, end="")
    # result = await generate_lexical_search_terms(chat_request)
    # return result


if __name__ == "__main__":
    result = asyncio.run(main())
    # print(result)
    # pprint(result, indent=3)
    # sterms = SearchTerms.model_validate(result)
    # # print(result.choices[0].message.content)
    # lex_queries = process_lexical_query(sterms.model_dump()["terms"])
    # executed_lex = execute_lexical_retrieval(lex_queries)
    # # print(sterms)
