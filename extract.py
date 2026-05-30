import sys
import os

# Force UTF-8 output so special characters (bullets, checkmarks, etc.) don't crash on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def extract_pdf(path):
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if text:
                print(f"\n--- Page {i} ---")
                print(text)

def extract_docx(path):
    from docx import Document
    doc = Document(path)
    for para in doc.paragraphs:
        if para.text.strip():
            print(para.text)

def extract_txt(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        print(f.read())

def main():
    if len(sys.argv) < 2:
        print("Usage: python extract.py <file.pdf|file.docx>")
        sys.exit(1)

    path = sys.argv[1]

    if not os.path.exists(path):
        print(f"Error: File not found: {path}")
        sys.exit(1)

    ext = os.path.splitext(path)[1].lower()

    if ext == ".pdf":
        extract_pdf(path)
    elif ext in (".docx", ".doc"):
        extract_docx(path)
    elif ext == ".txt":
        extract_txt(path)
    else:
        print(f"Error: Unsupported file type '{ext}'. Use .pdf, .docx, or .txt")
        sys.exit(1)

if __name__ == "__main__":
    main()
