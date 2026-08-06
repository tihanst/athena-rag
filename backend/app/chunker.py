from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1200,
    chunk_overlap=200,
    add_start_index=True,
    separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""],
)


def chunk_text(document_store: list[Document], document_id: str) -> list[Document]:
    docs = text_splitter.split_documents(document_store)

    for i, doc in enumerate(docs):
        start = doc.metadata["start_index"]
        end = start + len(doc.page_content)
        doc.metadata["end_index"] = end
        doc.metadata["source_document_id"] = document_id
        doc.metadata["document_chunk_index"] = i
        doc.metadata["document_last_chunk_index"] = len(docs) - 1

    return docs
