"""
Batch OCR using DeepSeek-OCR model.

Processes page images and outputs markdown text files.
The model loads once and processes all pages in the given range,
skipping pages that already have valid results (>100 bytes).

Usage:
    python ocr_batch.py <start_page> <end_page>

Expects:
    - Page images at /data/pages/page_NNNN.png
    - Output directory at /output/ocr_results/
    - NVIDIA GPU with >= 8GB VRAM
"""
import os
import sys
import shutil
import torch
from transformers import AutoModel, AutoTokenizer

INPUT_DIR = os.environ.get("INPUT_DIR", "/data/pages")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/output/ocr_results")
MODEL_NAME = os.environ.get("MODEL_NAME", "deepseek-ai/DeepSeek-OCR")
BASE_SIZE = int(os.environ.get("BASE_SIZE", "1024"))
IMAGE_SIZE = int(os.environ.get("IMAGE_SIZE", "640"))
CROP_MODE = os.environ.get("CROP_MODE", "true").lower() == "true"

def main():
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    end = int(sys.argv[2]) if len(sys.argv) > 2 else 20

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Loading {MODEL_NAME}...", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    model = AutoModel.from_pretrained(
        MODEL_NAME,
        _attn_implementation="flash_attention_2",
        trust_remote_code=True,
        use_safetensors=True,
    )
    model = model.eval().cuda().to(torch.bfloat16)
    print("Model loaded!", flush=True)

    prompt = "<image>\n<|grounding|>Convert the document to markdown."
    tmp_out = "/tmp/ocr_tmp"

    processed = 0
    skipped = 0

    for i in range(start, end + 1):
        image_file = os.path.join(INPUT_DIR, f"page_{i:04d}.png")
        out_file = os.path.join(OUTPUT_DIR, f"page_{i:04d}.md")

        # Skip if already done and valid
        if os.path.exists(out_file) and os.path.getsize(out_file) > 100:
            skipped += 1
            continue

        if not os.path.exists(image_file):
            continue

        print(f"  [{processed+1}] Processing page {i}...", flush=True)

        # Clean tmp dir
        if os.path.exists(tmp_out):
            shutil.rmtree(tmp_out)
        os.makedirs(tmp_out, exist_ok=True)

        try:
            model.infer(
                tokenizer,
                prompt=prompt,
                image_file=image_file,
                output_path=tmp_out,
                base_size=BASE_SIZE,
                image_size=IMAGE_SIZE,
                crop_mode=CROP_MODE,
                save_results=True,
                test_compress=True,
            )

            result_file = os.path.join(tmp_out, "result.mmd")
            if os.path.exists(result_file):
                with open(result_file, "r", encoding="utf-8") as f:
                    text_result = f.read()
                if len(text_result) > 10:
                    with open(out_file, "w", encoding="utf-8") as f:
                        f.write(text_result)
                    print(f"    OK ({len(text_result)} chars)", flush=True)
                    processed += 1
                else:
                    print(f"    WARNING: empty result for page {i}", flush=True)
            else:
                print(f"    WARNING: no result.mmd for page {i}", flush=True)

        except Exception as e:
            print(f"    ERROR on page {i}: {e}", flush=True)

    print(f"\nDone! Processed {processed} pages, skipped {skipped} existing.", flush=True)

if __name__ == "__main__":
    main()
