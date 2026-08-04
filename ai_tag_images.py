from __future__ import annotations

import argparse
import base64
import http.client
import json
import mimetypes
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
PROMPT_PATH = BASE_DIR / "提示词.txt"
GALLERY_DATA_PATH = BASE_DIR / "public" / "gallery-data.js"
TAGS_JSON_PATH = BASE_DIR / "public" / "image-tags.json"
TAGS_JS_PATH = BASE_DIR / "public" / "image-tags.js"
LOG_PATH = BASE_DIR / "ai_tag_log.txt"
CACHE_DIR = BASE_DIR / ".ai_tag_cache"
MODEL_NAME = "qwen3-vl-plus"
MAX_IMAGE_SIDE = 960
REQUEST_TIMEOUT = 180
REQUEST_RETRIES = 2
CONFIG_CANDIDATES = [
    "ai_config.json",
    "api_config.json",
    "bailian_config.json",
    "dashscope_config.json",
    "config.json",
    ".env",
    "api_key.txt",
]


def log(message: str) -> None:
    text = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    print(text, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(text + "\n")


def read_js_object(path: Path, prefix: str) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8").strip()
    if text.startswith(prefix):
        text = text[len(prefix) :].strip()
    if text.endswith(";"):
        text = text[:-1].strip()
    return json.loads(text) if text else {}


def read_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8").strip()
    return json.loads(text) if text else {}


def write_tags(payload: dict[str, Any]) -> None:
    TAGS_JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    TAGS_JS_PATH.write_text(
        "window.IMAGE_TAGS = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )


def parse_key_value_text(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
        elif ":" in line:
            key, value = line.split(":", 1)
        else:
            continue
        result[key.strip()] = value.strip().strip("'\"")
    return result


def load_config(config_path: str | None = None) -> dict[str, str]:
    candidates = [Path(config_path)] if config_path else [BASE_DIR / name for name in CONFIG_CANDIDATES]
    file_config: dict[str, Any] = {}
    used_path: Path | None = None
    for path in candidates:
        if not path.exists():
            continue
        used_path = path
        text = path.read_text(encoding="utf-8").strip()
        if path.suffix.lower() == ".json":
            file_config = json.loads(text)
        else:
            file_config = parse_key_value_text(text)
        break

    api_key = (
        file_config.get("api_key")
        or file_config.get("apikey")
        or file_config.get("key")
        or file_config.get("DASHSCOPE_API_KEY")
        or os.getenv("DASHSCOPE_API_KEY")
    )
    base_url = (
        file_config.get("base_url")
        or file_config.get("baseURL")
        or file_config.get("api_url")
        or file_config.get("url")
        or file_config.get("DASHSCOPE_BASE_URL")
        or os.getenv("DASHSCOPE_BASE_URL")
    )

    if not api_key or not base_url:
        searched = ", ".join(str(path.name) for path in candidates)
        raise SystemExit(
            "没有找到可用的 API 配置。请把配置文件放到图片库目录，或运行时用 --config 指定。\n"
            f"已搜索：{searched}\n"
            "配置示例见 ai_config.example.json。"
        )

    return {"api_key": str(api_key), "base_url": str(base_url), "config_path": str(used_path or "环境变量")}


def endpoint_from_base_url(base_url: str) -> str:
    url = base_url.strip().rstrip("/")
    if url.endswith("/chat/completions"):
        return url
    return url + "/chat/completions"


def prepared_image_path(path: Path) -> Path:
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return path

    CACHE_DIR.mkdir(exist_ok=True)
    cache_path = CACHE_DIR / f"{path.stem}_{MAX_IMAGE_SIDE}.jpg"
    if cache_path.exists() and cache_path.stat().st_mtime >= path.stat().st_mtime:
        return cache_path

    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
        image.save(cache_path, format="JPEG", quality=84, optimize=True)
    return cache_path


def image_data_url(path: Path) -> str:
    prepared_path = prepared_image_path(path)
    mime = mimetypes.guess_type(prepared_path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(prepared_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


def normalize_tag(raw: dict[str, Any], image_id: str) -> dict[str, Any]:
    item = raw.get("items", [raw])[0] if isinstance(raw.get("items"), list) else raw
    return {
        "image_id": image_id,
        "space_type": str(item.get("space_type") or "未分类建筑类型"),
        "design_style": str(item.get("design_style") or "未分类设计风格"),
        "materials": item.get("materials") if isinstance(item.get("materials"), list) else [],
        "color_tone": str(item.get("color_tone") or "未提取色彩特征"),
        "scene_usage": str(item.get("scene_usage") or "未分类场景用途"),
        "keywords": item.get("keywords") if isinstance(item.get("keywords"), list) else [],
    }


def perform_request(request: urllib.request.Request, image_id: str, timeout: int, retries: int) -> dict[str, Any]:
    retryable_errors = (
        TimeoutError,
        socket.timeout,
        ConnectionResetError,
        http.client.RemoteDisconnected,
        urllib.error.URLError,
    )
    for attempt in range(1, retries + 2):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code in {429, 500, 502, 503, 504} and attempt <= retries:
                log(f"{image_id} 接口暂时失败，准备重试 {attempt}/{retries}：HTTP {exc.code}")
                time.sleep(2 * attempt)
                continue
            raise RuntimeError(f"{image_id} 打标失败：HTTP {exc.code} {detail}") from exc
        except retryable_errors as exc:
            if attempt <= retries:
                log(f"{image_id} 连接中断，准备重试 {attempt}/{retries}：{exc}")
                time.sleep(2 * attempt)
                continue
            raise RuntimeError(f"{image_id} 打标失败：{exc}") from exc
    raise RuntimeError(f"{image_id} 打标失败：超过重试次数")


def call_qwen(
    endpoint: str,
    api_key: str,
    prompt: str,
    image_path: Path,
    image_id: str,
    timeout: int,
    retries: int,
) -> dict[str, Any]:
    task_prompt = (
        prompt
        + "\n\n本次只分析一张图片。请将 image_id 固定为："
        + image_id
        + "\n只返回一个标准 JSON 对象，items 数组中只能包含这一张图片。"
    )
    body = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_data_url(image_path)}},
                    {"type": "text", "text": task_prompt},
                ],
            }
        ],
        "temperature": 0.2,
        "max_tokens": 1200,
        "enable_thinking": False,
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    result = perform_request(request, image_id, timeout, retries)
    content = result["choices"][0]["message"]["content"]
    return normalize_tag(extract_json(content), image_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="使用 qwen3-vl-plus 为图片灵感库自动打标。")
    parser.add_argument("--config", help="API 配置文件路径。未提供时自动搜索图片库目录里的常见配置文件。")
    parser.add_argument("--force", action="store_true", help="重新打标所有图片；默认跳过已有标签的图片。")
    parser.add_argument("--limit", type=int, default=0, help="只处理前 N 张待打标图片，0 表示不限制。")
    parser.add_argument("--pause", action="store_true", help="运行结束后等待回车，适合双击运行时查看结果。")
    parser.add_argument("--timeout", type=int, default=REQUEST_TIMEOUT, help="单张图片接口等待秒数。")
    parser.add_argument("--retries", type=int, default=REQUEST_RETRIES, help="单张图片失败后的重试次数。")
    parser.add_argument("--skip-failed", action="store_true", help="跳过上次已经失败的图片，先处理其他图片。")
    args = parser.parse_args()

    LOG_PATH.write_text("", encoding="utf-8")
    if not PROMPT_PATH.exists():
        raise SystemExit("没有找到提示词.txt")
    if not GALLERY_DATA_PATH.exists():
        raise SystemExit("没有找到 gallery-data.js，请先运行 update_gallery.py")

    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    config = load_config(args.config)
    endpoint = endpoint_from_base_url(config["base_url"])
    gallery_data = read_js_object(GALLERY_DATA_PATH, "window.GALLERY_DATA = ")
    existing_payload = (
        read_js_object(TAGS_JS_PATH, "window.IMAGE_TAGS = ")
        if TAGS_JS_PATH.exists()
        else read_json_object(TAGS_JSON_PATH)
    )
    existing_items = existing_payload.get("items") if isinstance(existing_payload.get("items"), list) else []
    existing_failed = existing_payload.get("failed") if isinstance(existing_payload.get("failed"), list) else []
    failed_ids = {item.get("image_id") for item in existing_failed if item.get("image_id")}
    tags_by_id = {item.get("image_id"): item for item in existing_items if item.get("image_id")}

    gallery_items = gallery_data.get("items") if isinstance(gallery_data.get("items"), list) else []
    pending = [item for item in gallery_items if args.force or item.get("filename") not in tags_by_id]
    if args.skip_failed and not args.force:
        pending = [item for item in pending if item.get("filename") not in failed_ids]
    if args.limit > 0:
        pending = pending[: args.limit]

    log(f"配置来源：{config['config_path']}")
    log(f"待打标图片：{len(pending)} 张")

    failed: list[dict[str, str]] = []
    for index, item in enumerate(pending, start=1):
        image_id = item["filename"]
        image_path = BASE_DIR / "public" / "images" / Path(item["image"]).name
        if not image_path.exists():
            log(f"跳过不存在的图片：{image_id}")
            continue
        log(f"[{index}/{len(pending)}] 正在打标：{image_id}")
        try:
            tag = call_qwen(endpoint, config["api_key"], prompt, image_path, image_id, args.timeout, args.retries)
            tags_by_id[image_id] = tag
            log(f"完成：{image_id}")
        except Exception as exc:
            failed.append({"image_id": image_id, "error": str(exc)})
            log(f"失败：{image_id}；原因：{exc}")
            continue
        payload = {
            "model": MODEL_NAME,
            "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "items": list(tags_by_id.values()),
            "failed": failed,
        }
        write_tags(payload)
        time.sleep(0.4)

    payload = {
        "model": MODEL_NAME,
        "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "items": list(tags_by_id.values()),
        "failed": failed,
    }
    write_tags(payload)
    log(f"已保存标签：{TAGS_JSON_PATH}")
    if failed:
        log(f"有 {len(failed)} 张图片失败，详情见：{LOG_PATH}")
    else:
        log("全部待处理图片已完成。")

    if args.pause:
        input("运行结束，按回车关闭窗口...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("已停止。")
    except Exception as exc:
        log(f"程序异常退出：{exc}")
        if sys.stdin.isatty():
            input("程序遇到问题，按回车关闭窗口...")
        raise
