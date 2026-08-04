from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


BASE_DIR = Path(__file__).resolve().parent
IMAGE_DIR = BASE_DIR / "public" / "images"
EXCEL_PATH = BASE_DIR / "图片信息.xlsx"
OUTPUT_PATH = BASE_DIR / "public" / "gallery-data.js"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".avif"}
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def clean_cell(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def id_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        text = f"{value:.0f}"
    else:
        text = str(value).strip()
    if re.fullmatch(r"[+-]?\d+(?:\.\d+)?[eE][+-]?\d+", text):
        try:
            text = f"{Decimal(text):.0f}"
        except InvalidOperation:
            pass
    return Path(text).stem


def digits_only(value: str) -> str:
    return re.sub(r"\D+", "", value)


def title_from_filename(stem: str) -> str:
    title = re.sub(r"^\d{8,20}[-_\s]*", "", stem).strip(" -_")
    return title or "未命名建筑灵感"


def column_index(cell_ref: str) -> int:
    letters = re.sub(r"[^A-Z]", "", cell_ref.upper())
    index = 0
    for letter in letters:
        index = index * 26 + ord(letter) - ord("A") + 1
    return index - 1


def read_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        xml = archive.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ET.fromstring(xml)
    strings: list[str] = []
    for item in root.findall("m:si", NS):
        text_parts = [node.text or "" for node in item.findall(".//m:t", NS)]
        strings.append("".join(text_parts))
    return strings


def coerce_value(text: str) -> Any:
    if text == "":
        return ""
    if re.fullmatch(r"[+-]?\d+", text):
        return int(text)
    if re.fullmatch(r"[+-]?\d+\.\d+", text):
        number = float(text)
        return int(number) if number.is_integer() else number
    return text


def cell_value(cell: ET.Element, shared_strings: list[str]) -> Any:
    cell_type = cell.attrib.get("t", "")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//m:t", NS))

    value_node = cell.find("m:v", NS)
    text = value_node.text if value_node is not None and value_node.text is not None else ""
    if cell_type == "s":
        return shared_strings[int(text)] if text else ""
    return coerce_value(text)


def read_sheet_values() -> list[list[Any]]:
    with zipfile.ZipFile(EXCEL_PATH) as archive:
        shared_strings = read_shared_strings(archive)
        root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))

    rows: list[list[Any]] = []
    for row_node in root.findall(".//m:sheetData/m:row", NS):
        row: list[Any] = []
        for cell in row_node.findall("m:c", NS):
            idx = column_index(cell.attrib.get("r", "A1"))
            while len(row) <= idx:
                row.append("")
            row[idx] = cell_value(cell, shared_strings)
        rows.append(row)
    return rows


def read_rows() -> list[dict[str, Any]]:
    if not EXCEL_PATH.exists():
        raise FileNotFoundError(f"没有找到表格：{EXCEL_PATH}")

    values = read_sheet_values()
    if not values:
        return []

    headers = [str(cell).strip() if cell is not None else f"字段{idx + 1}" for idx, cell in enumerate(values[0])]
    rows: list[dict[str, Any]] = []
    for raw in values[1:]:
        if not any(cell is not None and str(cell).strip() for cell in raw):
            continue
        row = {headers[idx]: clean_cell(raw[idx]) if idx < len(raw) else "" for idx in range(len(headers))}
        first_value = raw[0] if raw else ""
        row["_raw_id"] = id_text(first_value)
        row["_digits"] = digits_only(row["_raw_id"])
        row["_prefix14"] = row["_digits"][:14]
        rows.append(row)
    return rows


def image_files() -> list[Path]:
    if not IMAGE_DIR.exists():
        raise FileNotFoundError(f"没有找到图片文件夹：{IMAGE_DIR}")
    return sorted(
        [path for path in IMAGE_DIR.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS],
        key=lambda path: path.name.lower(),
    )


def build_items() -> list[dict[str, Any]]:
    rows = read_rows()
    exact_map = {row["_raw_id"]: row for row in rows if row["_raw_id"]}
    prefix_map: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if row["_prefix14"]:
            prefix_map.setdefault(row["_prefix14"], []).append(row)

    items: list[dict[str, Any]] = []
    for index, image_path in enumerate(image_files(), start=1):
        stem = image_path.stem
        stem_digits = digits_only(stem)
        metadata = exact_map.get(stem)
        if metadata is None and stem_digits[:14]:
            candidates = prefix_map.get(stem_digits[:14], [])
            metadata = candidates[0] if candidates else None
        metadata = metadata or {}

        item = {
            "id": stem,
            "index": index,
            "filename": image_path.name,
            "image": f"image/{image_path.name}",
            "title": metadata.get("标题") or title_from_filename(stem),
            "author": metadata.get("用户名") or "未知作者",
            "likes": metadata.get("点赞数") or 0,
            "url": metadata.get("网址") or "",
            "keyword": metadata.get("关键词") or "",
            "sourceImageUrl": metadata.get("图片链接") or "",
            "time": metadata.get("时间") or stem,
            "matched": bool(metadata),
        }
        items.append(item)
    return items


def main() -> None:
    items = build_items()
    payload = {
        "title": "建筑素材灵感空间",
        "userName": "灵感策展人",
        "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(items),
        "items": items,
    }
    content = "window.GALLERY_DATA = "
    content += json.dumps(payload, ensure_ascii=False, indent=2)
    content += ";\n"
    OUTPUT_PATH.write_text(content, encoding="utf-8")
    print(f"已更新 {len(items)} 张图片：{OUTPUT_PATH}")


if __name__ == "__main__":
    main()
