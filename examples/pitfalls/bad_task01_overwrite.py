"""反面教材 2：模拟「能跑但违反约束」的错误实现（task-01）。

典型错误：
1. 用 `os.rename` 直接改名 —— 同名即覆盖，静默丢文件
2. `--dry-run` 只打印，但仍然执行了改名
3. 损坏文件无法解析时仍用 mtime 改名，而不是计入 failed
4. 无幂等性 —— 第二次运行会把文件继续改成 _1、_2

期望结果：harness 打分 < 100，并命中「不覆盖」「dry-run」「failed 计数」等验收项。
"""

import argparse
import os
import time
from pathlib import Path

from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("dir")
ap.add_argument("--dry-run", action="store_true")
args = ap.parse_args()

root = Path(args.dir)
for path in sorted(root.iterdir()):
    if not path.is_file():
        continue
    if path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        continue

    stamp = time.strftime("%Y%m%d_%H%M%S", time.localtime(path.stat().st_mtime))
    try:
        with Image.open(path) as im:
            raw = im.getexif().get(36867)
        if raw:
            stamp = str(raw).replace(":", "").replace(" ", "_")
            stamp = f"{stamp[:8]}_{stamp[9:]}"
    except Exception:
        pass                                # ← 错误 3：损坏文件也照样改名

    target = root / f"{stamp}{path.suffix.lower()}"
    if args.dry_run:
        print(f"[dry-run] {path.name} -> {target.name}")
    os.rename(path, target)                 # ← 错误 2：dry-run 也执行
                                            # ← 错误 1：目标存在即覆盖
