"""Task 02 验收测试：CSV「姓名」列拆分。

每条测试对应 task.md 里的一条验收标准。
"""

from helpers import ensure_out, read_csv_rows, run_task


def _write(path, text, encoding="utf-8"):
    path.write_text(text, encoding=encoding)
    return path


SAMPLE = """编号,姓名,部门
1,张三,技术
2,欧阳锋,技术
3,司马相如,市场
4,王五,市场
5,李,行政
6,John Smith,海外
"""


def test_basic_two_char_name(tmp_path):
    """标准两字姓名：姓取 1 字，名取 1 字。"""
    src = _write(tmp_path / "d.csv", SAMPLE)
    out = tmp_path / "o.csv"
    ensure_out(run_task("02", src, "-o", out), "task02")

    rows = read_csv_rows(out)
    assert rows[0]["姓"] == "张"
    assert rows[0]["名"] == "三"


def test_compound_surname_not_split(tmp_path):
    """复姓必须整体作为姓：欧阳锋 -> 欧阳 / 锋（不能是 欧 / 阳锋）。"""
    src = _write(tmp_path / "d.csv", SAMPLE)
    out = tmp_path / "o.csv"
    ensure_out(run_task("02", src, "-o", out))

    rows = {r["编号"]: r for r in read_csv_rows(out)}
    assert rows["2"]["姓"] == "欧阳" and rows["2"]["名"] == "锋"
    assert rows["3"]["姓"] == "司马" and rows["3"]["名"] == "相如"


def test_single_char_and_empty(tmp_path):
    """单字姓名：姓=原值，名=空；不得报错。"""
    src = _write(tmp_path / "d.csv", SAMPLE)
    out = tmp_path / "o.csv"
    ensure_out(run_task("02", src, "-o", out))

    rows = {r["编号"]: r for r in read_csv_rows(out)}
    assert rows["5"]["姓"] == "李"
    assert rows["5"]["名"] == ""


def test_english_name_split_by_space(tmp_path):
    """含空格的英文名按第一个空格拆，不得按字符拆。"""
    src = _write(tmp_path / "d.csv", SAMPLE)
    out = tmp_path / "o.csv"
    ensure_out(run_task("02", src, "-o", out))

    rows = {r["编号"]: r for r in read_csv_rows(out)}
    assert rows["6"]["姓"] == "John"
    assert rows["6"]["名"] == "Smith"


def test_column_order_preserved(tmp_path):
    """列顺序：『姓名』原位被『姓』『名』替换，其余列位置不变。"""
    src = _write(tmp_path / "d.csv", SAMPLE)
    out = tmp_path / "o.csv"
    ensure_out(run_task("02", src, "-o", out))

    with open(out, "r", encoding="utf-8-sig") as f:
        header = f.readline().strip().split(",")
    assert header == ["编号", "姓", "名", "部门"]


def test_output_has_bom_for_excel(tmp_path):
    """输出必须带 UTF-8 BOM，否则 Excel 打开中文乱码。"""
    src = _write(tmp_path / "d.csv", SAMPLE)
    out = tmp_path / "o.csv"
    ensure_out(run_task("02", src, "-o", out))

    raw = out.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf"), "输出缺少 UTF-8 BOM"


def test_gbk_input_supported(tmp_path):
    """GBK 编码的输入文件也必须能读（老版 Excel 导出的 CSV 常见）。"""
    src = _write(tmp_path / "gbk.csv", SAMPLE, encoding="gbk")
    out = tmp_path / "o.csv"
    res = run_task("02", src, "-o", out)
    ensure_out(res, "gbk")

    rows = {r["编号"]: r for r in read_csv_rows(out)}
    assert rows["2"]["姓"] == "欧阳"


def test_reports_manual_review_count(tmp_path):
    """空值/单字姓名应计入『需人工确认』并在输出中报告。"""
    src = _write(tmp_path / "d.csv", SAMPLE)
    out = tmp_path / "o.csv"
    res = ensure_out(run_task("02", src, "-o", out))
    assert "人工确认" in res.stdout
    # 样例里只有『李』一条需要人工确认
    assert "1" in res.stdout
