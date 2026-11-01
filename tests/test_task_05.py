"""Task 05 验收测试：批量压缩图片到 200KB 以内。

难点不在主逻辑，而在边界：
透明通道、已达标文件不许重编码、不许死循环、不许改动原文件。
"""

import os

from PIL import Image

from helpers import ensure_out, run_task

TARGET = 200 * 1024
MAX_SIDE = 1920


def _noise_rgb(size):
    w, h = size
    return Image.frombytes("RGB", (w, h), os.urandom(w * h * 3))


def _big_jpeg(path):
    """随机噪声图 —— 压缩收益最低，最能压出问题。"""
    _noise_rgb((2400, 1600)).save(path, "JPEG", quality=95)
    return path


def _small_png(path):
    """已达标：小尺寸 + 低体积，应原样复制。"""
    Image.new("RGB", (800, 600), (30, 90, 200)).save(path, "PNG")
    return path


def _transparent_png(path):
    """带透明通道且体积超标，必须白底合成后转 JPEG。"""
    w = h = 1200
    im = Image.frombytes("RGBA", (w, h), os.urandom(w * h * 4))
    px = im.load()
    for x in range(80):
        for y in range(80):
            px[x, y] = (0, 0, 0, 0)  # 左上角完全透明
    im.save(path, "PNG")
    return path


def _snapshot(root):
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            st = p.stat()
            out[str(p.relative_to(root))] = (st.st_size, int(st.st_mtime))
    return out


def test_big_image_compressed_under_target(tmp_path):
    """5MB 级别的噪声图必须被压到 200KB 以内，且最长边 ≤1920。"""
    src = tmp_path / "in"
    src.mkdir()
    _big_jpeg(src / "big.jpg")

    ensure_out(run_task("05", src, "-o", tmp_path / "out"))

    produced = tmp_path / "out" / "big.jpg"
    assert produced.exists(), "未生成输出文件"
    assert produced.stat().st_size <= TARGET, f"压缩后仍为 {produced.stat().st_size} 字节"
    with Image.open(produced) as im:
        assert max(im.size) <= MAX_SIDE, im.size


def test_compliant_file_not_reencoded(tmp_path):
    """已达标的小图必须原样复制（字节完全相同），不做二次编码。"""
    src = tmp_path / "in"
    src.mkdir()
    small = _small_png(src / "small.png")
    before = small.read_bytes()

    ensure_out(run_task("05", src, "-o", tmp_path / "out"))

    produced = tmp_path / "out" / "small.png"
    assert produced.exists(), "达标文件应保留原扩展名"
    assert produced.read_bytes() == before, "达标文件被重新编码了"


def test_transparent_area_becomes_white(tmp_path):
    """透明 PNG 转 JPEG 后，透明区域必须是白色，不能是黑色。"""
    src = tmp_path / "in"
    src.mkdir()
    _transparent_png(src / "logo.png")

    ensure_out(run_task("05", src, "-o", tmp_path / "out"))

    produced = tmp_path / "out" / "logo.jpg"
    assert produced.exists(), "透明 PNG 应被转为 JPEG"
    with Image.open(produced) as im:
        r, g, b = im.convert("RGB").getpixel((0, 0))
    assert min(r, g, b) >= 245, f"透明区域变成了 {(r, g, b)}，应该是白色"


def test_gif_skipped(tmp_path):
    """动图 GIF 必须跳过，不出现在输出目录。"""
    src = tmp_path / "in"
    src.mkdir()
    frames = [Image.new("RGB", (60, 60), c) for c in [(255, 0, 0), (0, 255, 0)]]
    frames[0].save(src / "anim.gif", save_all=True, append_images=frames[1:], duration=100)

    res = ensure_out(run_task("05", src, "-o", tmp_path / "out"))
    assert not (tmp_path / "out" / "anim.gif").exists()
    assert "跳过" in res.stdout


def test_originals_untouched(tmp_path):
    """原目录下所有文件的大小与 mtime 都不能变。"""
    src = tmp_path / "in"
    src.mkdir()
    _big_jpeg(src / "big.jpg")
    _small_png(src / "small.png")
    before = _snapshot(src)

    ensure_out(run_task("05", src, "-o", tmp_path / "out"))

    assert _snapshot(src) == before, "原文件被修改了"


def test_subdirectory_structure_preserved(tmp_path):
    """输出的相对目录结构必须与输入一致（不能压平）。"""
    src = tmp_path / "in"
    (src / "sub" / "deeper").mkdir(parents=True)
    _big_jpeg(src / "sub" / "deeper" / "photo.JPG")

    ensure_out(run_task("05", src, "-o", tmp_path / "out"))

    assert (tmp_path / "out" / "sub" / "deeper" / "photo.jpg").exists()


def test_output_within_target_and_max_side(tmp_path):
    """所有需要重编码的输出都必须同时满足体积与尺寸约束。"""
    src = tmp_path / "in"
    src.mkdir()
    _big_jpeg(src / "a.jpg")
    _transparent_png(src / "b.png")

    ensure_out(run_task("05", src, "-o", tmp_path / "out"))

    for p in (tmp_path / "out").rglob("*.jpg"):
        assert p.stat().st_size <= TARGET, f"{p.name} 超体积"
        with Image.open(p) as im:
            assert max(im.size) <= MAX_SIDE, f"{p.name} 超尺寸"


def test_no_infinite_loop(tmp_path):
    """极端小目标（1KB）也不能死循环：必须有缩小次数兜底。"""
    src = tmp_path / "in"
    src.mkdir()
    _big_jpeg(src / "big.jpg")

    res = run_task("05", src, "-o", tmp_path / "out", "--target", "1024", timeout=120)
    ensure_out(res, "tiny-target")
    assert (tmp_path / "out" / "big.jpg").exists()
