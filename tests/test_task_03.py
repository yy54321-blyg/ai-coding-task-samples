"""Task 03 验收测试：日志按小时统计 ERROR 数量。

核心考点：统计的是「级别字段」，不是字符串出现。
"""

from helpers import ensure_out, read_csv_rows, run_task

SAMPLE = """2025-03-01 12:34:56 [ERROR] db timeout
2025-03-01 12:59:01 [INFO] retry ERROR handler
2025-03-01 12:05:00 [ERROR] disk full
2025-03-01 13:00:01 [ERROR] db timeout
2025-03-02 00:10:00 [ERROR] rollover
this line is garbage
2025-03-01 23:59:59 [ERROR] final
"""


def _run(tmp_path, text):
    log = tmp_path / "app.log"
    log.write_text(text, encoding="utf-8")
    out = tmp_path / "res.csv"
    res = run_task("03", log, "-o", out)
    ensure_out(res, "task03")
    return res, read_csv_rows(out)


def test_counts_match_expected(tmp_path):
    """给定样例应得到 4 个小时的数据，且数值正确。"""
    _, rows = _run(tmp_path, SAMPLE)
    got = {r["hour"]: int(r["count"]) for r in rows}
    assert got == {
        "2025-03-01 12:00": 2,
        "2025-03-01 13:00": 1,
        "2025-03-01 23:00": 1,
        "2025-03-02 00:00": 1,
    }, got


def test_error_in_message_body_not_counted(tmp_path):
    """[INFO] retry ERROR handler —— 正文里的 ERROR 不算，12:00 只能是 2 条。"""
    _, rows = _run(tmp_path, SAMPLE)
    got = {r["hour"]: int(r["count"]) for r in rows}
    assert got["2025-03-01 12:00"] == 2, "把正文里的 ERROR 也算进去了"


def test_garbage_line_skipped_without_crash(tmp_path):
    """无法解析的行应跳过并计入 skipped，进程退出码必须为 0。"""
    res, _ = _run(tmp_path, SAMPLE)
    assert res.returncode == 0
    assert "跳过" in res.stdout


def test_output_sorted_ascending(tmp_path):
    """输出必须按时间升序。"""
    _, rows = _run(tmp_path, SAMPLE)
    hours = [r["hour"] for r in rows]
    assert hours == sorted(hours), hours


def test_hour_is_zero_padded(tmp_path):
    """小时必须补零为 HH:00，否则字符串排序会错。"""
    _, rows = _run(tmp_path, SAMPLE)
    for r in rows:
        assert len(r["hour"]) == 16, r["hour"]
        assert r["hour"][13:] == ":00", r["hour"]


def test_cross_day_split_into_two_hours(tmp_path):
    """23:59:59 与次日 00:10:00 必须分到两个不同的整点。"""
    _, rows = _run(tmp_path, SAMPLE)
    hours = {r["hour"] for r in rows}
    assert "2025-03-01 23:00" in hours
    assert "2025-03-02 00:00" in hours


def test_empty_file_outputs_header_only(tmp_path):
    """空日志：输出只有表头，退出码 0，不得抛异常。"""
    res, rows = _run(tmp_path, "")
    assert res.returncode == 0
    assert rows == []

    out = tmp_path / "res.csv"
    assert out.read_text(encoding="utf-8-sig").strip() == "hour,count"


def test_all_levels_other_than_error_ignored(tmp_path):
    """WARN / INFO / DEBUG 一律不计入。"""
    text = (
        "2025-04-01 09:00:00 [WARN] disk 80%\n"
        "2025-04-01 09:00:01 [INFO] ok\n"
        "2025-04-01 09:00:02 [DEBUG] trace\n"
        "2025-04-01 09:00:03 [ERROR] real one\n"
    )
    _, rows = _run(tmp_path, text)
    assert len(rows) == 1
    assert int(rows[0]["count"]) == 1
