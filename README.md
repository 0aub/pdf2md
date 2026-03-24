# pdf2md

A Dockerized pipeline that converts **entire books and large PDF documents** into clean, organized Markdown files using [DeepSeek-OCR](https://huggingface.co/deepseek-ai/DeepSeek-OCR) for high-accuracy text extraction.

Pair it with [Claude Code](https://claude.ai/claude-code) to get detailed visual descriptions of every figure, diagram, and clinical image in the document.

Everything runs inside Docker containers — nothing is installed on the host machine except Docker itself.

## How It Works

```
PDF ──► Split pages ──► Extract as images ──► DeepSeek-OCR (GPU) ──► Clean Markdown
                                                                          │
                                                          Claude Code ──► Image Descriptions
                                                                          │
                                                                     Final Markdown
```

1. **Split** — Extract a page range (or whole book) from the source PDF using `pypdf`
2. **Extract** — Convert each page to a high-resolution PNG image using `poppler`
3. **OCR** — Run DeepSeek-OCR on each page image to extract structured Markdown (text, tables, figure captions, math notation)
4. **Cleanup** — Strip OCR annotation tags and combine all pages into a single organized `.md` file
5. **Image Descriptions** *(optional, via Claude Code)* — Visually read every figure and generate detailed `[IMAGE DESCRIPTION]` blocks

## Use Cases

- Convert entire textbooks (500-2000+ pages) into searchable, editable Markdown
- Extract specific chapters or page ranges from large reference books
- Digitize medical, scientific, or technical texts with complex layouts
- Create accessible versions of image-heavy documents with figure descriptions
- Build study materials or knowledge bases from PDF sources

## Requirements

### Hardware

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU | NVIDIA GPU, 8GB VRAM | NVIDIA RTX 3090/4090, 24GB VRAM |
| RAM | 16GB | 32GB+ |
| Disk | 10GB free | 50GB+ (for large PDFs) |
| CPU | 4 cores | 8+ cores |

### Software

| Dependency | Version | Notes |
|------------|---------|-------|
| Docker | 20.10+ | With NVIDIA Container Toolkit |
| NVIDIA Driver | 525+ | CUDA 12.x compatible |
| nvidia-docker | 2.x | `nvidia-container-toolkit` package |
| Python 3 | 3.8+ | Only needed for cleanup scripts (runs on host) |

#### Installing NVIDIA Container Toolkit

```bash
# Ubuntu/Debian
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# Verify
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```

## Quick Start

```bash
# Clone the repo
git clone https://github.com/0aub/pdf2md.git
cd pdf2md

# Convert an entire book
./run.sh "/path/to/book.pdf" 1 500 --title "My Book"

# Or a specific page range
./run.sh "/mnt/d/Books/Campbell_Urology.pdf" 622 1402 --title "Campbell-Walsh-Wein Urology"

# Output will be at ./output/result.md
```

## Project Structure

```
pdf2md/
├── run.sh                          # Main pipeline script
├── CLAUDE.md                       # Claude Code project instructions
├── docker/
│   ├── Dockerfile.split            # PDF splitting (pypdf)
│   ├── Dockerfile.extract          # Page-to-image extraction (poppler)
│   └── Dockerfile.ocr              # DeepSeek-OCR (CUDA + flash-attn)
├── scripts/
│   ├── split_pdf.py                # Split PDF into page range
│   ├── extract_pages.py            # Convert pages to PNG images
│   ├── ocr_batch.py                # Run DeepSeek-OCR on page images
│   ├── cleanup_ocr.py              # Clean and combine OCR output
│   └── merge_descriptions.py       # Merge image descriptions into MD
├── pages/                          # (generated) Page images
├── ocr_results/                    # (generated) Per-page OCR output
├── image_descriptions/             # (generated) Figure descriptions
└── output/                         # (generated) Final markdown files
```

## Step-by-Step Manual Usage

If you prefer running each step individually:

### 1. Split PDF

```bash
docker build -t pdf2md-split -f docker/Dockerfile.split .
docker run --rm \
    -v "/path/to/pdfs:/data:ro" \
    -v "$(pwd)/output:/output" \
    pdf2md-split /data/book.pdf /output/subset.pdf 1 500
```

### 2. Extract Page Images

```bash
docker build -t pdf2md-extract -f docker/Dockerfile.extract .

# Process in batches of 50
for start in $(seq 1 50 500); do
    end=$((start + 49))
    docker run --rm \
        -v "$(pwd)/output:/data:ro" \
        -v "$(pwd)/pages:/output/pages" \
        -e PDF_INPUT="/data/subset.pdf" \
        pdf2md-extract $start $end
done
```

### 3. Run OCR

```bash
docker build -t pdf2md-ocr -f docker/Dockerfile.ocr .
docker run --rm --gpus all --init \
    -v "$(pwd)/pages:/data/pages:ro" \
    -v "$(pwd)/ocr_results:/output/ocr_results" \
    -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
    pdf2md-ocr 1 500
```

### 4. Clean Up and Combine

```bash
python3 scripts/cleanup_ocr.py ./ocr_results ./output/result.md --page-offset 0 --title "My Book"
```

## Adding Image Descriptions with Claude Code

The OCR pipeline captures all text, tables, and figure captions — but for figures, diagrams, and clinical images, you need a vision model to describe **what the image actually shows**. Claude Code can do this by reading the page images and writing detailed descriptions.

### Prerequisites

- [Claude Code](https://claude.ai/claude-code) installed (`npm install -g @anthropic-ai/claude-code`)
- OCR pipeline completed (Steps 1-4 above)
- Page images available in the `pages/` directory

### How It Works

1. Claude Code reads each page image that contains a figure
2. It writes a detailed visual description (colors, panels, labeled structures, staining, imaging modality, etc.)
3. Descriptions are saved as batch files in `image_descriptions/`
4. A merge script inserts them into the final markdown before each figure caption

### Step-by-Step

#### 1. Open Claude Code in the pdf2md directory

```bash
cd /path/to/pdf2md
claude
```

#### 2. Use this prompt to generate image descriptions

Copy and paste this prompt into Claude Code:

```
I have a PDF that was converted to markdown using DeepSeek-OCR. The text is in
output/result.md and the page images are in pages/page_NNNN.png.

I need you to add detailed visual descriptions for every figure in the document.

For each page that has a figure:
1. Read the page image
2. Write a detailed [IMAGE DESCRIPTION] block describing what you see
3. Save descriptions in batches to image_descriptions/batch_NN.md

Use this format for each figure:
<!-- Page image: page_NNNN.png -->
### Figure [number]
**[IMAGE DESCRIPTION]:** [Detailed description - colors, panels A/B/C, labeled
anatomical structures, arrows, scale bars, staining techniques, imaging modality]

Process all figure pages in parallel batches of 10 using agents for speed.
After all batches are done, run:
python3 scripts/merge_descriptions.py output/result.md image_descriptions output/result_final.md
```

#### 3. Claude Code will automatically:

- Scan the markdown for figure references (`Fig. X.Y.`)
- Identify which page images contain figures
- Launch parallel agents to read images and write descriptions
- Merge everything into the final output

#### 4. The result

Your final file at `output/result_final.md` will contain:
- Full text from every page (via DeepSeek-OCR)
- Detailed `**[IMAGE DESCRIPTION]**` blocks before every figure caption
- Tables in markdown format
- Mathematical notation in LaTeX
- All citations and references preserved

### Example Output

```markdown
<!-- Page 623 (file page 2) -->

### Figure 32.1
**[IMAGE DESCRIPTION]:** A composite photograph showing whole mount images of
developing human embryos from the Carnegie collection, arranged against a black
background. The specimens are numbered sequentially from 10 to 23, corresponding
to Carnegie Stages with approximate postovulatory days noted beneath each specimen.
The embryos increase dramatically in size and morphologic complexity across the
stages, progressing from small, curved, translucent forms at Stage 10 to
well-defined fetal forms with visible limbs and head structures at Stage 23.
A scale bar of 10 mm is provided at the bottom left.

Fig. 32.1. Whole mount photos of developing human embryos from the Carnegie
collection. Note increasing size and morphologic complexity with developmental
stage. (Image from Dr. Brad Smith, University of Michigan...)
```

### Performance with Claude Code

For a 781-page medical textbook with 627 figures:

| Step | Time | Method |
|------|------|--------|
| Identify figure pages | ~5 seconds | grep + Python |
| Generate descriptions | ~30 minutes | ~40 parallel agents, 10 pages each |
| Merge into final MD | ~2 seconds | Python script |

## DeepSeek-OCR Model Details

| Property | Value |
|----------|-------|
| Model | [deepseek-ai/DeepSeek-OCR](https://huggingface.co/deepseek-ai/DeepSeek-OCR) |
| Parameters | 3B |
| License | MIT |
| Precision | BF16 |
| VRAM Usage | ~8GB (inference) |
| Speed | ~2 pages/minute (RTX 4090) |
| Attention | Flash Attention 2 |

### OCR Configuration

The pipeline uses the "Gundam" configuration for the best balance of quality and speed:

| Setting | Value |
|---------|-------|
| `base_size` | 1024 |
| `image_size` | 640 |
| `crop_mode` | True |
| `save_results` | True |

### What DeepSeek-OCR Captures

- Body text with full paragraph structure
- Section headings and subheadings
- Tables (converted to HTML `<table>` format)
- Figure/image captions with source citations
- Mathematical notation (LaTeX format)
- References and bibliography
- Bulleted and numbered lists
- Multi-column layouts
- Key points boxes and clinical summaries

## Performance

Benchmarked on an NVIDIA RTX 4090 (24GB VRAM):

| Stage | Speed | Notes |
|-------|-------|-------|
| PDF Split | Instant | ~1 second for any range |
| Image Extraction | ~50 pages/min | 200 DPI PNG output |
| DeepSeek-OCR | ~2 pages/min | GPU-bound, Gundam config |
| Cleanup | Instant | Python text processing |

### Estimated Total Time by Book Size

| Pages | OCR Time | With Image Descriptions |
|-------|----------|------------------------|
| 100 | ~50 min | +15 min (Claude Code) |
| 500 | ~4 hours | +30 min (Claude Code) |
| 1000 | ~8 hours | +45 min (Claude Code) |
| 2000 | ~17 hours | +1 hour (Claude Code) |

The OCR is the bottleneck. Image extraction and cleanup are near-instant. Claude Code image descriptions are fast because they run in parallel.

## Tips

- **Whole books**: Just pass `1` as start page and the total page count as end page. The pipeline handles everything.
- **First run downloads the model** (~6GB). Subsequent runs use the cached version at `~/.cache/huggingface/`.
- **Crash recovery**: The OCR skips existing results (files >100 bytes). If it crashes, just re-run and it picks up where it left off.
- **Reduce DPI** to 150 if you're running low on disk space (the pages directory can get large).
- **Monitor GPU usage** with `nvidia-smi` or `watch -n1 nvidia-smi` in a separate terminal.
- **For WSL2 users**: PDF files on Windows drives are accessible at `/mnt/c/...` or `/mnt/d/...`.
- **Large books**: For 1000+ page books, consider running the OCR overnight. It's fully resumable.

## Known Limitations

- Requires NVIDIA GPU — no CPU-only mode (DeepSeek-OCR needs CUDA + Flash Attention)
- Handwritten text is not well supported (OCR is optimized for printed text)
- Very low-resolution scans (< 150 DPI source) may produce lower quality results
- The model downloads ~6GB on first run and needs ~8GB VRAM during inference

## License

MIT
