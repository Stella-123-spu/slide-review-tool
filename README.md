# slide-review-tool

A tiny, dependency-light tool to **review and label a folder of slide / patch images offline**.
It turns a manifest CSV into **one self-contained `.html` file**: the reviewer opens it in any
browser (no server, no internet, no install), sees each image **pre-labelled**, clicks **Agree**
or corrects it with one click or keystroke, then **exports a CSV**. Progress is auto-saved in the
browser, so they can close and resume.

Originally built for H&E tissue-type review, but **the label set is whatever you pass in** — use it
for tissue type, stain QC, biopsy adequacy, artifact flagging, or any per-image call.

> **Try it:** clone the repo and open [`examples/demo_review.html`](examples/demo_review.html) in any
> browser — a live demo on synthetic (non-patient) tiles. Click a card to zoom, press **A** / a label /
> **U**, then **⬇ download CSV**.

## Why it's convenient

- **Emailable** — one HTML file, works fully offline; nothing to install for the reviewer.
- **Fast for non-technical reviewers** — click *Agree* or a label, or press `A` / `1‑9` / `U`; the
  page auto-advances to the next unreviewed item.
- **Resumable** — decisions are stored in the browser (localStorage); close and reopen anytime.
- **Auditable** — exports a clean CSV of every decision (agreed / changed / unsure + optional note).

## Install

Python ≥ 3.8, then:

```bash
pip install -r requirements.txt
```

`Pillow` + `pandas` are all you need for plain image files (png/jpg/tif). `openslide-python` is
**only** needed if your `image` column points at whole-slide images (`.svs`, `.ndpi`, …).

## 1) Make a manifest CSV

Only `id` and `image` are required; the rest are optional.

| column        | required | meaning                                                            |
|---------------|:--------:|--------------------------------------------------------------------|
| `id`          |    ✅    | unique id per item (shown on the card, written to the CSV)         |
| `image`       |    ✅    | path to a thumbnail (png/jpg/tif) **or** a WSI (.svs …); relative paths resolve against the manifest's folder |
| `prelabel`    |          | the pre-filled call — ideally one of `--labels` (blank = no pre-fill) |
| `description` |          | free text shown under the image (e.g. the original report text)    |
| `meta`        |          | a short extra string shown next to the id (e.g. a model score)     |
| `order`       |          | integer for the default sort — smaller shows first (e.g. put the ones you most want reviewed at the top) |

Example (`examples/demo_manifest.csv`):

```csv
id,image,prelabel,description
tile_01,images/tile_01.png,tumor,"Dense sheets of atypical cells, high N:C ratio."
tile_02,images/tile_02.png,benign,"Bland glandular tissue, no atypia."
```

## 2) Build the page

```bash
python make_review_page.py \
    --manifest examples/demo_manifest.csv \
    --labels "tumor,benign,stroma" \
    --title "Tissue review" \
    --out review.html
```

Handy options (`python make_review_page.py -h` for all):

- `--labels "a,b,c"` — the correction buttons (colours auto-assigned; first 9 get number keys).
- `--thumb-px 512 --jpeg-quality 70` — thumbnail size / compression (controls file size).
- `--thumb-cache thumbs/` — cache generated thumbnails so re-builds are instant (recommended for WSIs).
- `--default-sort {order,id,prelabel}` — initial ordering.
- `--help-text "<b>…</b>"` — replace the instructions banner.

## 3) Reviewer workflow (what to tell your collaborator)

1. Open `review.html` in a web browser (double-click; works offline).
2. Each card shows an image + its pre-label. Click the big **✓ Agree** if it looks right, or click a
   **label** button to correct it, or **Unsure**.
3. Keyboard (on the outlined card): **A** = agree, **1‑9** = the labels in order, **U** = unsure,
   **arrows** = move. It jumps to the next unreviewed card automatically.
4. Use **sort / show** in the header to focus; **agree with all remaining** bulk-accepts the rest.
5. Click **⬇ download CSV** and email it back.

## 4) Output CSV

```
id, prelabel, reviewer_call, action, note
```

`action` ∈ `default` (untouched) · `confirmed` (agreed with the pre-label) · `changed` · `unsure`.

## Whole-slide images (.svs, .ndpi, …)

Point `image` at the WSI file and the tool makes a thumbnail via openslide. For a big cohort, pass
`--thumb-cache thumbs/` once so subsequent builds are instant.

## Files

- `make_review_page.py` — the CLI generator.
- `review_template.py` — the HTML/CSS/JS engine (label-agnostic; reuse it directly if you want).
- `examples/` — a **synthetic** demo (fake tiles, no real data). Open `examples/demo_review.html`.

## ⚠️ Data & privacy — read this

The **built `.html` embeds your images** (base64). If your images are patient-derived, treat the
built page as **controlled data**: do **not** commit it and do **not** post it publicly. This repo
is meant to ship **code + the synthetic demo only** — the included `.gitignore` excludes `data/`,
`thumbs/`, WSI files and built review pages so you don't accidentally commit real slides.

## License

MIT (or your choice — add a `LICENSE` file).
