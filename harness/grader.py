"""任务自动评分器（harness）。

用途
----
拿一份「候选实现」，跑对应的验收测试，输出逐条判定结果。

    # 评某一个任务
    python -m harness.grader --task 03 --solution /path/to/candidate.py

    # 自检：把所有参考实现跑一遍
    python -m harness.grader --all

设计说明
--------
* 评分器**不 import 候选代码**，只通过子进程调用它的命令行接口。
  这样候选代码即使有语法错误、死循环、`sys.exit()`，也不会污染评分进程。
* 验收标准就是 `tests/test_task_XX.py` 里的测试函数 —— 
  **测试即标准**，不维护两套规则，避免文档与实现漂移。
* 每个测试函数名即一条验收项；通过率就是得分。
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"

# 任务号 -> (目录名, 测试文件)
TASKS = {
    "01": ("task-01-batch-rename-images", "test_task_01.py"),
    "02": ("task-02-split-name-column", "test_task_02.py"),
    "03": ("task-03-log-hour-errors", "test_task_03.py"),
    "04": ("task-04-check-markdown-links", "test_task_04.py"),
    "05": ("task-05-compress-images", "test_task_05.py"),
}

RESULT_RE = re.compile(r"::(?P<name>[\w\[\]\-\.]+)\s+(?P<outcome>PASSED|FAILED|ERROR|SKIPPED)")
SUMMARY_RE = re.compile(r"(?P<count>\d+) (?P<kind>passed|failed|error|errors|skipped)")


def reference_solution(task_id: str) -> Path:
    return ROOT / TASKS[task_id][0] / "solution.py"


def _parse_junit(xml_path: Path) -> list:
    """从 pytest 的 JUnit XML 中提取每个用例的结果。

    不解析终端输出，因为 -q/-v 的优先级会被 pyproject 的 addopts 与
    父进程环境影响；XML 是稳定的。
    """
    import xml.etree.ElementTree as ET

    cases = []
    tree = ET.parse(xml_path)
    for tc in tree.iter("testcase"):
        if tc.find("failure") is not None:
            outcome = "FAILED"
        elif tc.find("error") is not None:
            outcome = "ERROR"
        elif tc.find("skipped") is not None:
            outcome = "SKIPPED"
        else:
            outcome = "PASSED"
        cases.append({"name": tc.get("name", "?"), "outcome": outcome})
    return cases


def run_one(task_id: str, solution: Path) -> dict:
    """在隔离环境中运行单个任务的验收测试，返回结构化结果。"""
    if task_id not in TASKS:
        raise SystemExit(f"未知任务号: {task_id}（可选 {', '.join(TASKS)}）")

    if not solution.exists():
        raise SystemExit(f"候选实现不存在: {solution}")

    test_file = TESTS / TASKS[task_id][1]
    cases = []

    with tempfile.TemporaryDirectory(prefix="grade_") as tmp:
        # 复制一份，避免候选代码在原位置被测试污染，也避免路径含中文
        staged = Path(tmp) / "solution.py"
        shutil.copy2(solution, staged)
        xml_path = Path(tmp) / "report.xml"

        env = dict(os.environ)
        env["CANDIDATE_SOLUTION"] = str(staged)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        # 避免嵌套 pytest 时被父进程状态干扰
        env.pop("PYTEST_CURRENT_TEST", None)

        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(test_file),
                "-v",
                "--tb=no",
                "-p",
                "no:cacheprovider",
                "-o",
                "addopts=",  # 屏蔽 pyproject 里的 addopts，保证 -v 生效
                f"--junit-xml={xml_path}",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=900,
        )

        if xml_path.exists():
            try:
                cases = _parse_junit(xml_path)
            except Exception:
                cases = []

    output = proc.stdout + proc.stderr
    if not cases:  # 兼容：XML 缺失时回退到终端输出解析
        cases = [
            {"name": m.group("name"), "outcome": m.group("outcome")}
            for m in RESULT_RE.finditer(output)
        ]


    counts = {"passed": 0, "failed": 0, "error": 0, "skipped": 0}
    for c in cases:
        key = c["outcome"].lower()
        counts[key] = counts.get(key, 0) + 1

    total = len(cases)
    return {
        "task": task_id,
        "solution": str(solution),
        "cases": cases,
        "counts": counts,
        "total": total,
        "passed": counts["passed"],
        "score": (counts["passed"] / total) if total else 0.0,
        "exit": proc.returncode,
        "log": output,
    }


def print_report(result: dict) -> None:
    task_id = result["task"]
    name = TASKS[task_id][0]
    print()
    print("=" * 72)
    print(f"任务 {task_id} · {name}")
    print(f"被测实现: {result['solution']}")
    print("=" * 72)

    if not result["cases"]:
        print("未能收集到任何测试用例（可能候选代码导入即崩溃，或 pytest 缺少依赖）")
        print(result["log"][-1500:])
        return

    width = max(len(c["name"]) for c in result["cases"])
    for c in result["cases"]:
        mark = {"PASSED": "PASS", "FAILED": "FAIL", "ERROR": "ERR ", "SKIPPED": "SKIP"}[
            c["outcome"]
        ]
        print(f"  [{mark}] {c['name'].ljust(width)}")

    c = result["counts"]
    print("-" * 72)
    print(
        f"  通过 {result['passed']}/{result['total']}"
        f"   失败 {c['failed']}   错误 {c['error']}   跳过 {c['skipped']}"
        f"   得分 {result['score'] * 100:.0f}"
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="AI Coding 任务验收评分器")
    ap.add_argument("--task", help="任务号，如 01 / 02 ... 05")
    ap.add_argument("--solution", help="候选实现路径（默认使用参考实现）")
    ap.add_argument("--all", action="store_true", help="对所有参考实现跑一遍自检")
    ap.add_argument("--quiet", action="store_true", help="只输出汇总")
    args = ap.parse_args(argv)

    if not args.all and not args.task:
        ap.print_help()
        return 2

    targets = []
    if args.all:
        targets = [(tid, reference_solution(tid)) for tid in sorted(TASKS)]
    else:
        sol = Path(args.solution) if args.solution else reference_solution(args.task)
        targets = [(args.task, sol)]

    results = []
    for task_id, sol in targets:
        res = run_one(task_id, sol)
        results.append(res)
        if not args.quiet:
            print_report(res)

    total = sum(r["total"] for r in results)
    passed = sum(r["passed"] for r in results)
    print()
    print("=" * 72)
    print(f"合计：{passed}/{total} 项验收通过", end="")
    if total:
        print(f"（总体得分 {passed / total * 100:.0f}）")
    else:
        print()

    ok = all(r["cases"] and r["counts"]["failed"] == 0 and r["counts"]["error"] == 0 for r in results)
    print("结论：全部通过" if ok else "结论：存在未通过项")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
