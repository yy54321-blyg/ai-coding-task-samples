"""Task 01 验收测试：按拍摄日期批量重命名图片。

这些测试会在实现有缺陷时失败 —— 例如把损坏文件也用 mtime 改名，
或者 --dry-run 实际上仍然写了磁盘。
"""

import os
import time
from datetime import datetime

from PIL import Image

from helpers import ensure_out, run_task

EXIF_TAG_DATETIME_ORIGINAL = 36867


def _make_jpeg(path, dt_str=None):
    """生成一张 JPEG，可选写入 EXIF DateTimeOriginal。"""
    im = Image.new("RGB", (24, 24), (180, 40, 40))
    kwargs = {}
    if dt_str:
        exif = im.getexif()
        exif[EXIF_TAG_DATETIME_ORIGINAL] = dt_str
        kwargs["exif"] = exif
    im.save(path, "JPEG", **kwargs)
    return path


def _set_mtime(path, dt: datetime):
    ts = dt.timestamp()
    os.utime(path, (ts, ts))


def _build_case(root):
    """按 task.md 的输入示例构造用例。"""
    _make_jpeg(root / "a.jpg", "2024:05:01 10:20:30")
    _make_jpeg(root / "c.jpg", "2024:05:01 10:20:30")  # 与 a.jpg 同秒
    _make_jpeg(root / "d.JPG", "2024:05:03 09:00:00")  # 大写扩展名

    b = root / "b.png"
    Image.new("RGB", (24, 24), (20, 60, 160)).save(b, "PNG")  # 无 EXIF
    _set_mtime(b, datetime(2024, 5, 2, 8, 0, 0))

    (root / "note.txt").write_text("not an image", encoding="utf-8")
    (root / "broken.jpg").write_bytes(b"\x00\x01\x02not-a-real-jpeg")  # 损坏


def _snapshot(root):
    """目录快照：文件名 -> (size, mtime)，用于判断“是否被改动”。"""
    return {
        p.name: (p.stat().st_size, int(p.stat().st_mtime))
        for p in sorted(root.iterdir())
        if p.is_file()
    }


def test_rename_produces_expected_names(tmp_path):
    """给定输入，输出文件名集合必须完全一致。"""
    _build_case(tmp_path)
    res = ensure_out(run_task("01", tmp_path), "task01")

    names = {p.name for p in tmp_path.iterdir() if p.is_file()}
    assert "20240501_102030.jpg" in names
    assert "20240501_102030_1.jpg" in names, "同秒冲突必须追加 _1，而不是覆盖"
    assert "20240502_080000.png" in names
    assert "20240503_090000.jpg" in names, "大写 .JPG 也要能处理并统一为小写"
    assert "note.txt" in names
    assert "broken.jpg" in names, "损坏文件不应被改名"

    assert "成功 4" in res.stdout, res.stdout
    assert "跳过 1" in res.stdout, res.stdout
    assert "失败 1" in res.stdout, res.stdout


def test_no_file_is_overwritten(tmp_path):
    """同秒冲突时两个文件都必须存在（不能一个把另一个覆盖掉）。"""
    _build_case(tmp_path)
    ensure_out(run_task("01", tmp_path))
    jpgs = [
        p for p in tmp_path.iterdir()
        if p.suffix.lower() == ".jpg" and p.name != "broken.jpg"
    ]
    # a.jpg / c.jpg / d.JPG = 3 个源文件 -> 必须有 3 个 jpg 输出
    assert len(jpgs) == 3, [p.name for p in jpgs]


def test_dry_run_changes_nothing(tmp_path):
    """--dry-run 下文件名与 mtime 都不能变。"""
    _build_case(tmp_path)
    before = _snapshot(tmp_path)
    ensure_out(run_task("01", tmp_path, "--dry-run"))
    after = _snapshot(tmp_path)
    assert before == after, "--dry-run 实际修改了文件"


def test_idempotent_on_second_run(tmp_path):
    """对同一目录重复运行，文件名不再变化（幂等）。"""
    _build_case(tmp_path)
    ensure_out(run_task("01", tmp_path))
    first = _snapshot(tmp_path)
    ensure_out(run_task("01", tmp_path))
    second = _snapshot(tmp_path)
    assert set(first) == set(second), (
        f"第二次运行又改了名字\n第一次: {sorted(first)}\n第二次: {sorted(second)}"
    )


def test_non_image_skipped(tmp_path):
    """非图片文件必须原样保留，且计入 skipped。"""
    _build_case(tmp_path)
    res = ensure_out(run_task("01", tmp_path))
    assert (tmp_path / "note.txt").read_text(encoding="utf-8") == "not an image"
    assert "跳过 1" in res.stdout


def test_broken_file_does_not_abort(tmp_path):
    """损坏文件应计入 failed，且后续文件仍然被处理。"""
    _build_case(tmp_path)
    res = ensure_out(run_task("01", tmp_path))
    assert "失败 1" in res.stdout, res.stdout
    assert (tmp_path / "20240503_090000.jpg").exists(), "损坏文件之后的文件也应被处理"


def test_exif_missing_falls_back_to_mtime(tmp_path):
    """无 EXIF 的图片回退到 mtime，不报错。"""
    p = tmp_path / "noexif.png"
    Image.new("RGB", (24, 24), (10, 10, 10)).save(p, "PNG")
    _set_mtime(p, datetime(2023, 12, 31, 23, 59, 58))

    ensure_out(run_task("01", tmp_path))
    assert (tmp_path / "20231231_235958.png").exists()


def test_reports_exif_time_not_mtime(tmp_path):
    """有 EXIF 时必须用 EXIF 时间，而不是文件修改时间。"""
    p = _make_jpeg(tmp_path / "x.jpg", "2024:01:02 03:04:05")
    _set_mtime(p, datetime(2025, 6, 6, 6, 6, 6))

    ensure_out(run_task("01", tmp_path))
    assert (tmp_path / "20240102_030405.jpg").exists(), "应使用 EXIF 时间而非 mtime"
