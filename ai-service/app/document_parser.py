from pathlib import Path

import fitz


def extract_text_from_pdf(file_path: str) -> list[dict]:
    """
    Trích xuất nội dung PDF theo từng trang.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"File không tồn tại: {file_path}"
        )

    pages = []

    with fitz.open(file_path) as document:
        for page_number, page in enumerate(document):
            text = page.get_text("text").strip()

            if text:
                pages.append({
                    "page": page_number + 1,
                    "text": text
                })

    return pages


def extract_text_from_txt(file_path: str) -> list[dict]:
    """
    Đọc file TXT và xem toàn bộ nội dung như một trang.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"File không tồn tại: {file_path}"
        )

    text = path.read_text(
        encoding="utf-8"
    ).strip()

    if not text:
        return []

    return [
        {
            "page": 1,
            "text": text
        }
    ]


def extract_text(file_path: str) -> list[dict]:
    """
    Tự nhận diện loại file.
    """

    extension = Path(file_path).suffix.lower()

    if extension == ".pdf":
        return extract_text_from_pdf(file_path)

    if extension == ".txt":
        return extract_text_from_txt(file_path)

    raise ValueError(
        f"Chưa hỗ trợ định dạng file: {extension}"
    )