# 反面教材（负样本）

这里的文件是**故意写错的实现**，用途只有一个：

> **证明验收标准真的有区分度——不会「随便交个东西都算过」。**

一个好的任务设计，不仅要能**判定正确的实现通过**，还必须能**判定错误的实现不通过**，
并且能指出它错在哪一条。

## 当前负样本

| 文件 | 对应任务 | 故意犯的错 | harness 预期结果 |
|---|---|---|---|
| `bad_task03_loose_regex.py` | task-03 | 用 `"ERROR" in line` 代替检查级别字段 | 8 项中失败 4 项，得分 50 |
| `bad_task01_overwrite.py` | task-01 | `os.rename` 直接覆盖、`--dry-run` 失效、损坏文件被改名 | 8 项中至少失败 3 项 |

## 怎么验证

```bash
python -m harness.grader --task 03 --solution examples/pitfalls/bad_task03_loose_regex.py
python -m harness.grader --task 01 --solution examples/pitfalls/bad_task01_overwrite.py
```

会输出逐条 PASS / FAIL，并在结尾给出得分。

## 为什么这一步重要

如果一组验收标准对错误实现也全部通过，那它对数据质量没有任何贡献——
它只会让评审者误以为"这题做对了"。

`tests/test_meta_discrimination.py` 把这件事写成了自动化测试：
**只要哪天验收标准弱化到抓不住这些错误，CI 就会变红。**
