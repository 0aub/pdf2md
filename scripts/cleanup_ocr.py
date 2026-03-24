"""
Clean up DeepSeek-OCR output and combine into a single markdown file.

- Removes <|ref|>...<|/ref|> and <|det|>...<|/det|> annotation tags
- Preserves markdown structure (headings, tables, etc.)
- Combines all per-page OCR results into one file
- Adds page number markers for reference

Usage:
    python cleanup_ocr.py <ocr_results_dir> <output_file> [--page-offset 0]

Example:
    python cleanup_ocr.py ./ocr_results ./output/book.md --page-offset 621
"""
import os
import re
import sys
import argparse

def clean_ocr_text(text):
    """Remove OCR annotation tags while preserving content."""
    text = re.sub(r'<\|ref\|>[^<]*<\|/ref\|>', '', text)
    text = re.sub(r'<\|det\|>\[\[[^\]]*\]\]<\|/det\|>', '', text)
    text = re.sub(r'<center>(.*?)</center>', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    text = re.sub(r'\n[ \t]+\n', '\n\n', text)
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def main():
    parser = argparse.ArgumentParser(description="Clean and combine OCR results")
    parser.add_argument("input_dir", help="Directory with per-page .md files")
    parser.add_argument("output_file", help="Output combined markdown file")
    parser.add_argument("--page-offset", type=int, default=0,
                        help="Offset to add to page numbers (e.g., 621 if file page 1 = PDF page 622)")
    parser.add_argument("--title", type=str, default="",
                        help="Title for the output document")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output_file) or ".", exist_ok=True)

    page_files = sorted([
        f for f in os.listdir(args.input_dir)
        if f.startswith("page_") and f.endswith(".md") and os.path.getsize(os.path.join(args.input_dir, f)) > 100
    ])

    print(f"Found {len(page_files)} valid OCR result files")

    with open(args.output_file, 'w', encoding='utf-8') as out:
        if args.title:
            out.write(f"# {args.title}\n\n---\n\n")

        for i, filename in enumerate(page_files):
            filepath = os.path.join(args.input_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                raw_text = f.read()

            cleaned = clean_ocr_text(raw_text)
            page_num = int(filename.replace("page_", "").replace(".md", ""))
            original_page = page_num + args.page_offset

            out.write(f"<!-- Page {original_page} (file page {page_num}) -->\n\n")
            out.write(cleaned)
            out.write("\n\n---\n\n")

            if (i + 1) % 100 == 0:
                print(f"  Processed {i + 1}/{len(page_files)} pages")

    size_mb = os.path.getsize(args.output_file) / (1024 * 1024)
    print(f"\nDone! Output: {args.output_file}")
    print(f"File size: {size_mb:.1f} MB")

if __name__ == "__main__":
    main()
