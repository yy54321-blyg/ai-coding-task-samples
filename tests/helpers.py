"""测试公共工具。

设计要点：
1. 一律**通过子进程调用脚本**测试 CLI 契约，而不是 import 内部函数
   —— 因为交付物是「命令行工具」，不是「库」。
2. 支持 `CANDIDATE_SOLUTION` 环境变量替换被测实现，
   这样 harness/grader.py 可以拿任意一份候选代码来跑同一套验收标准。
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TASKS = {
    "01": "task-01-batch-rename-images",
    "02": "task-02-split-name-column",
    "03": "task-03-log-hour-errors",
    "04": "task-04-check-markdown-links",
    "05": "task-05-compress-images",
}


def solution_script(task_id: str) -> Path:
    """返回被测脚本路径。CANDIDATE_SOLUTION 优先（供 grader 使用）。"""
    candidate = os.environ.get("CANDIDATE_SOLUTION")
    if candidate:
        return Path(candidate).resolve()
    return ROOT / TASKS[task_id] / "solution.py"


def run_task(task_id: str, *args, cwd=None, timeout=180):
    """以子进程方式调用脚本，返回 CompletedProcess。

    强制子进程 stdout/stderr 使用 UTF-8，否则 Windows 下默认 GBK
    会把中文输出写得乱码，导致基于输出的断言无法判断。
    被测试脚本本身不应依赖 locale，这也是对命令行工具的合理要求。
    """
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    cmd = [sys.executable, str(solution_script(task_id))] + [str(a) for a in args]
    return subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=env,
    )


def read_csv_rows(path: Path):
    """读取 CSV 为 list[dict]，兼容 utf-8-sig。"""
    import csv

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def ensure_out(res, label=""):
    """断言子进程成功退出，失败时带上 stderr 方便定位。"""
    assert res.returncode == 0, (
        f"{label} 退出码 {res.returncode}\n"
        f"--- stdout ---\n{res.stdout}\n--- stderr ---\n{res.stderr}"
    )
    return res
