"""Task 01 参考解法：批量按拍摄日期重命名图片。

用法:
    python solution.py ./in --dry-run
    python solution.py ./in

依赖: pip install Pillow
"""

import argparse
from datetime import datetime
from pathlib import Path

from PIL import Image

IMAGE_EXT = {".jpg", ".jpeg", ".png"}
EXIF_DATETIME_ORIGINAL = 36867


def get_taken_time(path: Path) -> datetime:
    """优先 EXIF DateTimeOriginal，其次回退到文件修改时间。

    区分两种情况（这是本任务最容易做错的地方）：
    - 「能打开但没有 EXIF」 -> 回退 mtime
    - 「根本打不开，不是图片」 -> 向上抛异常，由调用方计入 failed
    如果两者混在一起，损坏文件就会被当成正常图片改名。
    """
    with Image.open(path) as im:  # 打不开就抛，由调用方计入失败
        try:
            raw = im.getexif().get(EXIF_DATETIME_ORIGINAL)
            if raw:
                return datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S")
        except (ValueError, TypeError):
            pass
    return datetime.fromtimestamp(path.stat().st_mtime)


def build_name(stem: str, suffix: str, root: Path, used: set) -> str:
    name = f"{stem}{suffix}"
    n = 1
    while name in used or (root / name).exists():
        name = f"{stem}_{n}{suffix}"
        n += 1
    return name


def main() -> None:
    ap = argparse.ArgumentParser(description="按拍摄日期批量重命名图片")
    ap.add_argument("dir", help="图片所在目录")
    ap.add_argument("--dry-run", action="store_true", help="只打印，不改名")
    args = ap.parse_args()

    root = Path(args.dir)
    if not root.is_dir():
        raise SystemExit(f"目录不存在: {root}")

    ok = skipped = failed = 0
    used: set = set()

    for path in sorted(root.iterdir()):
        if not path.is_file():
            continue

        if path.suffix.lower() not in IMAGE_EXT:
            skipped += 1
            continue

        try:
            dt = get_taken_time(path)
        except Exception as exc:
            failed += 1
            print(f"[失败] {path.name}: 无法打开（{type(exc).__name__}）")
            continue

        stem = dt.strftime("%Y%m%d_%H%M%S")
        # 幂等：已经符合本规则命名的文件直接跳过，
        # 否则重复运行会把 *_1 再改成 *_2
        if path.stem == stem or path.stem.startswith(stem + "_"):
            ok += 1
            continue

        new_name = build_name(stem, path.suffix.lower(), root, used)
        used.add(new_name)

        if args.dry_run:
            print(f"[dry-run] {path.name} -> {new_name}")
        else:
            try:
                path.rename(root / new_name)
                print(f"{path.name} -> {new_name}")
            except OSError as exc:
                failed += 1
                print(f"[失败] {path.name}: {exc}")
                continue

        ok += 1

    print(f"\n统计：成功 {ok} / 跳过 {skipped} / 失败 {failed}")


if __name__ == "__main__":
    main()
