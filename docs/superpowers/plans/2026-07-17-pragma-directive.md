# Pragma 指令式注释过滤 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 markstrip 新增 `# markstrip: full` / `full-start` / `full-end` pragma 指令,支持文件级全量删注释与区间级全量删注释(保留代码)。

**Architecture:** 新增 `core/pragma_scanner.py` 纯函数模块(与 `block_scanner.py` 平级),`BlockRange` 加 `mode` 字段区分 "all"(删全部)/"comments"(只删注释)。pragma 逻辑在插件层,引擎零变更。

**Tech Stack:** Python 3.10+,标准库 `re`/`tokenize`/`ast`/`dataclasses`,pytest 测试框架,零运行时依赖。

**Spec:** `docs/superpowers/specs/2026-07-17-pragma-directive-design.md`

## Global Constraints

- pragma 前缀固定 `markstrip:`,不可配置,大小写敏感
- pragma 正则:`^\s*{prefix}\s*markstrip:\s*{directive}(?:\s|$)`,冒号两侧 `\s*` 容错
- `BlockRange.mode` 默认 `"all"`,向后兼容现有 `@internal-start/end` 行为
- warnings 复用现有链路:`pragma_scanner` → `config.warnings.extend()` → `StripResult.warnings` → CLI `--verbose`
- 现有 76 个测试必须全部通过(回归门槛)
- 导入顺序遵循 PEP 8(标准库→第三方→本地,每组空行分隔,组内字母序)
- 提交信息使用中文

---

## File Structure

| 文件 | 操作 | 职责 |
|------|------|------|
| `markstrip/core/pragma_scanner.py` | **新建** | `scan_file_pragma()`、`scan_full_ranges()`、`_build_pragma_regex()` 纯函数 |
| `markstrip/core/block_scanner.py` | **修改** | `BlockRange` 加 `mode: str = "all"` 字段 |
| `markstrip/languages/python_plugin.py` | **修改** | `strip_selective` 与 `_fallback_regex_selective` 接入 pragma |
| `markstrip/languages/markdown_plugin.py` | **修改** | `_fallback_strip` 接入 pragma |
| `tests/unit/test_pragma_scanner.py` | **新建** | pragma_scanner 单元测试 |
| `tests/golden/python/pragma_*.py` + `.expected.py` | **新建** | 6 组黄金测试 |
| `tests/integration/test_cli.py` | **修改** | pragma CLI 集成测试 |

---

### Task 1: pragma_scanner.scan_file_pragma(文件级检测)

**Files:**
- Create: `markstrip/core/pragma_scanner.py`
- Create: `tests/unit/test_pragma_scanner.py`

**Interfaces:**
- Consumes: 无(纯函数,仅用 `re` 标准库)
- Produces: `scan_file_pragma(lines: list[str], comment_prefix: str) -> bool`;`_build_pragma_regex(comment_prefix: str, directive: str) -> re.Pattern`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_pragma_scanner.py
"""pragma_scanner 单元测试。"""
from markstrip.core.pragma_scanner import scan_file_pragma


class TestScanFilePragma:
    """文件级 pragma 检测。"""

    def test_pragma_present(self):
        lines = ["# markstrip: full\n", "x = 1\n"]
        assert scan_file_pragma(lines, "#") is True

    def test_pragma_absent(self):
        lines = ["# 普通注释\n", "x = 1\n"]
        assert scan_file_pragma(lines, "#") is False

    def test_no_space_around_colon(self):
        lines = ["#markstrip:full\n"]
        assert scan_file_pragma(lines, "#") is True

    def test_extra_spaces(self):
        lines = ["#  markstrip :  full  \n"]
        assert scan_file_pragma(lines, "#") is True

    def test_trailing_text(self):
        lines = ["# markstrip: full  本文件全量清理\n"]
        assert scan_file_pragma(lines, "#") is True

    def test_case_sensitive(self):
        lines = ["# Markstrip: full\n"]
        assert scan_file_pragma(lines, "#") is False

    def test_only_full_directive(self):
        """full-start/full-end 不被 scan_file_pragma 识别。"""
        lines = ["# markstrip: full-start\n"]
        assert scan_file_pragma(lines, "#") is False

    def test_custom_prefix(self):
        lines = ["// markstrip: full\n"]
        assert scan_file_pragma(lines, "//") is True

    def test_pragma_anywhere(self):
        lines = ["x = 1\n", "y = 2\n", "# markstrip: full\n", "z = 3\n"]
        assert scan_file_pragma(lines, "#") is True

    def test_typo_not_recognized(self):
        lines = ["# markstrip: ful\n"]
        assert scan_file_pragma(lines, "#") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_pragma_scanner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'markstrip.core.pragma_scanner'`

- [ ] **Step 3: Write minimal implementation**

```python
# markstrip/core/pragma_scanner.py
"""Pragma 指令扫描器。

与 block_scanner.py 平级的纯函数模块,识别 # markstrip: <directive> 指令。
pragma 命名空间独立于 @internal 标记体系,语义为 full(全量删注释,保留代码)。
"""
import re

from markstrip.core.block_scanner import BlockRange, BlockScanResult


def _build_pragma_regex(comment_prefix: str, directive: str) -> re.Pattern:
    r"""构造 pragma 正则:^\s*{prefix}\s*markstrip:\s*{directive}(?:\s|$)。

    冒号两侧 \s* 容错,指令后须空白或行尾。
    """
    return re.compile(
        rf"^\s*{re.escape(comment_prefix)}\s*markstrip:\s*"
        rf"{re.escape(directive)}(?:\s|$)"
    )


def scan_file_pragma(lines: list[str], comment_prefix: str) -> bool:
    """检测是否存在 # markstrip: full(文件级 pragma)。

    扫描全部行,任意位置出现即返回 True。

    Args:
        lines: 源代码行列表(splitlines(keepends=True))。
        comment_prefix: 注释前缀,如 "#" 或 "//"。

    Returns:
        是否存在文件级 pragma。
    """
    regex = _build_pragma_regex(comment_prefix, "full")
    return any(regex.match(line) for line in lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_pragma_scanner.py -v`
Expected: 10 passed

- [ ] **Step 5: Run full regression**

Run: `python -m pytest -q`
Expected: 86 passed (76 existing + 10 new)

- [ ] **Step 6: Commit**

```bash
git add markstrip/core/pragma_scanner.py tests/unit/test_pragma_scanner.py
git commit -m "feat(pragma_scanner): 新增 scan_file_pragma 文件级 pragma 检测"
```

---

### Task 2: BlockRange.mode + pragma_scanner.scan_full_ranges(区间检测)

**Files:**
- Modify: `markstrip/core/block_scanner.py`(BlockRange 加 mode 字段)
- Modify: `markstrip/core/pragma_scanner.py`(加 scan_full_ranges)
- Modify: `tests/unit/test_pragma_scanner.py`(加区间测试)
- Modify: `tests/unit/test_block_scanner.py`(加 mode 默认值回归测试)

**Interfaces:**
- Consumes: `BlockRange`、`BlockScanResult` from `block_scanner`(Task 1 已导入)
- Produces: `scan_full_ranges(lines, comment_prefix) -> BlockScanResult`,ranges 中 `BlockRange.mode = "comments"`;`BlockRange.mode` 字段(default `"all"`)

- [ ] **Step 1: Write the failing test — BlockRange.mode 默认值**

```python
# 追加到 tests/unit/test_block_scanner.py 末尾
class TestBlockRangeMode:
    """BlockRange.mode 字段回归测试。"""

    def test_default_mode_is_all(self):
        from markstrip.core.block_scanner import BlockRange
        r = BlockRange(start_line=1, end_line=3)
        assert r.mode == "all"

    def test_explicit_mode_comments(self):
        from markstrip.core.block_scanner import BlockRange
        r = BlockRange(start_line=1, end_line=3, mode="comments")
        assert r.mode == "comments"
```

- [ ] **Step 2: Write the failing test — scan_full_ranges**

```python
# 追加到 tests/unit/test_pragma_scanner.py
from markstrip.core.pragma_scanner import scan_full_ranges


class TestScanFullRanges:
    """区间级 pragma 扫描。"""

    def test_single_range(self):
        lines = [
            "# markstrip: full-start\n",
            "# 注释 A\n",
            "x = 1\n",
            "# markstrip: full-end\n",
        ]
        result = scan_full_ranges(lines, "#")
        assert len(result.ranges) == 1
        assert result.ranges[0].start_line == 1
        assert result.ranges[0].end_line == 4
        assert result.ranges[0].mode == "comments"
        assert result.warnings == []

    def test_multiple_ranges(self):
        lines = [
            "# markstrip: full-start\n",
            "# a\n",
            "# markstrip: full-end\n",
            "y = 2\n",
            "# markstrip: full-start\n",
            "# b\n",
            "# markstrip: full-end\n",
        ]
        result = scan_full_ranges(lines, "#")
        assert len(result.ranges) == 2
        assert result.warnings == []

    def test_orphan_end(self):
        lines = ["# markstrip: full-end\n"]
        result = scan_full_ranges(lines, "#")
        assert result.ranges == []
        assert len(result.warnings) == 1
        assert "孤立" in result.warnings[0]

    def test_unclosed_start(self):
        lines = ["# markstrip: full-start\n", "# a\n"]
        result = scan_full_ranges(lines, "#")
        assert result.ranges == []
        assert len(result.warnings) == 1
        assert "未闭合" in result.warnings[0]

    def test_nested_start_ignored(self):
        lines = [
            "# markstrip: full-start\n",
            "# markstrip: full-start\n",
            "# a\n",
            "# markstrip: full-end\n",
        ]
        result = scan_full_ranges(lines, "#")
        assert len(result.ranges) == 1
        assert result.ranges[0].start_line == 1
        assert result.ranges[0].end_line == 4
        assert len(result.warnings) == 1
        assert "嵌套" in result.warnings[0]

    def test_whitespace_variations(self):
        lines = ["#markstrip:full-start\n", "#a\n", "#markstrip:full-end\n"]
        result = scan_full_ranges(lines, "#")
        assert len(result.ranges) == 1
        assert result.ranges[0].mode == "comments"

    def test_custom_prefix(self):
        lines = ["// markstrip: full-start\n", "// a\n", "// markstrip: full-end\n"]
        result = scan_full_ranges(lines, "//")
        assert len(result.ranges) == 1

    def test_no_pragma(self):
        lines = ["# 普通注释\n", "x = 1\n"]
        result = scan_full_ranges(lines, "#")
        assert result.ranges == []
        assert result.warnings == []
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_block_scanner.py::TestBlockRangeMode tests/unit/test_pragma_scanner.py::TestScanFullRanges -v`
Expected: FAIL — `BlockRange` 无 `mode` 字段;`scan_full_ranges` 未定义

- [ ] **Step 4: Add mode field to BlockRange**

```python
# markstrip/core/block_scanner.py — BlockRange dataclass 修改
@dataclass
class BlockRange:
    """块范围（1-based，含两端的定界行）。"""
    start_line: int
    end_line: int
    mode: str = "all"  # "all"=删全部(@internal-start/end), "comments"=只删注释(markstrip pragma)
```

- [ ] **Step 5: Implement scan_full_ranges**

```python
# markstrip/core/pragma_scanner.py — 追加 scan_full_ranges 函数

def scan_full_ranges(
    lines: list[str], comment_prefix: str
) -> BlockScanResult:
    """扫描 # markstrip: full-start / full-end 区间。

    返回 BlockScanResult,ranges 中 BlockRange.mode = 'comments'。
    块语义与 scan_blocks 一致(首 start 到首 end 闭区间、不支持嵌套、错配警告)。

    Args:
        lines: 源代码行列表(splitlines(keepends=True))。
        comment_prefix: 注释前缀,如 "#" 或 "//"。

    Returns:
        扫描结果,ranges 的 mode 均为 "comments"。
    """
    start_re = _build_pragma_regex(comment_prefix, "full-start")
    end_re = _build_pragma_regex(comment_prefix, "full-end")

    ranges: list[BlockRange] = []
    warnings: list[str] = []
    open_start: int | None = None

    for i, line in enumerate(lines, 1):
        if start_re.match(line):
            if open_start is not None:
                warnings.append(f"行 {i}: 嵌套 markstrip: full-start, 已忽略")
                continue
            open_start = i
        elif end_re.match(line):
            if open_start is None:
                warnings.append(f"行 {i}: 孤立 markstrip: full-end, 已忽略")
                continue
            ranges.append(
                BlockRange(
                    start_line=open_start,
                    end_line=i,
                    mode="comments",
                )
            )
            open_start = None

    if open_start is not None:
        warnings.append(
            f"行 {open_start}: 未闭合 markstrip: full-start, 已忽略"
        )

    return BlockScanResult(ranges=ranges, warnings=warnings)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_block_scanner.py::TestBlockRangeMode tests/unit/test_pragma_scanner.py::TestScanFullRanges -v`
Expected: 10 passed

- [ ] **Step 7: Run full regression**

Run: `python -m pytest -q`
Expected: 96 passed (86 + 2 BlockRange + 8 scan_full_ranges)

- [ ] **Step 8: Commit**

```bash
git add markstrip/core/block_scanner.py markstrip/core/pragma_scanner.py tests/unit/test_block_scanner.py tests/unit/test_pragma_scanner.py
git commit -m "feat(pragma_scanner): 新增 scan_full_ranges 区间检测与 BlockRange.mode 字段"
```

---

### Task 3: Python 插件文件级 pragma 集成

**Files:**
- Modify: `markstrip/languages/python_plugin.py:26-91`(strip_selective)
- Create: `tests/golden/python/pragma_full.py`
- Create: `tests/golden/python/pragma_full.expected.py`

**Interfaces:**
- Consumes: `scan_file_pragma` from `pragma_scanner`(Task 1);`scan_full_ranges` from `pragma_scanner`(Task 2,仅用于共存警告)
- Produces: `strip_selective` 在 tokenize 前检测文件级 pragma → 委托 `strip_full`

- [ ] **Step 1: Write the golden test file**

```python
# tests/golden/python/pragma_full.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# markstrip: full
# 这是一条普通注释
x = 1  # 行尾注释
# 另一条普通注释
y = 2


def foo():
    """这是一个 docstring。"""
    return x + y
```

```python
# tests/golden/python/pragma_full.expected.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
x = 1
y = 2


def foo():
    return x + y
```

- [ ] **Step 2: Run golden test to verify it fails**

Run: `python -m pytest tests/unit/test_python_plugin.py -k golden -v -x 2>&1 | findstr pragma_full`
Expected: FAIL — pragma_full 输出与 expected 不匹配(注释未被删除)

- [ ] **Step 3: Add import and file-level pragma check to strip_selective**

```python
# markstrip/languages/python_plugin.py — 修改导入区(第 6 行后追加)
from markstrip.core.pragma_scanner import scan_file_pragma, scan_full_ranges
```

```python
# markstrip/languages/python_plugin.py — strip_selective 方法体开头(第 39 行 lines = ... 之后)插入:
        # 文件级 pragma 检测
        if scan_file_pragma(lines, "#"):
            # 检查区间标记冗余
            pragma_scan = scan_full_ranges(lines, "#")
            if pragma_scan.ranges:
                config.warnings.append("文件级 full 已生效, 区间标记冗余")
            return self.strip_full(content, config)
```

- [ ] **Step 4: Run golden test to verify it passes**

Run: `python -m pytest tests/unit/test_python_plugin.py -k golden -v -x 2>&1 | findstr pragma_full`
Expected: PASS

- [ ] **Step 5: Run full regression**

Run: `python -m pytest -q`
Expected: 97 passed (96 + 1 golden)

- [ ] **Step 6: Commit**

```bash
git add markstrip/languages/python_plugin.py tests/golden/python/pragma_full.py tests/golden/python/pragma_full.expected.py
git commit -m "feat(python): strip_selective 接入文件级 pragma 检测并委托 strip_full"
```

---

### Task 4: Python 插件区间级 pragma 集成

**Files:**
- Modify: `markstrip/languages/python_plugin.py:26-91`(strip_selective 加 mode="comments" 处理)
- Modify: `markstrip/languages/python_plugin.py:382-453`(_fallback_regex_selective 加 pragma)
- Create: 5 组黄金测试

**Interfaces:**
- Consumes: `scan_full_ranges` from `pragma_scanner`(Task 2);`BlockRange.mode` from `block_scanner`(Task 2)
- Produces: strip_selective 与 _fallback_regex_selective 对 mode="comments" 区间执行 full 式注释删除(保留代码)

- [ ] **Step 1: Write the golden test files**

```python
# tests/golden/python/pragma_range.py
x = 1  # 区间外注释
# markstrip: full-start
# 注释 A
y = 2
# 注释 B
z = 3  # 行尾注释
# markstrip: full-end
w = 4  # @internal 行尾标记
```

```python
# tests/golden/python/pragma_range.expected.py
x = 1  # 区间外注释
y = 2
z = 3
w = 4
```

```python
# tests/golden/python/pragma_range_docstring.py
# markstrip: full-start
def foo():
    """这是一个 docstring。"""
    return 1
# markstrip: full-end
bar = 2
```

```python
# tests/golden/python/pragma_range_docstring.expected.py
def foo():
    return 1
bar = 2
```

```python
# tests/golden/python/pragma_mismatched_end.py
a = 1
# markstrip: full-end
b = 2
```

```python
# tests/golden/python/pragma_mismatched_end.expected.py
a = 1
# markstrip: full-end
b = 2
```

```python
# tests/golden/python/pragma_nested.py
# markstrip: full-start
# 外层注释
# markstrip: full-start
# 内层注释(嵌套,忽略)
# markstrip: full-end
c = 3
# markstrip: full-end
d = 4
```

```python
# tests/golden/python/pragma_nested.expected.py
c = 3
d = 4
```

```python
# tests/golden/python/pragma_with_selective.py
# @internal 区间外标记
x = 1
# markstrip: full-start
# 区间内注释
# @internal 区间内冗余标记
y = 2
# markstrip: full-end
# @internal 另一个区间外标记
z = 3
```

```python
# tests/golden/python/pragma_with_selective.expected.py
x = 1
y = 2
z = 3
```

- [ ] **Step 2: Run golden tests to verify they fail**

Run: `python -m pytest tests/unit/test_python_plugin.py -k golden -v -x 2>&1 | findstr pragma_range`
Expected: FAIL — 区间内注释未被删除

- [ ] **Step 3: Modify strip_selective — add pragma range handling**

在 `strip_selective` 方法中,`scan_blocks` 之后(第 58 行 `block_ranges = scan.ranges` 之后)插入 pragma 区间扫描,并修改 `_in_block` 逻辑与 COMMENT token 处理:

```python
# markstrip/languages/python_plugin.py — strip_selective 中,第 58 行后插入:
        # pragma 区间扫描
        pragma_scan = scan_full_ranges(lines, "#")
        config.warnings.extend(pragma_scan.warnings)
        pragma_ranges = pragma_scan.ranges

        def _in_pragma_range(line_num: int) -> bool:
            return any(
                r.start_line <= line_num <= r.end_line for r in pragma_ranges
            )
```

修改 COMMENT token 处理循环(第 65-83 行),在 `in_block` 判断后加 `in_pragma` 分支:

```python
        for tok in tokens:
            if tok.type == tokenize.COMMENT:
                in_block = _in_block(tok.start[0])
                in_pragma = _in_pragma_range(tok.start[0])
                if in_block:
                    # 块内：纯注释整行移除，内联仅删片段
                    if self._is_whole_line_comment(tok, lines):
                        comment_removals.append((tok.start[0], 0, -1))
                    else:
                        comment_removals.append(
                            (tok.start[0], tok.start[1], tok.end[1])
                        )
                elif in_pragma:
                    # pragma 区间：full 逻辑,删注释保留代码
                    if self._is_preserved_comment(tok, config):
                        continue
                    if self._is_whole_line_comment(tok, lines):
                        comment_removals.append((tok.start[0], 0, -1))
                    else:
                        comment_removals.append(
                            (tok.start[0], tok.start[1], tok.end[1])
                        )
                elif self._has_marker(tok.string, config):
                    # 块外逐行 @internal：纯注释整行移除，内联仅删片段
                    if self._is_whole_line_comment(tok, lines):
                        comment_removals.append((tok.start[0], 0, -1))
                    else:
                        comment_removals.append(
                            (tok.start[0], tok.start[1], tok.end[1])
                        )
```

修改 docstring 处理(第 85-88 行),加 pragma 区间检查:

```python
            if tok.type == tokenize.STRING:
                if self._is_docstring(tok, tokens):
                    in_pragma = _in_pragma_range(tok.start[0])
                    if in_pragma and not config.preserve_docstrings:
                        for line_num in range(tok.start[0], tok.end[0] + 1):
                            comment_removals.append((line_num, 0, -1))
                    else:
                        doc_removals = self._process_docstring(tok, config, lines)
                        comment_removals.extend(doc_removals)
```

- [ ] **Step 4: Modify _fallback_regex_selective — add pragma handling**

在 `_fallback_regex_selective` 方法中,`scan_blocks` 之后(第 408 行后)插入 pragma 扫描,并修改循环逻辑:

```python
# markstrip/languages/python_plugin.py — _fallback_regex_selective 中,第 408 行后插入:
        # pragma 区间扫描
        pragma_scan = scan_full_ranges(lines, "#")
        config.warnings.extend(pragma_scan.warnings)
        pragma_ranges = pragma_scan.ranges
```

在循环中(第 434-452 行),`_in_block_range` 判断后加 pragma 区间分支。修改 `for i, line in enumerate(lines, 1):` 循环体:

```python
        def _in_pragma_range(line_num: int) -> bool:
            return any(
                r.start_line <= line_num <= r.end_line for r in pragma_ranges
            )

        for i, line in enumerate(lines, 1):
            nl = _newline(line)
            body = line[:-len(nl)] if nl else line
            if _in_block_range(i):
                # 块内：纯注释行整行丢弃；否则删内联注释片段保留代码
                if any_comment_re.match(body):
                    continue
                cleaned = inline_any_re.sub("", body).rstrip()
                if cleaned:
                    out.append(cleaned + nl)
            elif _in_pragma_range(i):
                # pragma 区间：full 逻辑,删注释保留代码
                if any_comment_re.match(body):
                    continue
                cleaned = inline_any_re.sub("", body).rstrip()
                if cleaned:
                    out.append(cleaned + nl)
            else:
                # 块外：逐行 @internal（marker 边界已排除定界行）
                if full_re.match(body):
                    continue
                cleaned = inline_re.sub("", body)
                if cleaned.strip() == "":
                    continue
                out.append(cleaned.rstrip() + nl)
```

- [ ] **Step 5: Run golden tests to verify they pass**

Run: `python -m pytest tests/unit/test_python_plugin.py -k golden -v 2>&1 | findstr pragma`
Expected: 5 pragma golden tests PASS

- [ ] **Step 6: Run full regression**

Run: `python -m pytest -q`
Expected: 102 passed (97 + 5 golden)

- [ ] **Step 7: Commit**

```bash
git add markstrip/languages/python_plugin.py tests/golden/python/pragma_range*.py tests/golden/python/pragma_mismatched_end*.py tests/golden/python/pragma_nested*.py tests/golden/python/pragma_with_selective*.py
git commit -m "feat(python): strip_selective 与正则回退接入区间级 pragma 全量删注释保留代码"
```

---

### Task 5: Markdown 插件 pragma 集成

**Files:**
- Modify: `markstrip/languages/markdown_plugin.py:156-232`(_fallback_strip)
- Create: `tests/golden/markdown/pragma_in_yaml.md`
- Create: `tests/golden/markdown/pragma_in_yaml.expected.md`

**Interfaces:**
- Consumes: `scan_file_pragma`、`scan_full_ranges` from `pragma_scanner`(Task 1-2)
- Produces: `_fallback_strip` 对兜底语言(yaml/bash 等)接入文件级与区间级 pragma

- [ ] **Step 1: Write the golden test file**

````markdown
<!-- tests/golden/markdown/pragma_in_yaml.md -->
```yaml
# markstrip: full-start
key: value
# 内部配置注释
# markstrip: full-end
another: value
```
````

````markdown
<!-- tests/golden/markdown/pragma_in_yaml.expected.md -->
```yaml
key: value
another: value
```
````

- [ ] **Step 2: Run golden test to verify it fails**

Run: `python -m pytest tests/unit/test_markdown_plugin.py -k golden -v -x 2>&1 | findstr pragma_in_yaml`
Expected: FAIL — yaml 块内注释未被删除

- [ ] **Step 3: Modify _fallback_strip — add pragma handling**

```python
# markstrip/languages/markdown_plugin.py — 修改导入区(第 4 行后追加)
from markstrip.core.pragma_scanner import scan_file_pragma, scan_full_ranges
```

在 `_fallback_strip` 方法中,`prefix` 检查后(第 177 行 `if prefix is None: return code` 之后)插入 pragma 检测与区间扫描,并修改循环逻辑:

```python
# markstrip/languages/markdown_plugin.py — _fallback_strip 中,第 178 行(lines = ...)之后插入:
        # 文件级 pragma → 全量删注释
        if scan_file_pragma(lines, prefix):
            return self._fallback_full(lines, prefix, config)

        # pragma 区间扫描
        pragma_scan = scan_full_ranges(lines, prefix)
        config.warnings.extend(pragma_scan.warnings)
        pragma_ranges = pragma_scan.ranges

        def _in_pragma_range(line_num: int) -> bool:
            return any(
                r.start_line <= line_num <= r.end_line for r in pragma_ranges
            )
```

在循环中(第 215-230 行),`_in_block_range` 判断后加 pragma 区间分支:

```python
        for i, line in enumerate(lines, 1):
            nl = _newline(line)
            body = line[:-len(nl)] if nl else line
            if _in_block_range(i):
                if any_comment_re.match(body):
                    continue
                cleaned = inline_any_re.sub("", body).rstrip()
                if cleaned:
                    out.append(cleaned + nl)
            elif _in_pragma_range(i):
                # pragma 区间：full 逻辑,删注释保留代码
                if any_comment_re.match(body):
                    continue
                cleaned = inline_any_re.sub("", body).rstrip()
                if cleaned:
                    out.append(cleaned + nl)
            else:
                if full_re.match(body):
                    continue
                cleaned = inline_re.sub("", body)
                if cleaned.strip() == "":
                    continue
                out.append(cleaned.rstrip() + nl)
```

新增 `_fallback_full` 方法(全量删注释正则兜底):

```python
# markstrip/languages/markdown_plugin.py — MarkdownPlugin 类内新增方法:
    def _fallback_full(
        self,
        lines: list[str],
        prefix: str,
        config: StripConfig,
    ) -> str:
        """正则兜底的全量注释删除(文件级 pragma 触发)。

        删除所有注释行与行尾注释,保留代码。不保留 TODO/shebang
        (兜底语言无统一 shebang 约定,简化处理)。

        Args:
            lines: 代码行列表(splitlines(keepends=True))。
            prefix: 注释前缀。
            config: 清理配置(此方法不使用 preserve_* 字段)。

        Returns:
            清理后的代码。
        """
        any_comment_re = re.compile(rf"^\s*{re.escape(prefix)}")
        inline_any_re = re.compile(rf"\s*{re.escape(prefix)}.*$")

        def _newline(line: str) -> str:
            for nl in ("\r\n", "\n", "\r"):
                if line.endswith(nl):
                    return nl
            return ""

        out: list[str] = []
        for line in lines:
            nl = _newline(line)
            body = line[:-len(nl)] if nl else line
            if any_comment_re.match(body):
                continue
            cleaned = inline_any_re.sub("", body).rstrip()
            if cleaned:
                out.append(cleaned + nl)
        return "".join(out)
```

- [ ] **Step 4: Run golden test to verify it passes**

Run: `python -m pytest tests/unit/test_markdown_plugin.py -k golden -v -x 2>&1 | findstr pragma_in_yaml`
Expected: PASS

- [ ] **Step 5: Run full regression**

Run: `python -m pytest -q`
Expected: 103 passed (102 + 1 golden)

- [ ] **Step 6: Commit**

```bash
git add markstrip/languages/markdown_plugin.py tests/golden/markdown/pragma_in_yaml.md tests/golden/markdown/pragma_in_yaml.expected.md
git commit -m "feat(markdown): 兜底正则接入 pragma 文件级与区间级全量删注释"
```

---

### Task 6: CLI 集成测试

**Files:**
- Modify: `tests/integration/test_cli.py`

**Interfaces:**
- Consumes: 全部前序 Task 的功能
- Produces: CLI 层端到端验证

- [ ] **Step 1: Write the failing tests**

```python
# tests/integration/test_cli.py — 追加测试类
class TestCliPragma:
    """CLI pragma 指令集成测试。"""

    def test_cli_pragma_full_overrides_selective(self, tmp_path):
        """文件有 # markstrip: full,CLI selective → 输出 full 效果。"""
        src = tmp_path / "src.py"
        src.write_text(
            "# markstrip: full\n"
            "# 注释\n"
            "x = 1  # 行尾注释\n"
            "y = 2\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            [sys.executable, "-m", "markstrip", str(src), "--dry-run"],
            capture_output=True, text=True,
        )
        assert "# 注释" not in result.stdout
        assert "x = 1" in result.stdout
        assert "y = 2" in result.stdout

    def test_cli_pragma_full_with_cli_full_consistent(self, tmp_path):
        """文件有 pragma + CLI full → 一致(冗余无副作用)。"""
        src = tmp_path / "src.py"
        src.write_text(
            "# markstrip: full\n"
            "# 注释\n"
            "x = 1\n",
            encoding="utf-8",
        )
        r_pragma = subprocess.run(
            [sys.executable, "-m", "markstrip", str(src),
             "--dry-run", "--mode", "selective"],
            capture_output=True, text=True,
        )
        r_full = subprocess.run(
            [sys.executable, "-m", "markstrip", str(src),
             "--dry-run", "--mode", "full"],
            capture_output=True, text=True,
        )
        assert r_pragma.stdout == r_full.stdout

    def test_cli_verbose_pragma_warnings(self, tmp_path):
        """--verbose 输出 pragma 错配警告。"""
        src = tmp_path / "src.py"
        src.write_text(
            "# markstrip: full-end\n"
            "x = 1\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            [sys.executable, "-m", "markstrip", str(src),
             "--dry-run", "--verbose"],
            capture_output=True, text=True,
        )
        assert "Warning:" in result.stderr
        assert "孤立" in result.stderr
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/integration/test_cli.py::TestCliPragma -v`
Expected: FAIL — `TestCliPragma` 未定义(或部分 pass 如 Task 3 已使 pragma 全链路生效)

- [ ] **Step 3: Verify tests pass (no code change needed — pragma 已在前序 Task 实现)**

Run: `python -m pytest tests/integration/test_cli.py::TestCliPragma -v`
Expected: 3 passed

- [ ] **Step 4: Run full regression**

Run: `python -m pytest -q`
Expected: 106 passed (103 + 3 CLI)

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_cli.py
git commit -m "test(cli): 新增 pragma 指令 CLI 集成测试"
```

---

## Self-Review

### Spec 覆盖检查

| Spec 要求 | 覆盖 Task |
|-----------|-----------|
| `# markstrip: full` 文件级 pragma | Task 1(scan_file_pragma) + Task 3(Python 集成) + Task 5(Markdown 集成) |
| `# markstrip: full-start`/`full-end` 区间级 pragma | Task 2(scan_full_ranges) + Task 4(Python 集成) + Task 5(Markdown 集成) |
| BlockRange.mode 字段 | Task 2 |
| pragma 正则 `\s*` 容错 | Task 1(_build_pragma_regex) |
| 大小写敏感 | Task 1(test_case_sensitive) |
| 行尾可附说明 | Task 1(test_trailing_text) |
| CLI 交互矩阵 | Task 6(test_cli_pragma_full_overrides_selective, test_cli_pragma_full_with_cli_full_consistent) |
| 与 @internal-start/end 区别(只删注释保留代码) | Task 4(golden pragma_range) |
| 块语义(嵌套/孤立/未闭合) | Task 2(unit) + Task 4(golden pragma_nested, pragma_mismatched_end) |
| 文件级+区间级共存警告 | Task 3(strip_selective 共存检查) |
| 警告传播链路 | Task 2(warnings) + Task 6(test_cli_verbose_pragma_warnings) |
| 回归保护 76 测试 | 每个 Task 的 Step "Run full regression" |
| 范围边界 YAGNI | 无对应 Task(明确不实现) ✓ |

### 占位符扫描

无 TBD/TODO/模糊描述。所有步骤含完整代码。✓

### 类型一致性

- `scan_file_pragma(lines, comment_prefix) -> bool`:Task 1 定义,Task 3/5 消费 — 一致 ✓
- `scan_full_ranges(lines, comment_prefix) -> BlockScanResult`:Task 2 定义,Task 3/4/5 消费 — 一致 ✓
- `BlockRange.mode`:Task 2 定义为 `str`,默认 `"all"`,pragma 用 `"comments"` — 一致 ✓
- `_build_pragma_regex(comment_prefix, directive) -> re.Pattern`:Task 1 定义,Task 2 消费 — 一致 ✓
- `_fallback_full(lines, prefix, config) -> str`:Task 5 定义 — 一致 ✓
