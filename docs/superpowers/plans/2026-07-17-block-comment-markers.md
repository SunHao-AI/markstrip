# 块注释标记实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 markstrip 新增 `@internal-start` / `@internal-end` 块定界标记，并统一 selective 模式下被标记纯注释行的删除语义为"整行移除不留空行"。

**Architecture:** 新建纯函数模块 `BlockScanner` 作为块语义唯一真理源，供 Python 插件（tokenize 主路径 + 正则回退）与 Markdown 兜底共用；`StripConfig` 新增 3 个派生字段（`block_start_marker` / `block_end_marker`、`docstring_marker` 默认改空走派生）+ `warnings` 瞬态字段；`StripEngine` 调用插件前 `clear()` 瞬态通道、调用后复制 `list(config.warnings)` 并入 `StripResult.warnings`；selective 模式下纯注释标记行统一 `end_col=-1` 整行移除，修正 tokenize 路径与正则回退路径的既有不一致。

**Tech Stack:** Python 3.10+（`tokenize` / `ast` / `re` / `dataclasses` 标准库），`pytest` 黄金用例 + 单元测试。

## Global Constraints

- Python >= 3.10（`pyproject.toml` 的 `requires-python`）；ruff `line-length=100`、`target-version=py310`
- 注释前缀：Python `#`；Markdown 兜底语言 `#`（yaml/bash/shell）或 `//`（javascript/java/c/cpp）
- 定界行匹配正则：`^\s*{comment_prefix}\s*{marker}(?:\s|$)` —— 标记后须紧跟空白或行尾，避免 `@internal-started` 误匹配
- selective 模式删除语义：纯注释标记行 → `end_col=-1` 整行移除（含换行符不留空行）；代码行内联标记 → 仅删注释文本保留代码
- `full` 模式本次不改（其对缩进纯注释的同类不一致留待另行统一）
- `warnings` 传播契约：引擎每次调用插件**前** `config.warnings.clear()`；插件在处理过程中 `config.warnings.extend(...)` 回填；引擎调用后 `list(config.warnings)` **复制**并入 `StripResult.warnings`（复制而非引用，避免下次 `clear()` 误清空上一个结果）
- 提交信息用中文（工作区规则 `d:\WorkPlace\Pycharm\FastAPI-MS-Hao\AGENTS.md` 与 `.trae/rules/git-commit-message.md`）
- PowerShell 用分号 `;` 不用 `&&`（用户规则）
- 项目根：`d:\WorkPlace\Pycharm\markstrip`；测试命令：`python -m pytest tests/ -v`

## File Structure

| 文件 | 责任 | 改动类型 |
|---|---|---|
| `markstrip/core/config.py` | `StripConfig` 数据类 + 派生方法 + `warnings` 瞬态字段 | 修改 |
| `markstrip/core/block_scanner.py` | 块语义唯一真理源：`BlockRange` / `BlockScanResult` / `scan_blocks()` 纯函数 | 新建 |
| `markstrip/core/engine.py` | `strip()` 前置 `clear()` + 复制回填 `StripResult.warnings` | 修改 |
| `markstrip/languages/python_plugin.py` | tokenize 主路径接入块扫描 + 统一整行移除 + `_is_whole_line_comment` + `_has_marker` 排除定界 + `_process_docstring` 用 `effective_docstring_marker`；正则回退接入块 | 修改 |
| `markstrip/languages/markdown_plugin.py` | `_fallback_strip` 接入块（按语言前缀）+ `FALLBACK_COMMENT_PREFIX` 映射 | 修改 |
| `markstrip/cli.py` | `--docstring-marker` 默认改空 + 新增 `--block-start-marker` / `--block-end-marker` + `--verbose` 打印 warnings | 修改 |
| `tests/unit/test_config.py` | 派生字段与 `effective_*()` 测试 | 修改 |
| `tests/unit/test_block_scanner.py` | BlockScanner 8 组单测 | 新建 |
| `tests/unit/test_engine.py` | warnings 传播测试 | 修改 |
| `tests/unit/test_python_plugin.py` | 自定义 `line_marker` 联动块标记单测 | 修改 |
| `tests/golden/python/*.expected.py` | 4 组更新（删除语义统一） | 修改 |
| `tests/golden/python/block_*.py` | 5 组新增块黄金用例 | 新建 |
| `tests/golden/markdown/block_in_yaml.md` | 1 组新增兜底块黄金用例 | 新建 |
| `tests/integration/test_cli.py` | 块标记 CLI + verbose warnings 测试 | 修改 |

---

## Task 1: StripConfig 派生字段与 warnings 瞬态通道

**Files:**
- Modify: `markstrip/core/config.py`
- Test: `tests/unit/test_config.py`

**Interfaces:**
- Produces: `StripConfig.block_start_marker` / `block_end_marker`（默认 `""`）、`StripConfig.docstring_marker` 默认改 `""`、`StripConfig.warnings: list[str]`、`StripConfig.effective_docstring_marker() -> str`、`StripConfig.effective_block_start() -> str`、`StripConfig.effective_block_end() -> str`

- [ ] **Step 1: 写失败测试（更新 `tests/unit/test_config.py`）**

在 `tests/unit/test_config.py` 末尾追加：

```python
def test_default_derived_markers():
    """默认 line_marker=@internal 时派生标记与现状一致。"""
    config = StripConfig()
    assert config.docstring_marker == ""
    assert config.block_start_marker == ""
    assert config.block_end_marker == ""
    assert config.effective_docstring_marker() == "@internal-docstring"
    assert config.effective_block_start() == "@internal-start"
    assert config.effective_block_end() == "@internal-end"


def test_custom_line_marker_derives_all():
    """改 line_marker → 三类派生标记联动。"""
    config = StripConfig(line_marker="@private")
    assert config.effective_docstring_marker() == "@private-docstring"
    assert config.effective_block_start() == "@private-start"
    assert config.effective_block_end() == "@private-end"


def test_explicit_overrides_derivation():
    """显式设置非空值时不走派生。"""
    config = StripConfig(
        line_marker="@internal",
        docstring_marker="@secret-doc",
        block_start_marker="@secret-begin",
        block_end_marker="@secret-end",
    )
    assert config.effective_docstring_marker() == "@secret-doc"
    assert config.effective_block_start() == "@secret-begin"
    assert config.effective_block_end() == "@secret-end"


def test_warnings_default_empty():
    config = StripConfig()
    assert config.warnings == []


def test_warnings_independent():
    """每个 StripConfig 实例的 warnings 应独立。"""
    c1 = StripConfig()
    c2 = StripConfig()
    c1.warnings.append("x")
    assert c2.warnings == []
```

同时更新现有 `test_default_config`（因 `docstring_marker` 默认值由 `"@internal-docstring"` 改为 `""`）：

```python
def test_default_config():
    config = StripConfig()
    assert config.line_marker == "@internal"
    assert config.docstring_marker == ""
    assert config.block_start_marker == ""
    assert config.block_end_marker == ""
    assert config.preserve_docstrings is True
    assert config.preserve_todo is True
    assert config.custom_markers == []
    assert config.warnings == []
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd d:\WorkPlace\Pycharm\markstrip; python -m pytest tests/unit/test_config.py -v`
Expected: FAIL —— `AssertionError: assert '@internal-docstring' == ''`（`docstring_marker` 默认值仍是旧的）以及 `effective_*()` 方法不存在（`AttributeError`）。

- [ ] **Step 3: 实现（改写 `markstrip/core/config.py` 全文）**

```python
"""清理配置。"""
from dataclasses import dataclass, field


@dataclass
class StripConfig:
    """标记式注释清理配置。

    Attributes:
        line_marker: 行级标记符号，匹配此标记的注释行将被删除。
        docstring_marker: 整体 docstring 标记，空串时自动派生为
            f"{line_marker}-docstring"。
        block_start_marker: 块起始定界标记，空串时自动派生为
            f"{line_marker}-start"。
        block_end_marker: 块结束定界标记，空串时自动派生为
            f"{line_marker}-end"。
        preserve_docstrings: full 模式下是否保留 docstring。
        preserve_todo: full 模式下是否保留 TODO/FIXME 注释。
        custom_markers: 自定义额外标记列表，与 line_marker 一起匹配。
        warnings: 引擎瞬态回填通道，由引擎每次调用插件前 clear()，
            插件回填，引擎复制后并入 StripResult.warnings。非用户配置。
    """
    line_marker: str = "@internal"
    docstring_marker: str = ""
    block_start_marker: str = ""
    block_end_marker: str = ""
    preserve_docstrings: bool = True
    preserve_todo: bool = True
    custom_markers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def effective_docstring_marker(self) -> str:
        """返回实际生效的 docstring 标记（空则从 line_marker 派生）。"""
        return self.docstring_marker or f"{self.line_marker}-docstring"

    def effective_block_start(self) -> str:
        """返回实际生效的块起始标记（空则从 line_marker 派生）。"""
        return self.block_start_marker or f"{self.line_marker}-start"

    def effective_block_end(self) -> str:
        """返回实际生效的块结束标记（空则从 line_marker 派生）。"""
        return self.block_end_marker or f"{self.line_marker}-end"
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd d:\WorkPlace\Pycharm\markstrip; python -m pytest tests/unit/test_config.py -v`
Expected: PASS —— 7 个测试全绿。

- [ ] **Step 5: 检查回归（现有依赖 docstring_marker 默认值的代码）**

Run: `cd d:\WorkPlace\Pycharm\markstrip; python -m pytest tests/ -v`
Expected: 部分黄金用例可能因 `docstring_marker` 默认值变化而失败（如果它们依赖默认值）。实际上 `test_python_plugin.py` 的黄金测试用 `StripConfig()` 默认值，`effective_docstring_marker()` 返回 `@internal-docstring` 与旧行为一致，所以应仍 PASS。`test_cli.py` 不传 `--docstring-marker`，CLI 默认仍是 `"@internal-docstring"`（Task 7 才改 CLI 默认）。预期全绿。若有 failure，记录现象——但不应有。

- [ ] **Step 6: 提交**

```bash
cd d:\WorkPlace\Pycharm\markstrip
git add markstrip/core/config.py tests/unit/test_config.py
git commit -m "feat(config): 新增块标记派生字段与 warnings 瞬态通道"
```

---

## Task 2: BlockScanner 纯函数模块

**Files:**
- Create: `markstrip/core/block_scanner.py`
- Test: `tests/unit/test_block_scanner.py`

**Interfaces:**
- Produces: `BlockRange(start_line: int, end_line: int)`（1-based，含定界行）、`BlockScanResult(ranges: list[BlockRange], warnings: list[str])`、`scan_blocks(lines: list[str], comment_prefix: str, start_marker: str, end_marker: str) -> BlockScanResult`
- Consumes: 无（纯函数，不依赖 config）

- [ ] **Step 1: 写失败测试（新建 `tests/unit/test_block_scanner.py`）**

```python
"""BlockScanner 单元测试。"""
from markstrip.core.block_scanner import (
    BlockRange,
    BlockScanResult,
    scan_blocks,
)


def test_single_block():
    lines = [
        "# @internal-start\n",
        "# inside\n",
        "# @internal-end\n",
    ]
    result = scan_blocks(lines, "#", "@internal-start", "@internal-end")
    assert result.ranges == [BlockRange(1, 3)]
    assert result.warnings == []


def test_multiple_blocks():
    lines = [
        "# @internal-start\n",
        "# a\n",
        "# @internal-end\n",
        "# keep\n",
        "# @internal-start\n",
        "# b\n",
        "# @internal-end\n",
    ]
    result = scan_blocks(lines, "#", "@internal-start", "@internal-end")
    assert result.ranges == [BlockRange(1, 3), BlockRange(5, 7)]
    assert result.warnings == []


def test_start_without_end():
    lines = [
        "# @internal-start\n",
        "# inside\n",
    ]
    result = scan_blocks(lines, "#", "@internal-start", "@internal-end")
    assert result.ranges == []
    assert len(result.warnings) == 1
    assert "行 1" in result.warnings[0]
    assert "@internal-end" in result.warnings[0]


def test_end_without_start():
    lines = [
        "# inside\n",
        "# @internal-end\n",
    ]
    result = scan_blocks(lines, "#", "@internal-start", "@internal-end")
    assert result.ranges == []
    assert len(result.warnings) == 1
    assert "行 2" in result.warnings[0]
    assert "@internal-start" in result.warnings[0]


def test_nested_start_ignored_with_warning():
    lines = [
        "# @internal-start\n",
        "# @internal-start\n",
        "# inside\n",
        "# @internal-end\n",
    ]
    result = scan_blocks(lines, "#", "@internal-start", "@internal-end")
    assert result.ranges == [BlockRange(1, 4)]
    assert len(result.warnings) == 1
    assert "行 2" in result.warnings[0]
    assert "嵌套" in result.warnings[0]


def test_custom_prefix_slash_slash():
    lines = [
        "// @internal-start\n",
        "// inside\n",
        "// @internal-end\n",
    ]
    result = scan_blocks(lines, "//", "@internal-start", "@internal-end")
    assert result.ranges == [BlockRange(1, 3)]
    assert result.warnings == []


def test_marker_with_suffix_not_matched():
    """@internal-started 不应被识别为 start。"""
    lines = [
        "# @internal-started\n",
        "# @internal-end\n",
    ]
    result = scan_blocks(lines, "#", "@internal-start", "@internal-end")
    assert result.ranges == []
    assert len(result.warnings) == 1  # end 无匹配 start


def test_indented_delimiter():
    """缩进的定界行应被识别。"""
    lines = [
        "    # @internal-start\n",
        "    # inside\n",
        "    # @internal-end\n",
    ]
    result = scan_blocks(lines, "#", "@internal-start", "@internal-end")
    assert result.ranges == [BlockRange(1, 3)]
    assert result.warnings == []


def test_delimiter_with_trailing_text_allowed():
    """定界行标记后允许有说明文字。"""
    lines = [
        "# @internal-start ここから内部\n",
        "# inside\n",
        "# @internal-end ここまで\n",
    ]
    result = scan_blocks(lines, "#", "@internal-start", "@internal-end")
    assert result.ranges == [BlockRange(1, 3)]
    assert result.warnings == []


def test_custom_derived_markers():
    """scan_blocks 接收任意 marker，验证 @private 联动。"""
    lines = [
        "# @private-start\n",
        "# inside\n",
        "# @private-end\n",
    ]
    result = scan_blocks(lines, "#", "@private-start", "@private-end")
    assert result.ranges == [BlockRange(1, 3)]
    assert result.warnings == []


def test_blockscan_result_dataclass():
    r = BlockScanResult(ranges=[BlockRange(1, 2)], warnings=["w"])
    assert r.ranges[0].start_line == 1
    assert r.ranges[0].end_line == 2
    assert r.warnings == ["w"]
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd d:\WorkPlace\Pycharm\markstrip; python -m pytest tests/unit/test_block_scanner.py -v`
Expected: FAIL —— `ModuleNotFoundError: No module named 'markstrip.core.block_scanner'`。

- [ ] **Step 3: 实现（新建 `markstrip/core/block_scanner.py`）**

```python
"""块定界扫描器：纯函数，供 Python 插件与 Markdown 兜底共用。

块语义的唯一真理源。单趟扫描，严格容错，不支持嵌套：
内层 start 视为错配并忽略 + 警告；未闭合/无匹配的定界行均忽略 + 警告。
"""
import re
from dataclasses import dataclass, field


@dataclass
class BlockRange:
    """块范围（1-based，含两端的定界行）。"""
    start_line: int
    end_line: int


@dataclass
class BlockScanResult:
    """块扫描结果。"""
    ranges: list[BlockRange] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _build_delimiter_regex(comment_prefix: str, marker: str) -> re.Pattern:
    """构造定界行正则：^\s*{prefix}\s*{marker}(?:\s|$)。

    要求标记后紧跟空白或行尾，避免 @internal-started 等伪前缀误匹配。
    """
    escaped_prefix = re.escape(comment_prefix)
    escaped_marker = re.escape(marker)
    return re.compile(
        rf"^\s*{escaped_prefix}\s*{escaped_marker}(?:\s|$)"
    )


def scan_blocks(
    lines: list[str],
    comment_prefix: str,
    start_marker: str,
    end_marker: str,
) -> BlockScanResult:
    """扫描行列表，返回块范围与警告。

    Args:
        lines: 源行列表（含换行符，splitlines(keepends=True) 风格）。
        comment_prefix: 注释前缀，如 "#" 或 "//"（不含空白）。
        start_marker: 块起始标记文本，如 "@internal-start"。
        end_marker: 块结束标记文本，如 "@internal-end"。

    Returns:
        BlockScanResult，ranges 为配对成功的块范围（1-based，含定界行），
        warnings 为错配定界行的警告信息列表。
    """
    start_re = _build_delimiter_regex(comment_prefix, start_marker)
    end_re = _build_delimiter_regex(comment_prefix, end_marker)

    open_start: int | None = None
    ranges: list[BlockRange] = []
    warnings: list[str] = []

    for i, line in enumerate(lines, 1):
        is_start = start_re.match(line) is not None
        is_end = end_re.match(line) is not None
        if is_start:
            if open_start is not None:
                warnings.append(
                    f"行 {i}: 嵌套 {start_marker}，已忽略"
                )
                continue
            open_start = i
        elif is_end:
            if open_start is None:
                warnings.append(
                    f"行 {i}: 无匹配 {start_marker} 的 {end_marker}，已忽略"
                )
                continue
            ranges.append(BlockRange(open_start, i))
            open_start = None

    if open_start is not None:
        warnings.append(
            f"行 {open_start}: {start_marker} 缺少匹配 {end_marker}，已忽略"
        )

    return BlockScanResult(ranges=ranges, warnings=warnings)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd d:\WorkPlace\Pycharm\markstrip; python -m pytest tests/unit/test_block_scanner.py -v`
Expected: PASS —— 11 个测试全绿。

- [ ] **Step 5: 提交**

```bash
cd d:\WorkPlace\Pycharm\markstrip
git add markstrip/core/block_scanner.py tests/unit/test_block_scanner.py
git commit -m "feat(block_scanner): 新增块定界扫描器纯函数模块"
```

---

## Task 3: 引擎 warnings 传播契约

**Files:**
- Modify: `markstrip/core/engine.py`
- Test: `tests/unit/test_engine.py`

**Interfaces:**
- Consumes: `StripConfig.warnings`（Task 1）
- Produces: `StripResult.warnings` 由引擎复制 `list(config.warnings)` 填充

- [ ] **Step 1: 写失败测试（追加到 `tests/unit/test_engine.py`）**

在 `tests/unit/test_engine.py` 末尾追加：

```python
def test_strip_no_warnings_by_default():
    """正常 selective 清理应无警告。"""
    content = "# @internal 删除\nx = 1\n"
    result = strip(content, language="python", mode="selective")
    assert result.warnings == []


def test_strip_warnings_not_aliased_across_calls():
    """连续两次调用，第二次 clear() 不应清空第一次的 warnings。"""
    # 第一次：无块标记，无警告
    r1 = strip("# @internal 删除\nx = 1\n", language="python")
    # 第二次：仍无警告，但内部会 clear()
    r2 = strip("x = 1\n", language="python")
    assert r1.warnings == []
    assert r2.warnings == []
    # 关键：r1.warnings 必须是独立副本，不被第二次 clear 影响
    r1.warnings.append("manual")
    assert r2.warnings == []


def test_strip_warnings_propagated_from_plugin():
    """插件回填的 warnings 应出现在 StripResult.warnings。

    用块错配场景触发（Task 5 实现，此处先标记 xfail，Task 5 完成后转 pass）。
    """
    import pytest
    content = "# @internal-start\n# inside\nx = 1\n"
    result = strip(content, language="python", mode="selective")
    # Task 5 完成前块功能未接入，warnings 应为空
    # Task 5 完成后应有一条 "缺少匹配" 警告
    if not result.warnings:
        pytest.xfail("块功能未接入，warnings 暂为空（Task 5 完成后转 pass）")
    assert any("@internal-end" in w for w in result.warnings)
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd d:\WorkPlace\Pycharm\markstrip; python -m pytest tests/unit/test_engine.py -v`
Expected: `test_strip_no_warnings_by_default` 与 `test_strip_warnings_not_aliased_across_calls` FAIL —— 现有 `StripResult` 未填充 `warnings` 字段（默认空但引擎未传入），`r1.warnings.append("manual")` 后 `r2.warnings` 也可能受影响（若引擎未复制）。实际现有 `engine.py` 根本没碰 warnings，所以 `result.warnings` 是 dataclass 默认 `[]`，两个测试会因 `r1.warnings is r2.warnings`（若 dataclass 默认共享）而 FAIL。预期 FAIL。

- [ ] **Step 3: 实现（修改 `markstrip/core/engine.py` 的 `strip` 方法）**

将 `strip` 方法中 `config = config or StripConfig()` 之后、`plugin = self._resolve_plugin(...)` 之后，以及返回 `StripResult` 之前，改为：

```python
        config = config or StripConfig()

        plugin = self._resolve_plugin(language, filename, content)
        if plugin is None:
            return StripResult(
                cleaned_content=content,
                removed_count=0,
                warnings=["无法识别语言，跳过处理"],
            )

        # warnings 瞬态通道：调用插件前清空，插件回填，调用后复制并入结果
        config.warnings.clear()

        if mode == "full":
            cleaned = plugin.strip_full(content, config)
        else:
            cleaned = plugin.strip_selective(content, config)

        # 统计变更/删除行数
        original_lines = content.splitlines()
        cleaned_lines = cleaned.splitlines()
        removed_count = sum(
            1 for o, c in zip(original_lines, cleaned_lines) if o != c
        ) + max(0, len(original_lines) - len(cleaned_lines))

        return StripResult(
            cleaned_content=cleaned,
            removed_count=removed_count,
            detected_language=plugin.name,
            warnings=list(config.warnings),
        )
```

（其余 `_resolve_plugin` 不变。）

- [ ] **Step 4: 运行测试验证通过**

Run: `cd d:\WorkPlace\Pycharm\markstrip; python -m pytest tests/unit/test_engine.py -v`
Expected: PASS —— `test_strip_no_warnings_by_default`、`test_strip_warnings_not_aliased_across_calls` 通过；`test_strip_warnings_propagated_from_plugin` 走 `xfail` 分支（块功能未接入）。

- [ ] **Step 5: 检查回归**

Run: `cd d:\WorkPlace\Pycharm\markstrip; python -m pytest tests/ -v`
Expected: 全绿（warnings 默认空，不破坏现有断言）。

- [ ] **Step 6: 提交**

```bash
cd d:\WorkPlace\Pycharm\markstrip
git add markstrip/core/engine.py tests/unit/test_engine.py
git commit -m "feat(engine): 接入 warnings 瞬态通道并复制并入 StripResult"
```

---

## Task 4: Python 插件统一删除语义（不含块接入）

**Files:**
- Modify: `markstrip/languages/python_plugin.py`
- Test: `tests/golden/python/internal_comment.expected.py`、`tests/golden/python/docstring_selective.expected.py`（更新）；`tests/unit/test_python_plugin.py`（更新黄金断言数量）

**Interfaces:**
- Consumes: `StripConfig.effective_docstring_marker()`、`StripConfig.effective_block_start()`、`StripConfig.effective_block_end()`（Task 1）
- Produces: selective 模式逐行 `@internal` 纯注释行与 docstring 内 `@internal` 行均整行移除（`end_col=-1`）；`_has_marker` 排除块定界行；新增 `_is_whole_line_comment` 辅助

- [ ] **Step 1: 更新现有黄金期望（代表新期望行为）**

改写 `tests/golden/python/internal_comment.expected.py` 全文为：

```python
# 普通注释，应保留
x = 1
# 另一条普通注释
y = 2
```

（原文件第 2 行为空行，现整行删除，共 4 行。）

改写 `tests/golden/python/docstring_selective.expected.py` 全文为：

```python
def online_predict():
    """
    Online 推理任务调度


    Online 任务双重超时控制:
    Layer 1: requests.timeout
    """

    timeout = 1
    return timeout
```

（原 13 行；2 行 `@internal` 整行删除后剩 11 行：行 4 空行保留 + 原"行 7 空行"上移为新的空行，共 2 个空行夹在"Online 推理任务调度"与"Online 任务双重超时控制"之间。）

- [ ] **Step 2: 运行黄金测试验证失败**

Run: `cd d:\WorkPlace\Pycharm\markstrip; python -m pytest tests/unit/test_python_plugin.py -v`
Expected: FAIL —— `test_python_selective_golden[internal_comment]` 与 `[docstring_selective]` 失败（代码仍旧行为：纯注释 `@internal` 行被清空成空行而非整行删除）。

- [ ] **Step 3: 实现（修改 `markstrip/languages/python_plugin.py`）**

3a. 修改 `strip_selective` 中遍历 COMMENT 的分支（将逐行 `@internal` 纯注释行改为整行移除）。把现有：

```python
        for tok in tokens:
            if tok.type == tokenize.COMMENT:
                if self._has_marker(tok.string, config):
                    comment_removals.append(
                        (tok.start[0], tok.start[1], tok.end[1])
                    )
```

改为：

```python
        for tok in tokens:
            if tok.type == tokenize.COMMENT:
                if self._has_marker(tok.string, config):
                    if self._is_whole_line_comment(tok, lines):
                        # 纯注释标记行：整行移除（含换行不留空行）
                        comment_removals.append((tok.start[0], 0, -1))
                    else:
                        # 内联标记注释：仅删注释片段保留代码
                        comment_removals.append(
                            (tok.start[0], tok.start[1], tok.end[1])
                        )
```

3b. 新增 `_is_whole_line_comment` 方法（放在 `_has_marker` 之前）：

```python
    def _is_whole_line_comment(
        self, tok: tokenize.TokenInfo, lines: list[str]
    ) -> bool:
        """判断注释是否独占整行（行首到注释起点全为空白）。

        覆盖顶格注释与缩进注释。

        Args:
            tok: COMMENT token。
            lines: 原始行列表。

        Returns:
            True 表示该行从行首到注释起点之间全为空白。
        """
        line_text = lines[tok.start[0] - 1]
        before = line_text[: tok.start[1]]
        return before.strip() == ""
```

3c. 修改 `_has_marker` 排除块定界标记（避免 `@internal-start`/`-end` 被当作逐行 `@internal` 误删；本任务未接入块功能，定界行应作为普通注释保留）：

```python
    def _has_marker(self, comment_text: str, config: StripConfig) -> bool:
        """检查注释是否包含行级标记（排除块定界标记）。

        Args:
            comment_text: 注释文本（含 # 前缀）。
            config: 清理配置。

        Returns:
            是否包含行级标记。
        """
        markers = [config.line_marker] + config.custom_markers
        stripped = comment_text.lstrip("#").strip()
        # 排除块定界标记，避免 @internal-start/-end 被当作逐行 @internal
        block_delims = {
            config.effective_block_start(),
            config.effective_block_end(),
        }
        if any(stripped.startswith(d) for d in block_delims):
            return False
        for marker in markers:
            if stripped.startswith(marker):
                return True
        return False
```

3d. 修改 `_process_docstring`：整体标记用 `effective_docstring_marker()`；docstring 内逐行 `@internal` 由"清空成空行"改为整行移除。把现有 `_process_docstring` 全文替换为：

```python
    def _process_docstring(
        self,
        tok: tokenize.TokenInfo,
        config: StripConfig,
        lines: list[str],
    ) -> list[tuple[int, int, int]]:
        """处理单个 docstring，返回需删除的位置。

        Args:
            tok: docstring 的 STRING token。
            config: 清理配置。
            lines: 原始行列表。

        Returns:
            需要删除的 (line_num, start_col, end_col) 列表。
            end_col=-1 表示删除整行（含换行符）。
        """
        try:
            content = ast.literal_eval(tok.string)
        except (ValueError, SyntaxError):
            return []

        doc_lines = content.split("\n")

        # 检查整体 docstring 标记（整段删除）
        docstring_marker = config.effective_docstring_marker()
        has_whole_marker = any(
            line.strip().startswith(docstring_marker)
            for line in doc_lines
        )
        if has_whole_marker:
            removals = []
            for line_num in range(tok.start[0], tok.end[0] + 1):
                removals.append((line_num, 0, -1))
            return removals

        # 逐行检查行级标记（整行移除，不留空行）
        markers = [config.line_marker] + config.custom_markers
        block_delims = {
            config.effective_block_start(),
            config.effective_block_end(),
        }
        removals: list[tuple[int, int, int]] = []
        for i, line in enumerate(doc_lines):
            stripped = line.strip()
            # 排除块定界标记
            if any(stripped.startswith(d) for d in block_delims):
                continue
            for marker in markers:
                if stripped.startswith(marker):
                    source_line = tok.start[0] + i
                    # 整行移除（含换行符）
                    removals.append((source_line, 0, -1))
                    break

        return removals
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd d:\WorkPlace\Pycharm\markstrip; python -m pytest tests/unit/test_python_plugin.py -v`
Expected: PASS —— 所有 selective 黄金用例（含已更新的 `internal_comment` / `docstring_selective`）与 `full_mode` 黄金均绿。

- [ ] **Step 5: 检查 Markdown 黄金回归（python 块内 @internal 也应整行移除）**

Run: `cd d:\WorkPlace\Pycharm\markstrip; python -m pytest tests/unit/test_markdown_plugin.py -v`
Expected: FAIL —— `code_block_delegation` 与 `html_comment` 黄金用例失败（委托给 Python 插件，现 python 块内 `@internal` 纯注释空行被整行删除，但旧 `.expected.md` 仍含空行）。这是预期失败，Task 6 会更新这两个 expected。先记录现象，不提交。

- [ ] **Step 6: 更新 Markdown 黄金期望（提前到本任务，因属同一 breaking change）**

改写 `tests/golden/markdown/code_block_delegation.expected.md` 全文为：

````markdown
# 文档标题

```python
# 普通注释保留
x = 1
```

一些文字

```python
def func():
    """docstring"""
    return 1
```
````

改写 `tests/golden/markdown/html_comment.expected.md` 全文为：

````markdown
# 文档

<!-- 这条 HTML 注释应保留 -->

```python
x = 1
```
````

- [ ] **Step 7: 运行全部测试验证通过**

Run: `cd d:\WorkPlace\Pycharm\markstrip; python -m pytest tests/ -v`
Expected: PASS —— 所有黄金用例与单元/集成测试全绿。

- [ ] **Step 8: 提交**

```bash
cd d:\WorkPlace\Pycharm\markstrip
git add markstrip/languages/python_plugin.py tests/golden/python/internal_comment.expected.py tests/golden/python/docstring_selective.expected.py tests/golden/markdown/code_block_delegation.expected.md tests/golden/markdown/html_comment.expected.md
git commit -m "feat(python): 统一 selective 纯注释标记行为整行移除并更新黄金用例"
```

---

## Task 5: Python 插件接入块扫描（tokenize 主路径 + 正则回退）

**Files:**
- Modify: `markstrip/languages/python_plugin.py`
- Test: `tests/golden/python/block_comment.py` + `.expected.py`（新建）、`block_with_code.py` + `.expected.py`（新建）、`block_mismatched_start.py` + `.expected.py`（新建）、`block_mismatched_end.py` + `.expected.py`（新建）、`block_nested.py` + `.expected.py`（新建）；`tests/unit/test_python_plugin.py`（追加自定义 line_marker 联动单测）；`tests/unit/test_engine.py`（移除 Task 3 的 xfail）

**Interfaces:**
- Consumes: `scan_blocks`（Task 2）、`StripConfig.effective_block_start/end`（Task 1）、`_is_whole_line_comment` / `_has_marker`（Task 4）
- Produces: tokenize 路径与正则回退路径均支持块定界；块内纯注释行整行移除、内联注释仅删片段

- [ ] **Step 1: 写 5 组新增黄金用例 input**

新建 `tests/golden/python/block_comment.py`：

```python
# @internal-start
# 这是一段被注释掉的代码
# logger = logging.getLogger("celery")
# logger.setLevel(logging.INFO)
# @internal-end
x = 1
```

新建 `tests/golden/python/block_with_code.py`：

```python
# @internal-start
x = 1  # @internal 行尾注释
y = 2  # 普通行尾注释
# 纯注释行应整行删除
# @internal-end
z = 3
```

新建 `tests/golden/python/block_mismatched_start.py`：

```python
# @internal-start
# 这行不会被删除（start 缺匹配 end）
x = 1
```

新建 `tests/golden/python/block_mismatched_end.py`：

```python
x = 1
# 这行不会被删除（end 缺匹配 start）
# @internal-end
```

新建 `tests/golden/python/block_nested.py`：

```python
# @internal-start
# @internal-start
# 内层 start 应被忽略
# @internal-end
# 外层仍在块内
# @internal-end
x = 1
```

- [ ] **Step 2: 写 5 组新增黄金用例 expected**

新建 `tests/golden/python/block_comment.expected.py`（块内 5 行 + 定界行共 5 行整行删除）：

```python
x = 1
```

新建 `tests/golden/python/block_with_code.expected.py`（块内：行1定界整行删；行2/3保留代码删内联注释；行4纯注释整行删；行5定界整行删）：

```python
x = 1
y = 2
z = 3
```

新建 `tests/golden/python/block_mismatched_start.expected.py`（start 缺 end → 忽略该 start，定界行作普通注释保留）：

```python
# @internal-start
# 这行不会被删除（start 缺匹配 end）
x = 1
```

新建 `tests/golden/python/block_mismatched_end.expected.py`（end 缺 start → 忽略该 end，保留）：

```python
x = 1
# 这行不会被删除（end 缺匹配 start）
# @internal-end
```

新建 `tests/golden/python/block_nested.expected.py`（外层块 [1,4] 整行删除；行5"外层仍在块内"被删；行6第二个 end 错配保留；行7保留）：

```python
# @internal-end
x = 1
```

- [ ] **Step 3: 运行黄金测试验证失败**

Run: `cd d:\WorkPlace\Pycharm\markstrip; python -m pytest tests/unit/test_python_plugin.py -v`
Expected: FAIL —— 5 个新 block_* 用例失败（块功能未接入，定界行与块内行均未被删除）。

- [ ] **Step 4: 实现 tokenize 主路径接入块扫描**

修改 `markstrip/languages/python_plugin.py` 的 `strip_selective`。在文件顶部 import 区新增：

```python
from markstrip.core.block_scanner import scan_blocks
```

把 `strip_selective` 全文替换为：

```python
    def strip_selective(self, content: str, config: StripConfig) -> str:
        """标记式选择性过滤：仅删除含标记的注释。

        支持逐行 @internal、块定界 @internal-start/-end、docstring 整体标记。
        纯注释标记行整行移除，内联标记注释仅删注释片段保留代码。

        Args:
            content: Python 源代码内容。
            config: 清理配置。

        Returns:
            清理后的内容。
        """
        lines = content.splitlines(keepends=True)
        comment_removals: list[tuple[int, int, int]] = []

        # tokenize 识别注释
        try:
            tokens = list(tokenize.tokenize(
                iter(content.encode("utf-8").splitlines(True)).__next__
            ))
        except tokenize.TokenError:
            return self._fallback_regex_selective(content, config)

        # 块扫描
        scan = scan_blocks(
            lines,
            "#",
            config.effective_block_start(),
            config.effective_block_end(),
        )
        config.warnings.extend(scan.warnings)
        block_ranges = scan.ranges

        def _in_block(line_num: int) -> bool:
            return any(
                r.start_line <= line_num <= r.end_line for r in block_ranges
            )

        for tok in tokens:
            if tok.type == tokenize.COMMENT:
                in_block = _in_block(tok.start[0])
                if in_block:
                    # 块内：纯注释整行移除，内联仅删片段
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

            if tok.type == tokenize.STRING:
                if self._is_docstring(tok, tokens):
                    doc_removals = self._process_docstring(tok, config, lines)
                    comment_removals.extend(doc_removals)

        # 行级重组
        return self._rebuild(lines, comment_removals)
```

注意：块定界行本身也是 COMMENT token，`in_block` 为 True 且 `_is_whole_line_comment` 为 True → 整行移除。块内非定界的纯注释行同理整行移除。块内代码行的内联注释 → `in_block` True 且非纯注释行 → 仅删片段。

- [ ] **Step 5: 实现正则回退路径接入块扫描**

> **对 spec 的修正说明**：spec 原文称"逐行 @internal 部分无需改动"，但现有 `full_pattern = ^\s*#\s*{marker}.*$\n?` 会把 `# @internal-start` 当作 `@internal` + `-start` 后缀整行删除，导致**错配定界行**（缺 `end` 的 `start`）被误删而非保留+警告。本实现给 marker 正则加 `(?:\s|$)` 边界（与定界正则同一原则），让 `@internal-start`/`@internalized` 不再匹配 `@internal`，既修正定界行误删，也统一了伪前缀防护。

把 `_fallback_regex_selective` 全文替换为：

```python
    def _fallback_regex_selective(
        self, content: str, config: StripConfig
    ) -> str:
        """tokenize 失败时的正则回退。

        注意：正则无法区分字符串中的 # 和注释 #，此为已知限制。
        仅在 tokenize 失败（语法错误）时触发。

        逐行 @internal 与块内删除语义一致：纯注释行整行移除（不留空行），
        内联注释仅删片段保留代码。marker 正则要求标记后为空白/行尾，
        自动排除块定界行与 @internalized 等伪前缀。

        Args:
            content: 源代码内容。
            config: 清理配置。

        Returns:
            清理后的内容。
        """
        lines = content.splitlines(keepends=True)
        scan = scan_blocks(
            lines,
            "#",
            config.effective_block_start(),
            config.effective_block_end(),
        )
        config.warnings.extend(scan.warnings)

        markers = [config.line_marker] + config.custom_markers
        marker_alt = "|".join(re.escape(m) for m in markers)
        # marker 后须空白或行尾：排除定界行与伪前缀
        full_re = re.compile(rf"^\s*#\s*(?:{marker_alt})(?:\s|$).*")
        inline_re = re.compile(rf"\s*#\s*(?:{marker_alt})(?:\s|$).*$")
        any_comment_re = re.compile(r"^\s*#")
        inline_any_re = re.compile(r"\s*#.*$")

        def _newline(line: str) -> str:
            for nl in ("\r\n", "\n", "\r"):
                if line.endswith(nl):
                    return nl
            return ""

        out: list[str] = []
        block_iter = iter(scan.ranges)
        cur = next(block_iter, None)

        def _in_block_range(line_num: int) -> bool:
            nonlocal cur
            while cur is not None and line_num > cur.end_line:
                cur = next(block_iter, None)
            return cur is not None and cur.start_line <= line_num <= cur.end_line

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
            else:
                # 块外：逐行 @internal（marker 边界已排除定界行）
                if full_re.match(body):
                    continue
                cleaned = inline_re.sub("", body)
                if cleaned.strip() == "":
                    continue
                out.append(cleaned.rstrip() + nl)

        return "".join(out)
```

- [ ] **Step 6: 追加自定义 line_marker 联动单测**

黄金框架用默认 `StripConfig()`，无法测试 `line_marker=@private` 的块标记联动。在 `tests/unit/test_python_plugin.py` 末尾追加独立单测：

```python
def test_block_with_custom_line_marker_derives_block_markers(plugin):
    """line_marker=@private 时块标记应自动派生为 @private-start/-end。"""
    config = StripConfig(line_marker="@private")
    content = (
        "# @private-start\n"
        "# inside\n"
        "# @private-end\n"
        "x = 1\n"
    )
    result = plugin.strip_selective(content, config)
    assert result == "x = 1\n"
    assert "@private" not in result
```

- [ ] **Step 7: 移除 Task 3 的 xfail（块 warnings 现应传播）**

打开 `tests/unit/test_engine.py`，把 `test_strip_warnings_propagated_from_plugin` 的 xfail 分支移除，改为直接断言：

```python
def test_strip_warnings_propagated_from_plugin():
    """插件回填的 warnings 应出现在 StripResult.warnings。"""
    content = "# @internal-start\n# inside\nx = 1\n"
    result = strip(content, language="python", mode="selective")
    assert any("@internal-end" in w for w in result.warnings)
```

- [ ] **Step 8: 运行全部测试验证通过**

Run: `cd d:\WorkPlace\Pycharm\markstrip; python -m pytest tests/ -v`
Expected: PASS —— 5 个新 block_* 黄金用例、自定义 marker 单测、engine warnings 传播测试、现有用例全绿。错配用例的 warnings 通过 `result.warnings` 传播（黄金用例只比对内容，warnings 由 engine 测试覆盖）。

- [ ] **Step 9: 提交**

```bash
cd d:\WorkPlace\Pycharm\markstrip
git add markstrip/languages/python_plugin.py tests/golden/python/block_comment.py tests/golden/python/block_comment.expected.py tests/golden/python/block_with_code.py tests/golden/python/block_with_code.expected.py tests/golden/python/block_mismatched_start.py tests/golden/python/block_mismatched_start.expected.py tests/golden/python/block_mismatched_end.py tests/golden/python/block_mismatched_end.expected.py tests/golden/python/block_nested.py tests/golden/python/block_nested.expected.py tests/unit/test_python_plugin.py tests/unit/test_engine.py
git commit -m "feat(python): 接入块定界扫描并新增块黄金用例"
```

---

## Task 6: Markdown 兜底接入块扫描

**Files:**
- Modify: `markstrip/languages/markdown_plugin.py`
- Test: `tests/golden/markdown/block_in_yaml.md` + `.expected.md`（新建）

**Interfaces:**
- Consumes: `scan_blocks`（Task 2）、`StripConfig.effective_block_start/end`（Task 1）
- Produces: `_fallback_strip` 支持块定界（按语言注释前缀）；新增 `FALLBACK_COMMENT_PREFIX` 映射

- [ ] **Step 1: 写新增黄金用例**

新建 `tests/golden/markdown/block_in_yaml.md`：

````markdown
# 文档

```yaml
# @internal-start
key: value
# @internal-end
another: value
```
````

- [ ] **Step 2: 写新增黄金用例 expected**

新建 `tests/golden/markdown/block_in_yaml.expected.md`（块内两定界行整行删除，yaml 数据行保留）：

````markdown
# 文档

```yaml
key: value
another: value
```
````

- [ ] **Step 3: 运行测试验证失败**

Run: `cd d:\WorkPlace\Pycharm\markstrip; python -m pytest tests/unit/test_markdown_plugin.py -v`
Expected: FAIL —— `block_in_yaml` 用例失败（兜底未接入块，定界行未删除）。

- [ ] **Step 4: 实现（修改 `markstrip/languages/markdown_plugin.py`）**

在文件顶部 import 区新增：

```python
from markstrip.core.block_scanner import scan_blocks
```

在模块级常量区（`HTML_COMMENT_RE` 之后）新增：

```python
# 兜底语言的注释前缀映射（与 _fallback_strip 的 templates 语言集合对齐）
FALLBACK_COMMENT_PREFIX = {
    "yaml": "#",
    "bash": "#",
    "shell": "#",
    "javascript": "//",
    "java": "//",
    "c": "//",
    "cpp": "//",
}
```

把 `_fallback_strip` 全文替换为：

```python
    def _fallback_strip(
        self,
        code: str,
        lang: str,
        config: StripConfig,
    ) -> str:
        """无对应插件时的正则兜底。

        支持逐行 @internal 与块定界。纯注释标记行整行移除，内联注释
        仅删片段保留代码。

        Args:
            code: 代码内容。
            lang: 语言标识符。
            config: 清理配置。

        Returns:
            清理后的内容。
        """
        prefix = FALLBACK_COMMENT_PREFIX.get(lang)
        if prefix is None:
            return code

        lines = code.splitlines(keepends=True)
        scan = scan_blocks(
            lines,
            prefix,
            config.effective_block_start(),
            config.effective_block_end(),
        )
        config.warnings.extend(scan.warnings)

        markers = [config.line_marker] + config.custom_markers
        marker_alt = "|".join(re.escape(m) for m in markers)
        full_re = re.compile(
            rf"^\s*{re.escape(prefix)}\s*(?:{marker_alt})(?:\s|$).*"
        )
        inline_re = re.compile(
            rf"\s*{re.escape(prefix)}\s*(?:{marker_alt})(?:\s|$).*$"
        )
        any_comment_re = re.compile(rf"^\s*{re.escape(prefix)}")
        inline_any_re = re.compile(rf"\s*{re.escape(prefix)}.*$")

        def _newline(line: str) -> str:
            for nl in ("\r\n", "\n", "\r"):
                if line.endswith(nl):
                    return nl
            return ""

        out: list[str] = []
        block_iter = iter(scan.ranges)
        cur = next(block_iter, None)

        def _in_block_range(line_num: int) -> bool:
            nonlocal cur
            while cur is not None and line_num > cur.end_line:
                cur = next(block_iter, None)
            return cur is not None and cur.start_line <= line_num <= cur.end_line

        for i, line in enumerate(lines, 1):
            nl = _newline(line)
            body = line[:-len(nl)] if nl else line
            if _in_block_range(i):
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

        return "".join(out)
```

- [ ] **Step 5: 运行测试验证通过**

Run: `cd d:\WorkPlace\Pycharm\markstrip; python -m pytest tests/unit/test_markdown_plugin.py -v`
Expected: PASS —— `block_in_yaml` 与现有 `unknown_lang` / `code_block_delegation` / `html_comment` / `nested_codeblock` 全绿。

- [ ] **Step 6: 检查全量回归**

Run: `cd d:\WorkPlace\Pycharm\markstrip; python -m pytest tests/ -v`
Expected: PASS —— 全绿。

- [ ] **Step 7: 提交**

```bash
cd d:\WorkPlace\Pycharm\markstrip
git add markstrip/languages/markdown_plugin.py tests/golden/markdown/block_in_yaml.md tests/golden/markdown/block_in_yaml.expected.md
git commit -m "feat(markdown): 兜底正则接入块定界扫描并新增 yaml 块用例"
```

---

## Task 7: CLI 改造

**Files:**
- Modify: `markstrip/cli.py`
- Test: `tests/integration/test_cli.py`

**Interfaces:**
- Consumes: `StripConfig.block_start_marker` / `block_end_marker` / `warnings`（Task 1）、`StripResult.warnings`（Task 3）
- Produces: `--docstring-marker` 默认改空走派生；新增 `--block-start-marker` / `--block-end-marker` 可选参数；`--verbose` 打印 warnings

- [ ] **Step 1: 写失败测试（追加到 `tests/integration/test_cli.py`）**

```python
def test_cli_block_markers(tmp_path):
    """默认块标记 @internal-start/-end 应被识别。"""
    test_file = tmp_path / "test.py"
    test_file.write_text(
        "# @internal-start\n"
        "# inside\n"
        "# @internal-end\n"
        "x = 1\n",
        encoding="utf-8",
    )
    code, out, err = run_cli(str(test_file), "--dry-run")
    assert code == 0
    assert "@internal" not in out
    assert "x = 1" in out


def test_cli_custom_block_markers(tmp_path):
    """显式覆盖块标记。"""
    test_file = tmp_path / "test.py"
    test_file.write_text(
        "# @secret-begin\n"
        "# inside\n"
        "# @secret-end\n"
        "x = 1\n",
        encoding="utf-8",
    )
    code, out, err = run_cli(
        str(test_file), "--dry-run",
        "--block-start-marker", "@secret-begin",
        "--block-end-marker", "@secret-end",
    )
    assert code == 0
    assert "@secret" not in out
    assert "x = 1" in out


def test_cli_verbose_warnings(tmp_path):
    """错配块定界应通过 --verbose 打印 warning。"""
    test_file = tmp_path / "test.py"
    test_file.write_text(
        "# @internal-start\n"
        "x = 1\n",
        encoding="utf-8",
    )
    code, out, err = run_cli(str(test_file), "--dry-run", "--verbose")
    assert code == 0
    assert "Warning:" in err
    assert "@internal-end" in err
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd d:\WorkPlace\Pycharm\markstrip; python -m pytest tests/integration/test_cli.py -v`
Expected: FAIL —— `test_cli_block_markers` 失败（CLI 默认 `docstring_marker=@internal-docstring` 但块标记参数不存在，块内容未删除）；`test_cli_custom_block_markers` 失败（`--block-start-marker` 参数未定义）；`test_cli_verbose_warnings` 失败（`--verbose` 未打印 warnings）。

- [ ] **Step 3: 实现（修改 `markstrip/cli.py`）**

3a. 修改 `--docstring-marker` 默认值并新增两个块参数。把现有：

```python
    parser.add_argument(
        "--docstring-marker",
        default="@internal-docstring",
        help="整体 docstring 标记符号",
    )
```

改为：

```python
    parser.add_argument(
        "--docstring-marker",
        default="",
        help="整体 docstring 标记（默认自动派生为 {marker}-docstring）",
    )
    parser.add_argument(
        "--block-start-marker",
        default="",
        help="块起始标记（默认自动派生为 {marker}-start）",
    )
    parser.add_argument(
        "--block-end-marker",
        default="",
        help="块结束标记（默认自动派生为 {marker}-end）",
    )
```

3b. 修改 `config = StripConfig(...)` 构造，把现有：

```python
    config = StripConfig(
        line_marker=args.marker,
        docstring_marker=args.docstring_marker,
        preserve_docstrings=args.preserve_docstrings,
    )
```

改为：

```python
    config = StripConfig(
        line_marker=args.marker,
        docstring_marker=args.docstring_marker,
        block_start_marker=args.block_start_marker,
        block_end_marker=args.block_end_marker,
        preserve_docstrings=args.preserve_docstrings,
    )
```

3c. 修改 `_process_single_file` 的 verbose 输出，把现有：

```python
    if args.verbose:
        print(
            f"Processing {path}... removed {result.removed_count} lines",
            file=sys.stderr,
        )
```

改为：

```python
    if args.verbose:
        print(
            f"Processing {path}... removed {result.removed_count} lines",
            file=sys.stderr,
        )
        for w in result.warnings:
            print(f"Warning: {w}", file=sys.stderr)
```

3d. 同理修改 `_process_directory` 的 verbose 输出（在单文件 verbose 块之后追加 warnings 打印）。把现有：

```python
        if args.verbose:
            print(
                f"Processing {file_path}... "
                f"removed {result.removed_count} lines",
                file=sys.stderr,
            )
```

改为：

```python
        if args.verbose:
            print(
                f"Processing {file_path}... "
                f"removed {result.removed_count} lines",
                file=sys.stderr,
            )
            for w in result.warnings:
                print(f"Warning: {w}", file=sys.stderr)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd d:\WorkPlace\Pycharm\markstrip; python -m pytest tests/integration/test_cli.py -v`
Expected: PASS —— 3 个新测试 + 现有 CLI 测试全绿。

- [ ] **Step 5: 检查全量回归**

Run: `cd d:\WorkPlace\Pycharm\markstrip; python -m pytest tests/ -v`
Expected: PASS —— 全绿。

- [ ] **Step 6: 提交**

```bash
cd d:\WorkPlace\Pycharm\markstrip
git add markstrip/cli.py tests/integration/test_cli.py
git commit -m "feat(cli): 新增块标记参数并支持 verbose 打印 warnings"
```

---

## Self-Review

**1. Spec coverage（逐条对照 spec "实现要点摘要"）：**
- `config.py`：3 派生字段 + `effective_*()` + `warnings` 字段 → **Task 1** ✓
- `core/block_scanner.py`：新建纯函数扫描器 + `BlockRange` / `BlockScanResult` → **Task 2** ✓
- `python_plugin.py`：`strip_selective` 接入块扫描、`_is_whole_line_comment`、`_has_marker` 排除定界、逐行 `@internal` 与 docstring 内 `@internal` 改整行移除、`_process_docstring` 改用 `effective_docstring_marker`；`_fallback_regex_selective` 接入块 → **Task 4**（统一语义 + 排除定界 + `_is_whole_line_comment` + `_process_docstring`）+ **Task 5**（块扫描接入 tokenize 与正则回退）✓
- `markdown_plugin.py`：`_fallback_strip` 接入块（按语言前缀）+ `FALLBACK_COMMENT_PREFIX` → **Task 6** ✓
- `engine.py`：`strip()` 中 `config.warnings.clear()` 前置 + 回填并入 `StripResult` → **Task 3** ✓
- `cli.py`：`--docstring-marker` 默认改空、新增两可选参数、verbose 打印 warnings → **Task 7** ✓
- 测试：BlockScanner 单测 + 7 组新增黄金用例 + 4 组现有 `.expected` 更新 + 回归 → **Task 2/4/5/6/7** ✓

  > 关于 spec 列的 `python/block_custom_marker.py` 黄金用例：黄金框架用默认 `StripConfig()` 无法测试 `line_marker=@private` 联动，故改为 `tests/unit/test_python_plugin.py` 的独立单测（Task 5 Step 6），覆盖等价。`markdown/block_in_yaml.md` 在 Task 6。

**2. Placeholder scan：** 无 TBD/TODO/"implement later"；每个代码步骤均含完整可运行代码；无"类似 Task N"引用；每个测试步骤含完整断言。✓

**3. Type consistency：**
- `scan_blocks(lines, comment_prefix, start_marker, end_marker) -> BlockScanResult` —— Task 2 定义，Task 4/5/6 调用签名一致 ✓
- `BlockRange.start_line` / `end_line`（int）—— Task 2 定义，Task 5 `_in_block` 用 `r.start_line`/`r.end_line`，Task 6 `_in_block_range` 同 ✓
- `BlockScanResult.ranges` / `.warnings` —— Task 2 定义，Task 5/6 用 `scan.ranges`/`scan.warnings` ✓
- `StripConfig.effective_block_start()` / `effective_block_end()` / `effective_docstring_marker()` —— Task 1 定义，Task 4/5/6 调用一致 ✓
- `StripConfig.warnings` —— Task 1 定义，Task 3 `clear()`、Task 4/5/6 `extend()`、Task 3 `list()` 复制 ✓
- `_is_whole_line_comment(tok, lines)` —— Task 4 定义，Task 5 调用签名一致 ✓
- `_rebuild(lines, comment_removals)` 支持 `end_col=-1` —— 现有代码已支持，Task 4/5 复用不改 ✓
