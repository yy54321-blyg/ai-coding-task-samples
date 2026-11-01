"""Task 04 参考解法：检查 Markdown 中的外部链接是否失效。

用法:
    python solution.py ./docs -o dead-links.csv

依赖: pip install requests
"""

import argparse
import csv
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

# !? 兼容图片；url 用 [^)\s]+ 避免贪婪跨行
LINK_RE = re.compile(r"!?\[[^\]]*\]\((?P<url>[^)\s]+)\)")

TIMEOUT = 5
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; md-link-checker/1.0)"}
SKIP_PREFIXES = ("#", "mailto:", "tel:", "javascript:", "data:")


def iter_markdown(root: Path):
    if root.is_file():
        yield root
        return
    yield from sorted(root.rglob("*.md"))


def is_external(url: str) -> bool:
    return url.startswith(("http://", "https://"))


def check_url(url: str):
    """返回 (status, error)；有效返回 (None, None)。"""
    try:
        resp = requests.head(
            url, timeout=TIMEOUT, allow_redirects=True, headers=HEADERS
        )
        # 很多站点拒绝 HEAD，需回退 GET
        if resp.status_code in (403, 405, 501):
            resp = requests.get(
                url,
                timeout=TIMEOUT,
                allow_redirects=True,
                headers=HEADERS,
                stream=True,
            )

        if 200 <= resp.status_code < 400:
            return None, None
        return resp.status_code, ""
    except Exception as exc:
        return "ERR", type(exc).__name__


def main() -> None:
    ap = argparse.ArgumentParser(description="检查 Markdown 外部链接")
    ap.add_argument("path", help="md 文件或目录")
    ap.add_argument("-o", "--out", default="dead-links.csv")
    ap.add_argument("--workers", type=int, default=20)
    args = ap.parse_args()

    root = Path(args.path)
    if not root.exists():
        raise SystemExit(f"路径不存在: {root}")

    # 收集: url -> [(file, line), ...]
    found: dict = {}
    for md in iter_markdown(root):
        try:
            text = md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for m in LINK_RE.finditer(line):
                url = m.group("url").strip()
                if not is_external(url):
                    continue
                found.setdefault(url, []).append((str(md), lineno))

    urls = list(found)
    print(f"共发现 {len(urls)} 个待检查的外部链接，并发 {args.workers} 检查中…")

    dead = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(check_url, urls))

    for url, (status, error) in zip(urls, results):
        if status is None:
            continue
        for file, lineno in found[url]:
            dead.append(
                {"file": file, "line": lineno, "url": url, "status": status, "error": error}
            )

    dead.sort(key=lambda r: (r["file"], r["line"]))

    with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["file", "line", "url", "status", "error"]
        )
        writer.writeheader()
        writer.writerows(dead)

    print(f"死链 {len(dead)} 条 -> {args.out}")


if __name__ == "__main__":
    main()
