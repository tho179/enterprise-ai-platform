from pathlib import Path
from app.document_parser import extract_text_from_pdf

PDF_PATH = Path("data/documents/16.-MSC_Quy-che-noi-bo-ve-quan-tri-2025-1.pdf")

def main():
    if not PDF_PATH.exists():
        print("PDF file not found")
        return

    print(f"Đang đọc tài liệu PDF: {PDF_PATH}")

    pages = extract_text_from_pdf(str(PDF_PATH))
    text = "\n".join([page["text"] for page in pages])
    print(f"Độ dài văn bản: {len(text):,} ký tự")
    print(f"Số dòng: {len(text.splitlines()):,} dòng")

    print(f"\n 2.000 kí tự đầu")
    print(text[:2000])

    output_path = Path("data/extracted_test.txt")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")

    print(f"\nĐã lưu văn bản trích xuất tại: {output_path}")


if __name__ == "__main__":
    main()
