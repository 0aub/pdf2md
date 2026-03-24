# pdf2md — Claude Code Instructions

You are working inside the `pdf2md` project, a Dockerized pipeline that converts PDFs into organized Markdown using DeepSeek-OCR for text and Claude for image descriptions.

## Project Overview

- `run.sh` — Main pipeline script (split → extract → OCR → cleanup)
- `docker/` — Three Dockerfiles: split, extract, ocr
- `scripts/` — Python scripts for each pipeline stage
- `pages/` — Generated PNG page images
- `ocr_results/` — Per-page OCR markdown output
- `image_descriptions/` — Figure description batch files
- `output/` — Final combined markdown

## Key Technical Details

- DeepSeek-OCR model: `deepseek-ai/DeepSeek-OCR` (3B params, MIT license)
- Model loading: Must use `_attn_implementation="flash_attention_2"` and `.eval().cuda().to(torch.bfloat16)` — do NOT use `torch_dtype` in `from_pretrained` or `device_map="cuda"` as these break the `.infer()` method (returns None)
- The `.infer()` method writes results to `result.mmd` in the output_path when `save_results=True` — the return value is None
- OCR config "Gundam": `base_size=1024, image_size=640, crop_mode=True`
- HuggingFace cache should be mounted at `/root/.cache/huggingface` to avoid re-downloading the 6GB model each run
- All Docker containers should use `--init` flag to prevent zombie processes

## Image Description Workflow

When asked to add image descriptions:

1. Identify pages with figures: `grep -n "^Fig\." output/result.md`
2. Read page images at `pages/page_NNNN.png`
3. Write descriptions in batches to `image_descriptions/batch_NN.md`
4. Use format: `<!-- Page image: page_NNNN.png -->` followed by description blocks
5. Run `scripts/merge_descriptions.py` to combine into final output
