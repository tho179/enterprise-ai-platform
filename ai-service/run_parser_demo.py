import json
import sys
import io
from pathlib import Path

# Force UTF-8 encoding for stdout printing on Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from app.document_parser import extract_text
from app.block_analyzer import BlockAnalyzer
from app.chunking import TextChunker, TextChunk


def run_demo(pdf_file_path: str):
    path = Path(pdf_file_path)
    if not path.exists():
        print(f"File không tồn tại: {pdf_file_path}")
        return

    print("=" * 70)
    print(f"📖 ĐANG CHẠY DOCUMENT PARSER TRÊN FILE: {path.name}")
    print(f"📍 Đường dẫn: {path.resolve()}")
    print("=" * 70)

    # Call the parser
    pages = extract_text(str(path))

    print(f"\n✅ Đã trích xuất thành công: {len(pages)} trang")

    total_chars = sum(len(p["text"]) for p in pages)
    print(f"📊 Tổng số ký tự: {total_chars:,} ký tự")

    # Display preview for each extracted page
    for p in pages:
        page_num = p["page"]
        text = p["text"]
        lines = text.splitlines()
        print("\n" + "-" * 50)
        print(f"📄 TRANG {page_num} ({len(text)} ký tự, {len(lines)} dòng)")
        print("-" * 50)
        preview_lines = lines[:10]  # Show first 10 lines of each page
        for idx, line in enumerate(preview_lines, start=1):
            print(f"  [{idx:02d}] {line}")
        if len(lines) > 10:
            print(f"  ... (còn {len(lines) - 10} dòng nữa)")

    # Save to data/extracted_test.txt
    txt_output_path = Path("data/extracted_test.txt")
    txt_output_path.parent.mkdir(parents=True, exist_ok=True)
    full_text = "\n\n".join([f"=== TRANG {p['page']} ===\n{p['text']}" for p in pages])
    txt_output_path.write_text(full_text, encoding="utf-8")

    # Save to data/extracted_test.json
    json_output_path = Path("data/extracted_test.json")
    json_output_path.write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding="utf-8")

    # ----- NEW: RUN BLOCK ANALYZER -----
    print("\n" + "=" * 70)
    print("🧩 ĐANG CHẠY BLOCK ANALYZER ĐỂ PHÂN TÍCH CẤU TRÚC...")
    analyzer = BlockAnalyzer()
    blocks = analyzer.analyze(pages)
    
    print(f"✅ Đã phân tích thành: {len(blocks)} khối ngữ nghĩa (blocks)")
    for i, b in enumerate(blocks[:5]): # In thử 5 block đầu tiên
        print(f"  [{b['label']}] Block {b['block_id']}: {b['title']}")
    if len(blocks) > 5:
        print("  ...")
        
    block_output_path = Path("data/extracted_blocks.json")
    block_output_path.write_text(json.dumps(blocks, ensure_ascii=False, indent=2), encoding="utf-8")

    # ----- NEW: RUN CHUNKER -----
    print("\n" + "=" * 70)
    print("✂️ ĐANG CHẠY TEXT CHUNKER ĐỂ CẮT NHỎ VĂN BẢN...")
    chunker = TextChunker()
    final_chunks = chunker.chunk_blocks(blocks)
    
    print(f"✅ Đã cắt thành: {len(final_chunks)} chunks (đoạn nhỏ)")
    for i, c in enumerate(final_chunks[:3]): # In thử 3 chunk đầu
        print(f"  [Chunk {c.chunk_index}] {c.metadata['parent_chapter']} - {c.metadata['title']}")
        print(f"  Snippet: {c.content[:80]}...")
    if len(final_chunks) > 3:
        print("  ...")
        
    chunk_output_path = Path("data/final_chunks.json")
    # Convert DataClass to Dict for JSON serialization
    from dataclasses import asdict
    chunks_dict = [asdict(c) for c in final_chunks]
    chunk_output_path.write_text(json.dumps(chunks_dict, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 70)
    print(f"💾 Kết quả Parser (Văn bản) đã lưu tại: {txt_output_path.resolve()}")
    print(f"💾 Kết quả Parser (JSON) đã lưu tại: {json_output_path.resolve()}")
    print(f"💾 Kết quả Block (JSON) đã lưu tại: {block_output_path.resolve()}")
    print(f"💾 Kết quả Chunk (JSON) đã lưu tại: {chunk_output_path.resolve()}")
    print("=" * 70)


if __name__ == "__main__":
    # Test file PDF Scan thực tế
    target_pdf = "data/documents/dieu_le_sua_doi/Phu_luc_sua_doi_dieu_le_lan_1.pdf"
    if len(sys.argv) > 1:
        target_pdf = sys.argv[1]

    run_demo(target_pdf)
