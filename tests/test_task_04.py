"""Task 04 验收测试：Markdown 外部链接检查。

用**本地 HTTP 服务器**作为被测目标，不依赖外网，测试结果确定可复现。
这是这类任务的正确做法：依赖真实外网会让验收变得不可判定。
"""

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from helpers import ensure_out, read_csv_rows, run_task


class _Handler(BaseHTTPRequestHandler):
    """模拟三种站点行为：200 / 404 / 拒绝 HEAD 但允许 GET。"""

    def do_HEAD(self):
        if self.path == "/nohead":
            self.send_response(405)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self._send()

    def do_GET(self):
        self._send()

    def _send(self):
        code = 404 if self.path.startswith("/gone") else 200
        body = b"ok"
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture()
def site():
    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    yield base
    srv.shutdown()
    srv.server_close()


def _write_md(path, base):
    text = "\n".join(
        [
            "# 标题",
            f"正常链接 [ok]({base}/ok)",
            f"死链 [bad]({base}/gone)",
            f"死链2 [bad2]({base}/gone2)",
            f"图片 ![logo]({base}/gone)",
            f"拒绝HEAD的站 [nohead]({base}/nohead)",
            "相对路径 [rel](./images/a.png)",
            "锚点 [anchor](#section)",
            "邮箱 [mail](mailto:a@b.com)",
            "电话 [tel](tel:123456)",
            f"重复死链 [dup]({base}/gone)",
        ]
    )
    md = path / "doc.md"
    md.write_text(text, encoding="utf-8")
    return md


def _run(tmp_path, base, *extra):
    _write_md(tmp_path, base)
    out = tmp_path / "dead.csv"
    res = run_task("04", tmp_path, "-o", out, *extra)
    ensure_out(res, "task04")
    return res, read_csv_rows(out)


def test_detects_404_links(tmp_path, site):
    """404 链接必须被检出。"""
    _, rows = _run(tmp_path, site)
    urls = {r["url"] for r in rows}
    assert f"{site}/gone" in urls
    assert f"{site}/gone2" in urls


def test_ignores_relative_anchor_mailto(tmp_path, site):
    """相对路径、锚点、mailto、tel 不得进入检查结果。"""
    _, rows = _run(tmp_path, site)
    urls = {r["url"] for r in rows}
    assert not any(u.startswith("./") for u in urls)
    assert not any(u.startswith("#") for u in urls)
    assert not any(u.startswith("mailto:") for u in urls)
    assert not any(u.startswith("tel:") for u in urls)


def test_head_405_falls_back_to_get(tmp_path, site):
    """返回 405 的站点应回退 GET 后判定为有效，不能误报为死链。"""
    _, rows = _run(tmp_path, site)
    urls = {r["url"] for r in rows}
    assert f"{site}/nohead" not in urls, "HEAD 405 必须回退 GET，否则误报"


def test_image_syntax_also_extracted(tmp_path, site):
    """图片语法 ![]() 也要被提取（不能只匹配 []() ）。"""
    _, rows = _run(tmp_path, site)
    urls = {r["url"] for r in rows}
    assert f"{site}/gone" in urls


def test_dedup_same_url_reported_once_per_occurrence(tmp_path, site):
    """同一 URL 出现两次，应按出现位置各记一行，但只检查一次。"""
    _, rows = _run(tmp_path, site)
    gone_rows = [r for r in rows if r["url"] == f"{site}/gone"]
    # 正文中 /gone 出现 3 次（死链、图片、重复），应全部定位到
    assert len(gone_rows) == 3, gone_rows


def test_line_number_recorded(tmp_path, site):
    """结果必须带行号，能定位到具体位置。"""
    _, rows = _run(tmp_path, site)
    assert all(r["line"].isdigit() for r in rows)
    assert min(int(r["line"]) for r in rows) >= 2


def test_status_code_recorded(tmp_path, site):
    """必须记录状态码，且 404 被记为 404 而不是 ERR。"""
    _, rows = _run(tmp_path, site)
    gone = [r for r in rows if r["url"] == f"{site}/gone"]
    assert gone[0]["status"] == "404", gone[0]


def test_unreachable_host_marked_err(tmp_path):
    """连不上的地址记为 ERR，且脚本不崩溃。"""
    md = tmp_path / "x.md"
    md.write_text("[x](http://127.0.0.1:9/none)", encoding="utf-8")
    out = tmp_path / "d.csv"
    res = run_task("04", tmp_path, "-o", out, "--workers", "4")
    ensure_out(res, "unreachable")
    rows = read_csv_rows(out)
    assert rows and rows[0]["status"] == "ERR", rows


def test_no_links_yields_empty_csv(tmp_path, site):
    """没有外链时输出空表（只有表头），退出码 0。"""
    md = tmp_path / "empty.md"
    md.write_text("纯文本，没有链接。\n[锚点](#a)\n", encoding="utf-8")
    out = tmp_path / "d.csv"
    res = run_task("04", tmp_path, "-o", out)
    ensure_out(res)
    assert read_csv_rows(out) == []
