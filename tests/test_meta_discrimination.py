"""元测试：验收标准必须具备「区分度」。

这一组测试不是在测业务逻辑，而是在测**验收标准本身的质量**。

要求：
- 正确实现 -> 100% 通过（见其余 test_task_*.py）
- 错误实现 -> 必须被打下来，且能指出错在哪一条

如果哪天有人把验收标准改松了（例如删掉「不许覆盖同名文件」这条），
这里的断言就会失败，CI 变红。

> 一个对错误实现也全部放行的验收标准，对数据质量没有贡献。
"""

from pathlib import Path

import pytest

pytest.importorskip("PIL", reason="task-01 负样本需要 Pillow")

from harness import grader  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PITFALLS = ROOT / "examples" / "pitfalls"


def test_bad_task03_is_rejected():
    """用 `"ERROR" in line` 的松散实现必须被判为不合格。"""
    res = grader.run_one("03", PITFALLS / "bad_task03_loose_regex.py")

    assert res["total"] > 0, "没有收集到验收项"
    assert res["score"] < 1.0, "错误实现竟通过了全部验收，说明验收标准失效"
    assert res["counts"]["failed"] >= 2, "至少要抓出 2 条错误"


def test_bad_task03_fails_the_right_criteria():
    """不仅要判错，还要判对是哪几条 —— 定位能力同样重要。"""
    res = grader.run_one("03", PITFALLS / "bad_task03_loose_regex.py")
    failed = {c["name"] for c in res["cases"] if c["outcome"] != "PASSED"}

    assert "test_error_in_message_body_not_counted" in failed, (
        "没有抓到『把正文里的 ERROR 也统计』这个核心错误"
    )
    assert "test_output_sorted_ascending" in failed, "没有抓到『输出无序』"


def test_bad_task01_is_rejected():
    """直接 os.rename 覆盖 + dry-run 失效 + 损坏文件被改名，必须被判为不合格。"""
    res = grader.run_one("01", PITFALLS / "bad_task01_overwrite.py")

    assert res["total"] > 0
    assert res["score"] < 1.0, "错误实现竟通过了全部验收"
    assert res["counts"]["failed"] >= 3, "至少要抓出 3 条错误"


def test_reference_implementations_are_clean():
    """对照：参考实现必须全部通过，否则说明验收标准本身写错了。"""
    for task_id in ("01", "02", "03", "04", "05"):
        res = grader.run_one(task_id, grader.reference_solution(task_id))
        assert res["total"] > 0, f"task {task_id} 没有验收项"
        assert res["counts"]["failed"] == 0, f"task {task_id} 参考实现未通过验收"
        assert res["counts"]["error"] == 0, f"task {task_id} 出现错误"
