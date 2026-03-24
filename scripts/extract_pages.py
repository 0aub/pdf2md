"""
Extract PDF pages as PNG images for OCR processing.

Usage:
    python extract_pages.py <start_page> <end_page> [--dpi 200]

Expects:
    - Input PDF at /data/input.pdf
    - Output directory at /output/pages/
"""
import sys
import os
from pdf2image import convert_from_path

INPUT = os.environ.get("PDF_INPUT", "/data/input.pdf")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/output/pages")
DPI = int(os.environ.get("DPI", "200"))

def main():
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    end = int(sys.argv[2]) if len(sys.argv) > 2 else 20

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Converting pages {start}-{end} to images (DPI={DPI})...", flush=True)
    images = convert_from_path(INPUT, first_page=start, last_page=end, dpi=DPI)

    for i, img in enumerate(images, start=start):
        path = os.path.join(OUTPUT_DIR, f"page_{i:04d}.png")
        img.save(path, "PNG")
        print(f"  Saved {path}", flush=True)

    print("Done.", flush=True)

if __name__ == "__main__":
    main()
