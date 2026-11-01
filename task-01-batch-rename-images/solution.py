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
    """优先 EXIF DateTimeOriginal，失败则回退到文件修改时间。"""
    try:
        with Image.open(path) as im:
            raw = im.getexif().get(EXIF_DATETIME_ORIGINAL)
            if raw:
                return datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S")
    except Exception:
        # 损坏文件 / 无 EXIF / 不是图片，统一走回退逻辑
        pass
    return datetime.fromtimestamp(path.stat().st_mtime)


def build_name(dt: datetime, suffix: str, root: Path, used: set) -> str:
    stem = dt.strftime("%Y%m%d_%H%M%S")
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
        except Exception:
            failed += 1
            print(f"[失败] {path.name}: 无法读取时间")
            continue

        try:
            new_name = build_name(dt, path.suffix.lower(), root, used)
        except Exception:
            failed += 1
            continue

        # 幂等：目标名与原名相同则不做事
        if new_name == path.name:
            ok += 1
            continue

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
