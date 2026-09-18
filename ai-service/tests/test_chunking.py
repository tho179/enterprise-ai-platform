import json
from pathlib import Path

from app.chunking import TextChunker


INPUT_PATH = Path("data/extracted_test.txt")
OUTPUT_PATH = Path("data/chunks_test.json")


def main():
    if not INPUT_PATH.exists():
        print(f"Không tìm thấy file: {INPUT_PATH}")
        return

    text = INPUT_PATH.read_text(encoding="utf-8")

    print("========== THÔNG TIN ĐẦU VÀO ==========")
    print(f"File: {INPUT_PATH}")
    print(f"Số ký tự: {len(text):,}")

    chunker = TextChunker(
        chunk_size=1200,
        chunk_overlap=200,
        min_chunk_size=100,
    )

    chunks = chunker.split_text(text)

    chunks_data = [
        {
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "start_char": chunk.start_char,
            "end_char": chunk.end_char,
        }
        for chunk in chunks
    ]

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            chunks_data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\n========== KẾT QUẢ CHUNKING ==========")
    print(f"Số chunk: {len(chunks_data):,}")
    print(f"File kết quả: {OUTPUT_PATH}")

    for chunk in chunks_data[:3]:
        print("\n----------------------------------------")
        print(f"Chunk index: {chunk['chunk_index']}")
        print(f"Số ký tự: {len(chunk['content']):,}")
        print(chunk["content"][:500])


if __name__ == "__main__":
    main()