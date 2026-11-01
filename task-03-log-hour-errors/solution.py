"""Task 03 参考解法：按小时统计日志中的 ERROR 数量。

用法:
    python solution.py app.log -o error_per_hour.csv --top 5
"""

import argparse
import csv
import re
from collections import Counter
from datetime import datetime

# 精确锚定：开头是时间，紧接着是 [ERROR]，正文不参与判断
LINE_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+\[(?P<level>[A-Z]+)\]"
)
TS_FMT = "%Y-%m-%d %H:%M:%S"


def main() -> None:
    ap = argparse.ArgumentParser(description="按小时统计 ERROR 数量")
    ap.add_argument("log", help="日志文件")
    ap.add_argument("-o", "--out", default="error_per_hour.csv")
    ap.add_argument("--top", type=int, default=0, help="终端只打印前 N 行")
    args = ap.parse_args()

    counter: Counter = Counter()
    skipped = 0

    with open(args.log, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            m = LINE_RE.match(line)
            if not m:
                skipped += 1
                continue
            if m.group("level") != "ERROR":
                continue
            try:
                dt = datetime.strptime(m.group("ts"), TS_FMT)
            except ValueError:
                skipped += 1
                continue
            counter[dt.strftime("%Y-%m-%d %H:00")] += 1

    rows = sorted(counter.items())

    with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["hour", "count"])
        writer.writerows(rows)

    shown = rows[: args.top] if args.top > 0 else rows
    for hour, count in shown:
        print(f"{hour}\t{count}")

    print(f"\n统计：写入 {len(rows)} 个小时的数据，跳过 {skipped} 行 -> {args.out}")


if __name__ == "__main__":
    main()
