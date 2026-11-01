"""Task 05 参考解法：批量压缩图片到 200KB 以内。

用法:
    python solution.py ./in -o ./out

依赖: pip install Pillow
"""

import argparse
import io
import shutil
from pathlib import Path

from PIL import Image, ImageOps

TARGET_BYTES = 200 * 1024
MAX_SIDE = 1920
MIN_QUALITY = 20
MAX_QUALITY = 95
SKIP_EXT = {".gif", ".bmp", ".svg", ".webp"}
SUPPORTED = {".jpg", ".jpeg", ".png"}


def flatten_to_rgb(im: Image.Image) -> Image.Image:
    """把任意模式转为 RGB；透明区域合成为白底，避免转 JPEG 后变黑。"""
    if im.mode == "RGBA" or (im.mode == "P" and "transparency" in im.info):
        rgba = im.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[-1])
        return bg
    if im.mode == "LA":
        rgba = im.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[-1])
        return bg
    return im.convert("RGB")


def fit_max_side(im: Image.Image, max_side: int) -> Image.Image:
    w, h = im.size
    if max(w, h) <= max_side:
        return im
    scale = max_side / max(w, h)
    return im.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)


def encode_jpeg(im: Image.Image, quality: int) -> bytes:
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def best_quality_under(im: Image.Image, target: int):
    """二分搜索：返回不超过 target 的最大质量编码结果，找不到返回 None。"""
    lo, hi = MIN_QUALITY, MAX_QUALITY
    best = None
    while lo <= hi:
        mid = (lo + hi) // 2
        data = encode_jpeg(im, mid)
        if len(data) <= target:
            best = data
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def compress_to_target(im: Image.Image, target: int) -> bytes:
    while True:
        data = best_quality_under(im, target)
        if data is not None:
            return data
        w, h = im.size
        if min(w, h) <= 64:
            # 兜底：已经很小了，用最低质量输出，避免无限循环
            return encode_jpeg(im, MIN_QUALITY)
        im = im.resize((max(1, int(w * 0.8)), max(1, int(h * 0.8))), Image.LANCZOS)


def human(size: int) -> str:
    return f"{size / 1024:.0f} KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f} MB"


def main() -> None:
    ap = argparse.ArgumentParser(description="批量压缩图片")
    ap.add_argument("src")
    ap.add_argument("-o", "--out", default="out")
    ap.add_argument("--target", type=int, default=TARGET_BYTES, help="目标字节数")
    args = ap.parse_args()

    src = Path(args.src)
    out = Path(args.out)
    if not src.is_dir():
        raise SystemExit(f"输入目录不存在: {src}")

    ok = skipped = failed = 0

    for path in sorted(src.rglob("*")):
        if not path.is_file():
            continue
        ext = path.suffix.lower()

        rel = path.relative_to(src)

        if ext not in SUPPORTED:
            if ext in SKIP_EXT:
                print(f"跳过({ext.lstrip('.')})  {rel}")
            skipped += 1
            continue

        try:
            orig_size = path.stat().st_size

            with Image.open(path) as raw:
                im = ImageOps.exif_transpose(raw)
                compliant = orig_size <= args.target and max(im.size) <= MAX_SIDE

                if compliant:
                    # 已达标：按原名复制（仅扩展名转小写），避免二次失真
                    dst = out / rel.with_suffix(path.suffix.lower())
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, dst)
                    print(f"{rel}  {human(orig_size)} -> {human(orig_size)}  OK(跳过重编码)")
                    ok += 1
                    continue

                im = fit_max_side(flatten_to_rgb(im), MAX_SIDE)
                data = compress_to_target(im, args.target)

            # 需要重编码：统一输出 JPEG
            dst = out / rel.with_suffix(".jpg")
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
            print(f"{rel}  {human(orig_size)} -> {human(len(data))}  OK")
            ok += 1

        except Exception as exc:
            failed += 1
            print(f"{rel}  失败: {type(exc).__name__}: {exc}")

    print(f"\n统计：成功 {ok} / 跳过 {skipped} / 失败 {failed}")


if __name__ == "__main__":
    main()
