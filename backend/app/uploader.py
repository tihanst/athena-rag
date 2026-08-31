import pdf_inspector
from docling.document_converter import DocumentConverter
from pathlib import Path
import re


def file_uploader(
    id_based_file_name: str, uploads_path: Path, markdown_upload_path: Path
) -> tuple[str, str]:
    # Handle a pdf (scanned or otherwise), txt, md, or docx separately NEEDS TO BE DONE....breakout a with open(...) as a separate function
    # Returns document_text, saved_filename

    full_file_path = uploads_path / id_based_file_name

    suffix = Path(id_based_file_name).suffix
    base_name = Path(id_based_file_name).stem

    if suffix == ".pdf":
        result = pdf_inspector.process_pdf(
            str(full_file_path)
        )  # "text_based", "scanned", "image_based", "mixed"
        # print(result.pdf_type)

        if result.pdf_type == "scanned":
            converter = DocumentConverter()
            result = converter.convert(full_file_path)
            mkdn_result = result.document.export_to_markdown()
            # print(f"****USED DOCLING****\n\n\n{mkdn_result}")
        else:
            mkdn_result = result.markdown or ""

        with open(
            f"{markdown_upload_path}/{base_name}.md",
            "w",
            encoding="utf-8",
        ) as f:
            f.write(mkdn_result)

        return mkdn_result, f"{base_name}.md"

    elif suffix == ".txt":
        text = full_file_path.read_text(encoding="utf-8")
        text = normalize_txt_file_text(text)
        (markdown_upload_path / f"{base_name}.txt").write_text(text, encoding="utf-8")
        return text, f"{base_name}.txt"

    elif suffix == ".md":
        text = full_file_path.read_text(encoding="utf-8")
        (markdown_upload_path / f"{base_name}.md").write_text(text, encoding="utf-8")
        return text, f"{base_name}.md"

    elif suffix == ".docx":
        converter = DocumentConverter()
        result = converter.convert(full_file_path)
        mkdn_result = result.document.export_to_markdown()
        (markdown_upload_path / f"{base_name}.md").write_text(
            mkdn_result, encoding="utf-8"
        )
        return mkdn_result, f"{base_name}.md"

    else:
        raise ValueError(f"Unsupported file suffix: {suffix!r}")


def normalize_txt_file_text(text: str) -> str:
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Split on blank lines = paragraph boundaries
    paragraphs = re.split(r"\n\s*\n+", text)

    # Replace single newlines inside each paragraph with spaces
    paragraphs = [
        " ".join(line.strip() for line in paragraph.splitlines() if line.strip())
        for paragraph in paragraphs
    ]

    # Restore paragraph breaks
    return "\n\n".join(p for p in paragraphs if p)


def generate_llm_summary():
    pass


if __name__ == "__main__":
    pass
    # file_uploader()
