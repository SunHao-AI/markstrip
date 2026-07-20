# 修正 @internal 块文档 + 废弃 full-start/full-end 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修正 README 中 `@internal-start`/`@internal-end` 的错误描述，并废弃 `# markstrip: full-start`/`full-end` 区间 pragma 指令。

**Architecture:** 纯删除 + 文档修正。从 `pragma_scanner.py` 移除 `scan_full_ranges()` 函数，从 `python_plugin.py` 和 `markdown_plugin.py` 移除其调用点，清理相关测试，修正 README 和 design.md 文档。

**Tech Stack:** Python 3.12+，pytest

**Spec:** `docs/superpowers/specs/2026-07-19-fix-block-docs-and-remove-full-range.md`

## Global Constraints

- 保留 `# markstrip: full`（文件级 pragma）完全不变
- 保留 `scan_file_pragma()` 函数
- `@internal-start`/`@internal-end` 代码行为不变（仅文档修正）
- 分支命名：`fix/remove-full-range-pragma`
- 提交信息用中文，单行，避免 PowerShell here-string

---

## 文件结构

| 文件 | 职责 | 本计划变更 |
|------|------|-----------|
| `markstrip/core/pragma_scanner.py` | pragma 指令扫描（`scan_file_pragma` + `scan_full_ranges`） | 移除 `scan_full_ranges` 及 BlockRange/BlockScanResult 导入 |
| `markstrip/languages/python_plugin.py` | Python 插件（strip_selective + strip_full + fallback） | 移除 `scan_full_ranges` 导入及 pragma 区间逻辑 |
| `markstrip/languages/markdown_plugin.py` | Markdown 插件（代码块 + HTML 注释 + fallback） | 移除 `scan_full_ranges` 导入及 pragma 区间逻辑 |
| `tests/unit/test_pragma_scanner.py` | pragma 扫描器单元测试 | 移除 `TestScanFullRanges` 类及导入 |
| `tests/unit/test_python_plugin.py` | Python 插件单元测试 | 移除 3 个 pragma 区间相关测试 |
| `tests/integration/test_cli.py` | CLI 集成测试 | 移除 1 个 pragma 错配警告测试 |
| `tests/golden/python/pragma_range*` | golden 测试 | 删除 6 个文件 |
| `tests/golden/python/pragma_with_selective*` | golden 测试 | 删除 2 个文件 |
| `tests/golden/python/pragma_nested*` | golden 测试 | 删除 2 个文件 |
| `tests/golden/python/pragma_mismatched_end*` | golden 测试 | 删除 2 个文件 |
| `tests/golden/markdown/pragma_in_yaml*` | golden 测试 | 删除 2 个文件 |
| `README.md` | 用户文档 | 修正块描述 + 移除 full-start/full-end 内容 |
| `docs/markstrip-design.md` | 设计文档 | 移除 full-start/full-end 章节 + 修正块描述 |

---

## Task 1: 源代码变更 — 移除 `scan_full_ranges` 与调用点

**Files:**
- Modify: `markstrip/core/pragma_scanner.py`
- Modify: `markstrip/languages/python_plugin.py`
- Modify: `markstrip/languages/markdown_plugin.py`

**Interfaces:**
- Consumes: 无（依赖现有代码）
- Produces: `pragma_scanner` 模块仅暴露 `scan_file_pragma`；`python_plugin.py` 和 `markdown_plugin.py` 不再导入 `scan_full_ranges`

- [ ] **Step 1: 从 `pragma_scanner.py` 移除 `scan_full_ranges` 函数和导入**

打开 `markstrip/core/pragma_scanner.py`，执行两处编辑：

1. 移除第 8 行的 `BlockRange`/`BlockScanResult` 导入：

```python
# 删除此行
from markstrip.core.block_scanner import BlockRange, BlockScanResult
```

2. 移除第 38-84 行的 `scan_full_ranges` 函数（整个函数定义）：

```python
# 删除第 38-84 行的整个函数
def scan_full_ranges(
    lines: list[str], comment_prefix: str
) -> BlockScanResult:
    ...
```

编辑后文件应仅保留：
- `import re`
- `_build_pragma_regex()` 函数
- `scan_file_pragma()` 函数

- [ ] **Step 2: 从 `python_plugin.py` 移除 `scan_full_ranges` 导入和调用**

打开 `markstrip/languages/python_plugin.py`，执行以下编辑：

1. 第 8 行：移除 `scan_full_ranges` 导入：

```python
# 修改前
from markstrip.core.pragma_scanner import scan_file_pragma, scan_full_ranges
# 修改后
from markstrip.core.pragma_scanner import scan_file_pragma
```

2. 第 82-84 行（`strip_selective` 中文件级 pragma 检查后的区间扫描）：移除这 3 行：

```python
# 删除以下 3 行
            pragma_scan = scan_full_ranges(lines, "#")
            config.warnings.extend(pragma_scan.warnings)
            if pragma_scan.ranges:
```

3. 第 85-88 行：文件级 pragma 委托逻辑中，移除区间 pragma 相关判断。原代码为：

```python
            if pragma_scan.ranges:
                config.warnings.append(
                    "文件级 markstrip: full 已生效, 区间标记冗余"
                )
            return self.strip_full(content, config)
```

需改为直接委托：

```python
            return self.strip_full(content, config)
```

4. 第 138-145 行（`strip_selective` 中 pragma 区间扫描 + `_in_pragma_range` 定义）：移除这 8 行：

```python
# 删除以下 8 行
        pragma_scan = scan_full_ranges(lines, "#")
        config.warnings.extend(pragma_scan.warnings)
        pragma_ranges = pragma_scan.ranges

        def _in_pragma_range(line_num: int) -> bool:
            return any(
                r.start_line <= line_num <= r.end_line for r in pragma_ranges
            )
```

5. 第 150 行：移除 `in_pragma = _in_pragma_range(tok.start[0])` 这行：

```python
# 删除此行
                in_pragma = _in_pragma_range(tok.start[0])
```

6. 第 151 行：将 `if in_block:` 改为 `if in_block:`（不变），但第 159 行的 `elif in_pragma and not check_mode:` 块需移除，即第 159-168 行：

```python
# 删除第 159-168 行
                elif in_pragma and not check_mode:
                    # pragma 区间(check_mode=False):full 逻辑,删注释保留代码
                    if self._is_preserved_comment(tok, config):
                        continue
                    if self._is_whole_line_comment(tok, lines):
                        comment_removals.append((tok.start[0], 0, -1))
                    else:
                        comment_removals.append(
                            (tok.start[0], tok.start[1], tok.end[1])
                        )
```

7. 第 190-193 行：移除 `check_mode` 下的 `in_pragma` 分支：

```python
# 删除第 190-193 行
                elif in_pragma and check_mode:
                    # pragma 区间内非 @internal 注释:check_mode 不删除不报告
                    pass
```

8. 第 197-198 行：移除 STRING/docstring 处理中的 pragma 区间逻辑。原代码：

```python
                    in_pragma = _in_pragma_range(tok.start[0])
                    if in_pragma and not config.preserve_docstrings and not check_mode:
```

改为直接使用 `_process_docstring`：

```python
                    doc_removals = self._process_docstring(
                        tok, config, lines
                    )
                    comment_removals.extend(doc_removals)
```

即删除第 197-200 行，保留第 201-205 行（else 分支内容提升为主分支）。

9. 第 554-645 行区域（`_fallback_regex_selective` 方法）：同样的删除逻辑。删除 `scan_full_ranges` 调用、`pragma_ranges`、`_in_pragma_range` 定义及其使用：

```python
# 删除 pragma 区间扫描代码块（约第 602-633 行）：
        pragma_scan = scan_full_ranges(lines, "#")
        config.warnings.extend(pragma_scan.warnings)
        pragma_ranges = pragma_scan.ranges

        def _in_pragma_range(line_num: int) -> bool:
            return any(
                r.start_line <= line_num <= r.end_line for r in pragma_ranges
            )
```

以及删除循环中使用 `_in_pragma_range` 的分支（`elif _in_pragma_range(i) and not check_mode:`）。

- [ ] **Step 3: 从 `markdown_plugin.py` 移除 `scan_full_ranges` 导入和调用**

打开 `markstrip/languages/markdown_plugin.py`，执行以下编辑：

1. 第 6 行：移除 `scan_full_ranges` 导入：

```python
# 修改前
from markstrip.core.pragma_scanner import scan_file_pragma, scan_full_ranges
# 修改后
from markstrip.core.pragma_scanner import scan_file_pragma
```

2. 第 259-266 行：移除 pragma 区间扫描 + `_in_pragma_range` 定义：

```python
# 删除以下 8 行
        pragma_scan = scan_full_ranges(lines, prefix)
        config.warnings.extend(pragma_scan.warnings)
        pragma_ranges = pragma_scan.ranges

        def _in_pragma_range(line_num: int) -> bool:
            return any(
                r.start_line <= line_num <= r.end_line for r in pragma_ranges
            )
```

3. 第 312 行：移除 `elif _in_pragma_range(i):` 分支（删除该 elif 块）。

- [ ] **Step 4: 跑测试验证源代码变更**

Run: `python -m pytest tests/unit/test_pragma_scanner.py -v`
Expected: `TestScanFullRanges` 测试失败（函数已被移除），`TestScanFilePragma` 全部通过。

Run: `python -m pytest tests/unit/test_python_plugin.py tests/unit/test_markdown_plugin.py -v`
Expected: 部分 pragma 区间相关测试失败。

- [ ] **Step 5: 提交**

```bash
git add markstrip/core/pragma_scanner.py markstrip/languages/python_plugin.py markstrip/languages/markdown_plugin.py
git commit -m "refactor: 移除 scan_full_ranges 与 full-start/full-end 区间 pragma 支持"
```

---

## Task 2: 测试变更 — 移除 full-start/full-end 相关测试

**Files:**
- Modify: `tests/unit/test_pragma_scanner.py`
- Modify: `tests/unit/test_python_plugin.py`
- Modify: `tests/integration/test_cli.py`
- Delete: 14 个 golden 文件（见下方清单）

**Interfaces:**
- Consumes: Task 1 的源代码变更（`scan_full_ranges` 已移除）
- Produces: 全量测试应全部通过，无遗留 `full-start`/`full-end` 引用

### 2.1 删除 golden 文件

- [ ] **Step 1: 删除区间级 pragma golden 文件**

删除以下 14 个文件（注意保留 `pragma_full.py` 和 `pragma_full.expected.py`）：

```bash
# 区间级 pragma golden 文件（删除）
tests/golden/python/pragma_range.py
tests/golden/python/pragma_range.expected.py
tests/golden/python/pragma_range_docstring.py
tests/golden/python/pragma_range_docstring.expected.py
tests/golden/python/pragma_nested.py
tests/golden/python/pragma_nested.expected.py
tests/golden/python/pragma_mismatched_end.py
tests/golden/python/pragma_mismatched_end.expected.py
tests/golden/python/pragma_with_selective.py
tests/golden/python/pragma_with_selective.expected.py
tests/golden/markdown/pragma_in_yaml.md
tests/golden/markdown/pragma_in_yaml.expected.md
```

每个文件用 `DeleteFile` 工具删除。路径为绝对路径：
- `d:\WorkPlace\Pycharm\markstrip\tests\golden\python\pragma_range.py`
- `d:\WorkPlace\Pycharm\markstrip\tests\golden\python\pragma_range.expected.py`
- `d:\WorkPlace\Pycharm\markstrip\tests\golden\python\pragma_range_docstring.py`
- `d:\WorkPlace\Pycharm\markstrip\tests\golden\python\pragma_range_docstring.expected.py`
- `d:\WorkPlace\Pycharm\markstrip\tests\golden\python\pragma_nested.py`
- `d:\WorkPlace\Pycharm\markstrip\tests\golden\python\pragma_nested.expected.py`
- `d:\WorkPlace\Pycharm\markstrip\tests\golden\python\pragma_mismatched_end.py`
- `d:\WorkPlace\Pycharm\markstrip\tests\golden\python\pragma_mismatched_end.expected.py`
- `d:\WorkPlace\Pycharm\markstrip\tests\golden\python\pragma_with_selective.py`
- `d:\WorkPlace\Pycharm\markstrip\tests\golden\python\pragma_with_selective.expected.py`
- `d:\WorkPlace\Pycharm\markstrip\tests\golden\markdown\pragma_in_yaml.md`
- `d:\WorkPlace\Pycharm\markstrip\tests\golden\markdown\pragma_in_yaml.expected.md`

### 2.2 修改 `test_pragma_scanner.py`

- [ ] **Step 2: 移除 `TestScanFullRanges` 测试类**

打开 `tests/unit/test_pragma_scanner.py`，执行以下编辑：

1. 第 2 行：移除 `scan_full_ranges` 导入：

```python
# 修改前
from markstrip.core.pragma_scanner import scan_file_pragma, scan_full_ranges
# 修改后
from markstrip.core.pragma_scanner import scan_file_pragma
```

2. 删除第 50-124 行：整个 `TestScanFullRanges` 类及其所有测试方法（`test_single_range`、`test_multiple_ranges`、`test_orphan_end`、`test_unclosed_start`、`test_nested_start_ignored`、`test_whitespace_variations`、`test_custom_prefix`、`test_no_pragma`）。

编辑后文件应仅保留 `TestScanFilePragma` 类（第 5-48 行）。

### 2.3 修改 `test_python_plugin.py`

- [ ] **Step 3: 移除 pragma 区间相关测试**

打开 `tests/unit/test_python_plugin.py`，删除以下测试：

1. 第 166-176 行：删除 `test_redundant_range_pragma_warns` 方法（依赖 `full-start`/`full-end` 内容）：

```python
# 删除整个方法
    def test_redundant_range_pragma_warns(self, plugin, config):
        ...
```

2. 第 253-268 行：删除 `test_check_mode_skips_in_pragma_branch` 方法（依赖 `full-start`/`full-end` 内容）：

```python
# 删除整个方法
def test_check_mode_skips_in_pragma_branch(plugin):
    ...
```

**保留的 pragma 相关测试**（这些仅使用 `# markstrip: full` 文件级 pragma，**不依赖** `full-start`/`full-end`）：
- `test_delegates_and_removes_comments`（第 137 行）
- `test_check_mode_skips_file_level_pragma`（第 236 行）
- `test_check_mode_pragma_not_reported`（第 270 行）
- `test_check_mode_off_pragma_works`（第 282 行）
- `TestPragmaDelegation` 类中其他测试

### 2.4 修改 `test_cli.py`

- [ ] **Step 4: 移除 pragma 错配警告测试**

打开 `tests/integration/test_cli.py`，删除第 178-192 行的 `test_cli_verbose_pragma_warnings` 方法（依赖 `# markstrip: full-end` 孤立检测）：

```python
# 删除整个方法
    def test_cli_verbose_pragma_warnings(self, tmp_path):
        ...
```

### 2.5 验证

- [ ] **Step 5: 跑全量回归测试**

Run: `python -m pytest tests/ -v`
Expected: 全部通过（预期测试数量减少约 20 个，从 146 降到约 126）。

- [ ] **Step 6: 提交**

```bash
git add tests/
git commit -m "test: 移除 full-start/full-end 区间 pragma 相关测试与 golden 文件"
```

---

## Task 3: 文档变更 — README.md + design.md

**Files:**
- Modify: `README.md`
- Modify: `docs/markstrip-design.md`

**Interfaces:**
- Consumes: Task 1-2 的代码与测试变更
- Produces: 文档与代码行为一致，`full-start`/`full-end` 不再出现在任何文档中

### 3.1 README.md 变更

- [ ] **Step 1: 修正 `@internal-start`/`@internal-end` 描述**

打开 `README.md`，定位"标记类型详解"表（使用 Grep `@internal-start`）。将第 143 行：

```markdown
| `@internal-start` / `@internal-end` | 行注释定界对 | 块区域 | 删除两个定界行及其间的所有行（含纯注释与代码行） |
```

改为：

```markdown
| `@internal-start` / `@internal-end` | 行注释定界对 | 块区域 | 删除两个定界行及其间的所有注释（纯注释整行删除，行尾注释仅删注释部分），保留代码行 |
```

- [ ] **Step 2: 移除标记类型表中 `full-start`/`full-end` 行**

定位第 146-147 行，删除：

```markdown
# 删除这两行
| `# markstrip: full-start` | 区间起始行 | 区间内 | 区间内注释全量删除，保留代码 |
| `# markstrip: full-end` | 区间结束行 | 区间内 | 与 full-start 配对，闭区间 |
```

- [ ] **Step 3: 移除核心特性中 `full-start`/`full-end` 描述**

定位第 64 行（使用 Grep `full-start`），将：

```markdown
- **Pragma 指令式全量删注释**：`# markstrip: full` 文件级 / `full-start`/`full-end` 区间级指令
```

改为：

```markdown
- **Pragma 指令式全量删注释**：`# markstrip: full` 文件级全量删除指令
```

- [ ] **Step 4: 移除 `full-start`/`full-end` 示例**

定位示例章节（使用 Grep `full-start`），删除 `full-start`/`full-end` 相关代码示例块（约第 277-282 行）。

- [ ] **Step 5: 移除 pragma 交互表中的 `full-start/end` 行**

定位 pragma 交互表（使用 Grep `区间.*full-start`），删除该行（约第 303 行）：

```markdown
# 删除此行
| 区间 `full-start/end` | selective | 区间内 full，外 selective |
```

同时删除 pragma 嵌套说明（约第 307 行）：

```markdown
# 删除此行
- **pragma 是否支持嵌套**：不支持。内层 `full-start` 视为错配，输出 warning 后忽略。
```

- [ ] **Step 6: 更新已知限制**

定位已知限制第 6 条（使用 Grep `Pragma 不支持嵌套`），删除第 1018 行：

```markdown
# 删除此行
6. **Pragma 不支持嵌套**：`# markstrip: full-start` 采用单层闭区间语义，内层视为错配。
```

重新编号后续已知限制项（第 7-9 项 → 第 6-8 项）。

- [ ] **Step 7: 更新"已实现（v1.2）"清单**

定位第 1080 行（使用 Grep `已实现（v1.2）`），将：

```markdown
- [x] Pragma 指令系统（`# markstrip: full` / `full-start` / `full-end`）
```

改为：

```markdown
- [x] Pragma 指令系统（`# markstrip: full` 文件级全量删除）
```

### 3.2 design.md 变更

- [ ] **Step 8: 更新 v1.2 更新记录**

打开 `docs/markstrip-design.md`，定位第 1385 行（使用 Grep `v1.2`），将：

```markdown
| 2026-07-17 | v1.2 | 新增 pragma 指令系统（`# markstrip: full` / `full-start` / `full-end`）、`pragma_scanner` 模块、`BlockRange.mode` 字段 | Trae AI |
```

改为：

```markdown
| 2026-07-17 | v1.2 | 新增 pragma 指令系统（`# markstrip: full`）、`pragma_scanner` 模块 | Trae AI |
```

- [ ] **Step 9: 移除 `full-start`/`full-end` 章节**

定位 `full-start` 相关章节（第 385-433 行区域），删除以下内容：
- 第 385-386 行：标记类型表中的 `full-start`/`full-end` 行
- 第 393-394 行：区间级扫描器说明
- 第 405 行：区间 pragma 示例
- 第 412-433 行：`@internal` 块 vs `full-start/end` 对比表、错配说明、模式交互表

- [ ] **Step 10: 移除测试用例表中的 pragma 区间用例**

定位测试用例覆盖表（第 1217-1220 行），删除：

```markdown
# 删除以下 4 行
| `pragma_range` | 区间级 `full-start`/`full-end` 区间内 full，区间外 selective |
| `pragma_mismatched_end` | 孤立 `full-end` 输出 warning 且忽略 |
| `pragma_nested` | 嵌套 `full-start` 视为错配并 warning |
| Pragma 区间起始 | `# markstrip: full-start` | 区间内 | 区间内注释全量删除，保留代码 |
| Pragma 区间结束 | `# markstrip: full-end` | 区间内 | 与 full-start 配对，闭区间 |
```

- [ ] **Step 11: 修正 design.md 中 `@internal-start`/`@internal-end` 描述**

定位 `@internal-start` 在 design.md 中的描述，确认与 README 修正后的行为一致（仅删注释，保留代码）。

- [ ] **Step 12: 人工验证文档一致性**

检查 `README.md` 和 `docs/markstrip-design.md`：
- 目录锚点链接正确（`full-start`/`full-end` 已从 TOC 移除）
- 无遗留 `full-start` 或 `full-end` 字符串（除更新记录中"废弃"说明外）
- 表格列数对齐
- 已知限制编号连续

- [ ] **Step 13: 跑全量回归**

Run: `python -m pytest tests/ -v`
Expected: 全部通过。

- [ ] **Step 14: 提交**

```bash
git add README.md docs/markstrip-design.md
git commit -m "docs: 修正 @internal 块描述 + 移除 full-start/full-end 文档"
```

---

## Self-Review

**1. Spec coverage:**
- [x] 问题 1（README 描述错误）→ Task 3 Step 1 + Step 11
- [x] 问题 2（full-start/full-end 废弃）→ Task 1（代码）+ Task 2（测试）+ Task 3（文档）

**2. Placeholder scan:** 无 TBD/TODO/占位符。

**3. Type consistency:** 无新增类型或接口，仅删除。

## Execution Handoff

任务依赖链：Task 1 → Task 2 → Task 3（Task 3 也可独立执行，但建议按顺序确保代码变更后测试通过，文档最后修正）。