"""
Split a PDF into a page range.

Usage:
    python split_pdf.py <input_pdf> <output_pdf> <start_page> <end_page>

Example:
    python split_pdf.py /data/input.pdf /output/subset.pdf 622 1402
"""
import sys
from pypdf import PdfReader, PdfWriter

def main():
    if len(sys.argv) < 5:
        print("Usage: python split_pdf.py <input> <output> <start> <end>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    start_page = int(sys.argv[3])
    end_page = int(sys.argv[4])

    reader = PdfReader(input_path)
    writer = PdfWriter()

    total = len(reader.pages)
    if end_page > total:
        end_page = total

    for i in range(start_page - 1, end_page):
        writer.add_page(reader.pages[i])

    writer.write(output_path)
    page_count = end_page - start_page + 1
    print(f"Done — wrote pages {start_page}-{end_page} ({page_count} pages) to {output_path}")

if __name__ == "__main__":
    main()
