"""Keep the existing image when a newly crawled image is a near duplicate.

The script uses a Marr-Hildreth perceptual hash (MHash): a Laplacian-of-
Gaussian edge fingerprint. It is compared with Hamming distance, so resized or
recompressed copies remain close while visibly different images stay apart.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter, ImageOps


BASE_DIR = Path(__file__).resolve().parent
IMAGE_DIR = BASE_DIR / "public" / "images"
DUPLICATE_DIR = BASE_DIR / "duplicates"
CACHE_PATH = BASE_DIR / "image-mhash.json"
REPORT_PATH = BASE_DIR / "dedupe-report.json"
TAG_PATH = BASE_DIR / "public" / "image-tags.json"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".avif"}
HASH_GRID = 16
HASH_IMAGE_SIZE = HASH_GRID * 4
DEFAULT_THRESHOLD = 26


def image_paths() -> list[Path]:
    return sorted(
        (path for path in IMAGE_DIR.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS),
        key=lambda path: path.name.lower(),
    )


def signature(path: Path) -> str:
    stat = path.stat()
    return f"{stat.st_size}:{stat.st_mtime_ns}"


def mhash(path: Path) -> str:
    """Return a 256-bit Marr-Hildreth (LoG zero-crossing) perceptual hash."""
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("L")
        image = image.resize((HASH_IMAGE_SIZE, HASH_IMAGE_SIZE), Image.Resampling.LANCZOS)
        image = image.filter(ImageFilter.GaussianBlur(radius=1.55))

    # Pillow 14 replaces getdata() with get_flattened_data(). Keep support for
    # the installed Pillow version while avoiding a warning in newer releases.
    flattened = getattr(image, "get_flattened_data", None)
    pixels = list(flattened() if flattened else image.getdata())
    laplacian = [[0] * HASH_IMAGE_SIZE for _ in range(HASH_IMAGE_SIZE)]
    for y in range(1, HASH_IMAGE_SIZE - 1):
        row = y * HASH_IMAGE_SIZE
        for x in range(1, HASH_IMAGE_SIZE - 1):
            center = pixels[row + x]
            laplacian[y][x] = (
                pixels[row + x - 1]
                + pixels[row + x + 1]
                + pixels[row - HASH_IMAGE_SIZE + x]
                + pixels[row + HASH_IMAGE_SIZE + x]
                - 4 * center
            )

    bits: list[str] = []
    block = HASH_IMAGE_SIZE // HASH_GRID
    for gy in range(HASH_GRID):
        for gx in range(HASH_GRID):
            crossings = 0
            for y in range(gy * block + 1, (gy + 1) * block - 1):
                for x in range(gx * block + 1, (gx + 1) * block - 1):
                    value = laplacian[y][x]
                    if (value * laplacian[y][x + 1] < 0) or (value * laplacian[y + 1][x] < 0):
                        crossings += 1
            bits.append("1" if crossings >= 2 else "0")
    return f"{int(''.join(bits), 2):064x}"


def distance(hash_a: str, hash_b: str) -> int:
    return (int(hash_a, 16) ^ int(hash_b, 16)).bit_count()


def read_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def unique_duplicate_path(path: Path) -> Path:
    DUPLICATE_DIR.mkdir(exist_ok=True)
    candidate = DUPLICATE_DIR / path.name
    number = 2
    while candidate.exists():
        candidate = DUPLICATE_DIR / f"{path.stem}_{number}{path.suffix}"
        number += 1
    return candidate


def tagged_filenames() -> set[str]:
    data = read_json(TAG_PATH, {})
    return {str(item.get("image_id")) for item in data.get("items", []) if item.get("image_id")}


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove newly crawled near-duplicate images using MHash.")
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD, help="Maximum MHash Hamming distance (default: 26).")
    args = parser.parse_args()
    if args.threshold < 0 or args.threshold > HASH_GRID * HASH_GRID:
        raise SystemExit("threshold must be between 0 and 256")
    if not IMAGE_DIR.exists():
        raise SystemExit(f"Image folder not found: {IMAGE_DIR}")

    paths = image_paths()
    cached = read_json(CACHE_PATH, {}).get("images", [])
    cached_by_name = {item.get("filename"): item for item in cached if item.get("filename") and item.get("mhash")}
    accepted: dict[str, dict[str, str]] = {}
    candidates: list[Path] = []

    for path in paths:
        old = cached_by_name.get(path.name)
        if old and old.get("signature") == signature(path):
            accepted[path.name] = {"filename": path.name, "signature": signature(path), "mhash": str(old["mhash"])}
        else:
            candidates.append(path)

    # First run: use already-tagged pictures as the known library. If nothing
    # has been tagged yet, establish a baseline without deleting existing work.
    if not cached_by_name:
        tagged = tagged_filenames()
        seed_paths = [path for path in candidates if path.name in tagged]
        if not seed_paths:
            for path in candidates:
                accepted[path.name] = {"filename": path.name, "signature": signature(path), "mhash": mhash(path)}
            write_json(CACHE_PATH, {"algorithm": "marr-hildreth-mhash", "hash_bits": 256, "images": list(accepted.values())})
            write_json(REPORT_PATH, {"generatedAt": datetime.now().isoformat(timespec="seconds"), "mode": "baseline", "kept": len(accepted), "duplicates": []})
            print(f"MHash baseline created for {len(accepted)} images. Future crawls will be compared before tagging.")
            return
        for path in seed_paths:
            accepted[path.name] = {"filename": path.name, "signature": signature(path), "mhash": mhash(path)}
        candidates = [path for path in candidates if path.name not in accepted]

    duplicates: list[dict[str, Any]] = []
    for path in candidates:
        try:
            candidate_hash = mhash(path)
        except Exception as error:
            print(f"Skipping unreadable image {path.name}: {error}")
            continue
        closest_name = ""
        closest_distance = HASH_GRID * HASH_GRID + 1
        for record in accepted.values():
            current_distance = distance(candidate_hash, record["mhash"])
            if current_distance < closest_distance:
                closest_name = record["filename"]
                closest_distance = current_distance
        if closest_distance <= args.threshold:
            target = unique_duplicate_path(path)
            shutil.move(str(path), str(target))
            duplicates.append({"new_file": path.name, "kept_file": closest_name, "distance": closest_distance, "moved_to": str(target.relative_to(BASE_DIR))})
            print(f"Near duplicate moved: {path.name} -> {target.name} (distance {closest_distance})")
        else:
            accepted[path.name] = {"filename": path.name, "signature": signature(path), "mhash": candidate_hash}
            print(f"Accepted new image: {path.name}")

    write_json(CACHE_PATH, {"algorithm": "marr-hildreth-mhash", "hash_bits": 256, "threshold": args.threshold, "images": list(accepted.values())})
    write_json(REPORT_PATH, {"generatedAt": datetime.now().isoformat(timespec="seconds"), "threshold": args.threshold, "kept": len(accepted), "duplicates": duplicates})
    print(f"MHash scan complete: {len(duplicates)} near duplicates moved, {len(accepted)} images kept.")


if __name__ == "__main__":
    main()
