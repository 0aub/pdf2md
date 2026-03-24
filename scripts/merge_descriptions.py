"""
Merge image descriptions into the main OCR markdown file.

For each figure caption (Fig. X.Y.), inserts the corresponding
image description block right before it.

Usage:
    python merge_descriptions.py <main_md> <descriptions_dir> <output_md>

Example:
    python merge_descriptions.py ./output/book.md ./image_descriptions ./output/book_final.md
"""
import os
import re
import sys
import glob
import argparse

def load_descriptions(desc_dir):
    """Load all batch description files and index by page number."""
    descriptions = {}

    for batch_file in sorted(glob.glob(os.path.join(desc_dir, "batch_*.md"))):
        with open(batch_file, "r", encoding="utf-8") as f:
            content = f.read()

        sections = re.split(r'<!-- Page image: page_(\d+)\.png -->', content)
        for i in range(1, len(sections), 2):
            page_num = int(sections[i])
            desc_content = sections[i + 1].strip() if i + 1 < len(sections) else ""
            if desc_content:
                if page_num not in descriptions:
                    descriptions[page_num] = desc_content
                else:
                    descriptions[page_num] += "\n\n" + desc_content

    return descriptions

def main():
    parser = argparse.ArgumentParser(description="Merge image descriptions into markdown")
    parser.add_argument("main_md", help="Main markdown file from OCR")
    parser.add_argument("descriptions_dir", help="Directory with batch_*.md description files")
    parser.add_argument("output_md", help="Output merged markdown file")
    args = parser.parse_args()

    descriptions = load_descriptions(args.descriptions_dir)
    print(f"Loaded descriptions for {len(descriptions)} pages")

    with open(args.main_md, "r", encoding="utf-8") as f:
        lines = f.readlines()

    output_lines = []
    current_page = 0
    page_desc_inserted = set()

    for line in lines:
        m = re.match(r'<!-- Page \d+ \(file page (\d+)\) -->', line)
        if m:
            current_page = int(m.group(1))

        fig_match = re.match(r'^(Fig\. \d+\.\d+)', line.strip())
        if fig_match and current_page in descriptions and current_page not in page_desc_inserted:
            output_lines.append("\n")
            output_lines.append(descriptions[current_page] + "\n\n")
            page_desc_inserted.add(current_page)

        output_lines.append(line)

    with open(args.output_md, "w", encoding="utf-8") as f:
        f.writelines(output_lines)

    size_mb = os.path.getsize(args.output_md) / (1024 * 1024)
    print(f"Output: {args.output_md} ({size_mb:.1f} MB)")
    print(f"Inserted descriptions for {len(page_desc_inserted)} pages")

if __name__ == "__main__":
    main()
