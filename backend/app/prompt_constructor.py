from app.schemas import ContextLoadChunk

DOCUMENT_CHUNK_ELEMENT = """\
<document title="{document_title}">

{chunk_elements}
</document>"""

CHUNK_ELEMENT = """\
<entry index="{db_entry_number}">
{chunk}
</entry>"""


def construct_rag_chat_user_prompt(
    context_dict: dict[str, list[ContextLoadChunk]],
) -> str:
    """Arrange context dict docs and chunks in proper formatting for user chat prompt.
    Context dict are listed from least important document chunks to most important at the end."""

    context_string = ""

    for doc, chunks in context_dict.items():
        clean_title = doc[doc.find("__") + 2 :]
        chunks_string = ""
        for c in chunks:
            chunks_string += (
                CHUNK_ELEMENT.format(
                    db_entry_number=c.start_db_entry_id, chunk=c.content
                )
                + "\n\n"
            )

        context_string += (
            DOCUMENT_CHUNK_ELEMENT.format(
                document_title=clean_title, chunk_elements=chunks_string
            )
            + "\n\n"
        )
    return context_string
