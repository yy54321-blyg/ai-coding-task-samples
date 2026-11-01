"""反面教材 1：模拟「看起来能用」的错误实现（task-03）。

典型错误：
1. 用 `"ERROR" in line` 判断级别 —— 把消息正文里的 ERROR 也统计进去
2. 不解析时间格式，直接截字符串
3. 直接遍历 dict 输出 —— 顺序随机
4. 不统计 skipped，脏数据静默丢失

期望结果：harness 打分 < 100，且能明确指出失败的具体验收项。
"""

import argparse
import csv
from collections import Counter

ap = argparse.ArgumentParser()
ap.add_argument("log")
ap.add_argument("-o", "--out", default="out.csv")
ap.add_argument("--top", type=int, default=0)
args = ap.parse_args()

counter = Counter()
with open(args.log, encoding="utf-8", errors="replace") as f:
    for line in f:
        if "ERROR" in line:                     # ← 错误 1
            counter[line[:13] + ":00"] += 1     # ← 错误 2

with open(args.out, "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["hour", "count"])
    for key, value in counter.items():          # ← 错误 3
        writer.writerow([key, value])
