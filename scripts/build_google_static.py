from __future__ import annotations

import base64
import gzip
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "google" / "data"
BASE64_RE = re.compile(r"[^A-Za-z0-9+/=]")


def read_chunk(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig").strip()
    start = text.find('push("')
    end = text.rfind('")')
    if start == -1 or end == -1 or end <= start + 6:
        raise RuntimeError(f"Cannot parse payload chunk: {path}")
    return BASE64_RE.sub("", text[start + 6 : end])


def decode_payload(prefix: str, count: int) -> str:
    chunks = [read_chunk(DATA_DIR / f"{prefix}-{index}.txt") for index in range(1, count + 1)]

    # Normal case: chunks are slices of one Base64 string. Remove accidental
    # intermediate padding/whitespace and restore padding only at the end.
    joined = "".join(chunks).replace("=", "")
    joined += "=" * (-len(joined) % 4)

    errors: list[Exception] = []
    try:
        compressed = base64.b64decode(joined, validate=False)
        return gzip.decompress(compressed).decode("utf-8")
    except Exception as exc:
        errors.append(exc)

    # Fallback for chunks that were encoded independently before being split.
    try:
        compressed_parts = []
        for chunk in chunks:
            normalized = chunk.rstrip("=")
            normalized += "=" * (-len(normalized) % 4)
            compressed_parts.append(base64.b64decode(normalized, validate=False))
        return gzip.decompress(b"".join(compressed_parts)).decode("utf-8")
    except Exception as exc:
        errors.append(exc)

    raise RuntimeError(f"Failed to decode {prefix} payload: {errors}")


def inject_terms_redirect(html: str) -> str:
    redirect = (
        "<script>"
        "if(new URLSearchParams(location.search).get('terms')==='1')"
        "{location.replace('/google/terms.html')}"
        "</script>"
    )
    if "<head>" in html:
        return html.replace("<head>", "<head>" + redirect, 1)
    return redirect + html


def main() -> None:
    main_html = inject_terms_redirect(decode_payload("ua", 9))
    terms_html = decode_payload("terms", 3)

    (ROOT / "google" / "index.html").write_text(main_html, encoding="utf-8")
    (ROOT / "google" / "terms.html").write_text(terms_html, encoding="utf-8")

    print(f"Built google/index.html: {len(main_html.encode('utf-8'))} bytes")
    print(f"Built google/terms.html: {len(terms_html.encode('utf-8'))} bytes")


if __name__ == "__main__":
    main()
