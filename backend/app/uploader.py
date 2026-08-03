import pdf_inspector
from docling.document_converter import DocumentConverter
from pathlib import Path


def file_uploader(
    id_based_file_name: str, uploads_path: Path, markdown_upload_path: Path
):
    # Handle a pdf (scanned or otherwise), txt, md, or docx separately NEEDS TO BE DONE....breakout a with open(...) as a separate function

    # print(file_path)
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
            with open(
                f"{markdown_upload_path}/{base_name}.md",
                "w",
                encoding="utf-8",
            ) as f:
                f.write(mkdn_result)
        else:
            with open(
                f"{markdown_upload_path}/{base_name}.md",
                "w",
                encoding="utf-8",
            ) as f:
                if result.markdown is not None:
                    f.write(result.markdown)

    elif suffix == ".txt":
        text = full_file_path.read_text(encoding="utf-8")
        (markdown_upload_path / f"{base_name}.txt").write_text(text, encoding="utf-8")

    elif suffix == ".md":
        text = full_file_path.read_text(encoding="utf-8")
        (markdown_upload_path / f"{base_name}.md").write_text(text, encoding="utf-8")

    elif suffix == ".docx":
        converter = DocumentConverter()
        result = converter.convert(full_file_path)
        mkdn_result = result.document.export_to_markdown()
        (markdown_upload_path / f"{base_name}.md").write_text(
            mkdn_result, encoding="utf-8"
        )


if __name__ == "__main__":
    file_uploader("f")
