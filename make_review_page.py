#!/usr/bin/env python3
"""Build a self-contained, offline HTML review page from a manifest CSV.

The reviewer opens ONE .html file in a browser (no server, no internet, no install),
sees each item's image pre-labelled, clicks Agree or corrects it, then exports a CSV.
Nothing dataset-specific lives here — you define the label set on the command line.

Manifest CSV columns (only `id` and `image` are required):
  id           unique id per item                       (required)
  image        path to a thumbnail (png/jpg/tif) OR a WSI (.svs/.tiff) ; relative
               paths are resolved against the manifest's folder                (required)
  prelabel     the pre-filled call (should be one of --labels, or blank)   (optional)
  description  free text shown on the card                                 (optional)
  meta         a short extra string shown by the id (e.g. a score)         (optional)
  order        integer for the default sort (smaller = shown first)        (optional)

Example:
  python make_review_page.py --manifest examples/demo_manifest.csv \\
      --labels "tumor,benign,stroma" --title "Tissue review" --out review.html

WSIs (.svs etc.) need `openslide-python`; plain image files only need Pillow.
"""
import argparse, os, io, base64, sys
import pandas as pd
from PIL import Image

import review_template as tpl

_OPENSLIDE = None  # lazy


def _thumb_from_wsi(path, px):
    global _OPENSLIDE
    if _OPENSLIDE is None:
        import openslide  # only needed for WSIs
        _OPENSLIDE = openslide
    s = _OPENSLIDE.OpenSlide(path)
    im = s.get_thumbnail((px, px)).convert("RGB")
    s.close()
    return im


def image_b64(path, px, quality, cache_dir=None):
    key = None
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        key = os.path.join(cache_dir, os.path.splitext(os.path.basename(path))[0] + f"_{px}.jpg")
        if os.path.exists(key):
            return base64.b64encode(open(key, "rb").read()).decode()
    ext = os.path.splitext(path)[1].lower()
    if ext in (".svs", ".ndpi", ".scn", ".mrxs", ".tiff", ".tif", ".vms", ".vmu"):
        try:
            im = _thumb_from_wsi(path, px)
        except Exception:
            im = Image.open(path).convert("RGB")   # tif that PIL can read directly
    else:
        im = Image.open(path).convert("RGB")
    im.thumbnail((px, px))
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=quality)
    data = buf.getvalue()
    if key:
        open(key, "wb").write(data)
    return base64.b64encode(data).decode()


def main():
    ap = argparse.ArgumentParser(description="Build an offline HTML review page from a manifest CSV.")
    ap.add_argument("--manifest", required=True, help="CSV with columns id,image[,prelabel,description,meta,order]")
    ap.add_argument("--labels", required=True, help='comma-separated correction buttons, e.g. "tumor,benign,stroma"')
    ap.add_argument("--out", default="review.html")
    ap.add_argument("--title", default="Slide review")
    ap.add_argument("--help-text", default="", help="custom instructions banner (HTML allowed)")
    ap.add_argument("--thumb-px", type=int, default=512)
    ap.add_argument("--jpeg-quality", type=int, default=70)
    ap.add_argument("--thumb-cache", default="", help="optional dir to cache generated thumbnails")
    ap.add_argument("--id-col", default="id")
    ap.add_argument("--image-col", default="image")
    ap.add_argument("--storage-key", default="", help="localStorage key (default: derived from --out)")
    ap.add_argument("--default-sort", default="order", choices=["order", "id", "prelabel"])
    a = ap.parse_args()

    labels = [x.strip() for x in a.labels.split(",") if x.strip()]
    if not labels:
        sys.exit("--labels is empty")
    df = pd.read_csv(a.manifest)
    for col in (a.id_col, a.image_col):
        if col not in df.columns:
            sys.exit(f"manifest is missing required column '{col}' (have: {list(df.columns)})")
    base_dir = os.path.dirname(os.path.abspath(a.manifest))

    def _get(row, name):
        return row[name] if name in df.columns and pd.notna(row[name]) else ""

    cards, ok, miss = [], 0, 0
    for _, r in df.iterrows():
        img = str(r[a.image_col])
        path = img if os.path.isabs(img) else os.path.join(base_dir, img)
        if not os.path.exists(path):
            print(f"  MISSING image, skipped: {path}"); miss += 1; continue
        try:
            b64 = image_b64(path, a.thumb_px, a.jpeg_quality, a.thumb_cache or None)
        except Exception as e:
            print(f"  FAILED {path}: {repr(e)[:70]}"); miss += 1; continue
        item = {"id": _get(r, a.id_col), "prelabel": _get(r, "prelabel"),
                "description": _get(r, "description"), "meta": _get(r, "meta"),
                "order": int(r["order"]) if "order" in df.columns and pd.notna(r["order"]) else ok}
        cards.append(tpl.card_html(item, labels, b64)); ok += 1
        if ok % 100 == 0:
            print(f"  ...{ok} images")
    print(f"embedded {ok}, skipped {miss}")

    key = a.storage_key or ("rev_" + os.path.splitext(os.path.basename(a.out))[0])
    help_text = a.help_text or (
        "<b>How to review:</b> each item shows a pre-label. Click the big "
        "<span class='pill'>✓ Agree</span> if it looks right, or click a label button to correct it. "
        "<b>Faster:</b> the <b>outlined</b> card takes keys — <b>A</b>=agree, <b>1..9</b>=labels, "
        "<b>U</b>=unsure — and jumps to the next. When done, click <b>⬇ download CSV</b> and send it back. "
        "Your progress is saved in the browser, so you can close and resume.")
    page = tpl.build_page("\n".join(cards), labels, a.title, help_text, key, a.default_sort)
    with open(a.out, "w") as f:
        f.write(page)
    print(f"[saved] {a.out}  ({os.path.getsize(a.out)/1e6:.1f} MB)  labels={labels}")


if __name__ == "__main__":
    main()
