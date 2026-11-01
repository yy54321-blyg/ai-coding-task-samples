# AI Coding 任务设计样例集

> 一个「AI Coding 任务」应该由三部分组成：**规格**、**实现**、**可执行的验收标准**。
> 只有前两样，评审者无法判断质量；加上第三样，质量才变成可测的。

本仓库演示这三层，并附带一个**自动评分器**，用于拿任意候选实现跑同一套验收标准。

---

## 一、这个仓库解决什么问题

AI 编程任务的数据质量，取决于**验收标准有多严格**。

- 标准太松 → 错误实现也能通过，数据被污染
- 标准只在文档里 → 无法自动判定，只能靠人肉看
- 标准写不出测试 → 说明它本身还不够具体

所以这里每个任务都配了**能跑的测试**，并且额外提供了**反面教材**，
用来证明这套标准确实能抓住错误实现。

---

## 二、仓库结构

```
.
├── task-01-batch-rename-images/     # 任务 1：按 EXIF 拍摄时间批量重命名
│   ├── task.md                      #   规格：需求 / 示例 / 验收标准 / 常见错误
│   └── solution.py                  #   参考实现
├── task-02-split-name-column/       # 任务 2：CSV 姓名列拆分（含复姓与编码探测）
├── task-03-log-hour-errors/         # 任务 3：日志按小时统计 ERROR
├── task-04-check-markdown-links/    # 任务 4：Markdown 死链检查（并发）
├── task-05-compress-images/         # 任务 5：批量压缩图片到 200KB
│
├── tests/                           # 验收标准（测试即标准）
│   ├── helpers.py                   #   子进程调用、CSV 读取等公共工具
│   ├── test_task_01.py              #   8 条验收项
│   ├── test_task_02.py              #   8 条
│   ├── test_task_03.py              #   8 条
│   ├── test_task_04.py              #   9 条（用本地 HTTP 服务器，结果确定）
│   ├── test_task_05.py              #   8 条
│   └── test_meta_discrimination.py  #   4 条元测试：验收标准必须有区分度
│
├── harness/
│   └── grader.py                    # 自动评分器：给任意候选实现打分
│
├── examples/pitfalls/               # 反面教材：故意写错的实现
└── ci/acceptance.yml               # CI 配置（复制到 .github/workflows/ 即启用）
```

---

## 三、三层是怎么配合的

### 第 1 层：规格（`task.md`）

写清楚需求、输入输出示例、**可测的验收标准**、难度定位，以及**常见错误预判**。

验收标准要求写成可测的形式：

| 反例（不可测） | 正例（可测） |
|---|---|
| 「代码要健壮」 | 「`--dry-run` 下目录内文件名与 mtime 均不变」 |
| 「处理好异常」 | 「无法解析的行计入 failed，且不中断后续处理」 |

### 第 2 层：实现（`solution.py`）

已验证可运行的参考实现。

### 第 3 层：验收（`tests/`）

**测试就是验收标准本身**，不维护第二套规则，避免文档与实现漂移。

示例（task-03 的核心考点）：

```python
def test_error_in_message_body_not_counted(tmp_path):
    """[INFO] retry ERROR handler —— 正文里的 ERROR 不算。"""
    _, rows = _run(tmp_path, SAMPLE)
    got = {r["hour"]: int(r["count"]) for r in rows}
    assert got["2025-03-01 12:00"] == 2, "把正文里的 ERROR 也算进去了"
```

---

## 四、自动评分器

拿任意一份实现，跑对应任务的验收标准，输出逐条判定：

```bash
# 评单个任务（不指定 --solution 则评参考实现）
python -m harness.grader --task 03
python -m harness.grader --task 03 --solution ./my_attempt.py

# 全量自检
python -m harness.grader --all
```

输出示例（用反面教材演示）：

```
$ python -m harness.grader --task 03 --solution examples/pitfalls/bad_task03_loose_regex.py

========================================================================
任务 03 · task-03-log-hour-errors
========================================================================
  [FAIL] test_counts_match_expected
  [FAIL] test_error_in_message_body_not_counted
  [FAIL] test_garbage_line_skipped_without_crash
  [FAIL] test_output_sorted_ascending
  [PASS] test_hour_is_zero_padded
  [PASS] test_cross_day_split_into_two_hours
  [PASS] test_empty_file_outputs_header_only
  [PASS] test_all_levels_other_than_error_ignored
------------------------------------------------------------------------
  通过 4/8   失败 4   错误 0   跳过 0   得分 50
```

**关键点：它不只说"不合格"，它指出错在哪一条。** 这正是任务设计要提供的东西。

评分器不导入候选代码，只用子进程调用其命令行接口——
候选代码即使死循环或有语法错误，也不会污染评分进程。

---

## 五、验收标准必须有区分度

`tests/test_meta_discrimination.py` 在测的不是业务逻辑，而是**验收标准的质量**：

- 正确实现 → 必须 100% 通过
- 错误实现 → 必须被打下来，且指出正确的失败项

如果哪天有人把标准改松了（例如删掉「不许覆盖同名文件」这条），CI 会变红。

反面教材见 [`examples/pitfalls/`](./examples/pitfalls/README.md)。

---

## 六、运行

```bash
pip install -r requirements.txt -r requirements-dev.txt

# 全部验收
python -m pytest tests -q

# 评分器自检
python -m harness.grader --all
```

单独跑某个任务：

```bash
python task-03-log-hour-errors/solution.py app.log -o out.csv
python task-02-split-name-column/solution.py data.csv -o out.csv
python task-01-batch-rename-images/solution.py ./in --dry-run
python task-04-check-markdown-links/solution.py ./docs -o dead.csv
python task-05-compress-images/solution.py ./in -o ./out
```

---

## 七、评测结果一览

| 任务 | 验收项 | 参考实现 | 反面教材得分 |
|---|---:|---|---|
| task-01 图片重命名 | 8 | 8/8 | 2/8 |
| task-02 姓名拆分 | 8 | 8/8 | — |
| task-03 日志统计 | 8 | 8/8 | 4/8 |
| task-04 死链检查 | 9 | 9/9 | — |
| task-05 图片压缩 | 8 | 8/8 | — |
| 元测试（区分度） | 4 | 4/4 | — |
| **合计** | **45** | **45/45** | — |

---

## 八、我如何判断一个任务的好坏

1. **有唯一正确答案** —— 换个人执行，结果应当一致
2. **有明确的失败方式** —— 做错时能被发现，且能定位到哪一条
3. **需要判断，不只是执行** —— 存在需要人为决策的边界（复姓怎么拆、同秒冲突怎么编号）
4. **难度可控** —— 能按难度分层，构造简单 / 中等 / 困难样本
5. **能写成测试** —— 写不成测试，说明验收标准还不够具体

---

## 九、说明

本仓库所有任务、验收标准与代码，均为本人在学习过程中自行设计，用于任务设计与评测练习。
