"""Task 02 参考解法：CSV「姓名」列拆分为「姓」「名」。

用法:
    python solution.py data.csv -o out.csv
"""

import argparse
import csv

COMPOUND_SURNAMES = {
    "欧阳", "司马", "上官", "诸葛", "东方", "皇甫", "尉迟", "公孙", "慕容",
    "长孙", "宇文", "司徒", "令狐", "夏侯", "端木", "南宫", "独孤", "轩辕", "百里",
}

ENCODINGS = ("utf-8-sig", "utf-8", "gbk")


def read_rows(path: str):
    """依次尝试常见编码，返回 (行列表, 使用的编码)。"""
    last_err = None
    for enc in ENCODINGS:
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                return list(csv.DictReader(f)), enc
        except UnicodeDecodeError as exc:
            last_err = exc
            continue
    raise SystemExit(f"无法识别文件编码: {path} ({last_err})")


def split_name(full: str):
    """返回 (姓, 名, 是否需要人工确认)。"""
    name = (full or "").strip()

    if not name:
        return "", "", True

    # 含空格 / 点号：按第一个空格拆（英文名、西式姓名）
    for sep in (" ", "　"):
        if sep in name:
            a, b = name.split(sep, 1)
            return a, b.strip(), False

    if len(name) == 1:
        return name, "", True

    if len(name) >= 3 and name[:2] in COMPOUND_SURNAMES:
        return name[:2], name[2:], False

    return name[0], name[1:], False


def main() -> None:
    ap = argparse.ArgumentParser(description="拆分钟文姓名列")
    ap.add_argument("src", help="输入 CSV")
    ap.add_argument("-o", "--out", default="out.csv", help="输出 CSV")
    args = ap.parse_args()

    rows, enc = read_rows(args.src)
    if not rows:
        raise SystemExit("输入文件为空")

    src_fields = list(rows[0].keys())
    if "姓名" not in src_fields:
        raise SystemExit("输入文件必须包含『姓名』列")

    # 保持原列顺序，把「姓名」替换成「姓」「名」
    out_fields = []
    for field in src_fields:
        if field == "姓名":
            out_fields.extend(["姓", "名"])
        else:
            out_fields.append(field)

    warned = 0
    out_rows = []
    for row in rows:
        xing, ming, need_review = split_name(row.get("姓名", ""))
        if need_review:
            warned += 1
        new_row = {}
        for field in src_fields:
            if field == "姓名":
                new_row["姓"] = xing
                new_row["名"] = ming
            else:
                new_row[field] = row.get(field, "")
        out_rows.append(new_row)

    with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"读取编码: {enc}")
    print(f"完成 {len(out_rows)} 行，其中需人工确认 {warned} 行 -> {args.out}")


if __name__ == "__main__":
    main()
