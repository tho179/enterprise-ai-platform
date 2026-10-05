import sys
import io
import json
from pathlib import Path
from app.document_parser import extract_text

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def main():
    target_pdf = "data/documents/nhan_su_va_lao_dong/Noi_quy_lao_dong.pdf"
    if len(sys.argv) > 1:
        target_pdf = sys.argv[1]

    print(f"📄 Đang đọc PDF: {target_pdf}")
    pages = extract_text(target_pdf)
    
    out_dir = Path("debug")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    out_path = out_dir / "01_extracted_pages.json"
    out_path.write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print(f"✅ Đã lưu kết quả Extractor ({len(pages)} trang) tại: {out_path}")

if __name__ == "__main__":
    main()
