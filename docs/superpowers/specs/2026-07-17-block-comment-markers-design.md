# markstrip 块注释标记设计：`@internal-start` / `@internal-end`

## 概述

为 markstrip 新增**块级定界标记**，圈定连续注释区域一次性过滤，免去为每行注释重复添加 `@internal` 的冗余。

**动机场景**：一段被注释掉的代码块（如 `temp.log` 中 17 行 Celery 日志配置的注释块），当前必须逐行加 `# @internal` 才能过滤；块标记允许用起止定界符圈定整段，一次过滤。

## 目标

1. 引入 `@internal-start` / `@internal-end` 块定界标记
2. 块内语义等价于逐行 `@internal`，但纯注释行**整行移除不留空行**（比逐行 `@internal` 的"清空成空行"更干净）
3. 标记命名随 `line_marker` 自动联动
4. 将 `docstring_marker` 也改为"空 → 从 `line_marker` 派生"模式，使三个派生标记风格统一
5. 向后兼容：现有逐行 `@internal` 行为与所有现有黄金测试不变

## 非目标（YAGNI）

- 不在 docstring 内支持块标记（docstring 已有 `@internal-docstring` 整体删除机制，语义重叠）
- 不在 HTML 注释、Markdown prose 中支持块标记
- 不支持块嵌套（内层 `start` 视为错配，严格忽略 + 警告）
- 不在 `full` 模式启用块标记（该模式本就删除所有注释，块标记无意义）

## 标记语法总表（更新）

| 标记类型 | 语法 | 作用范围 | 备注 |
|---------|------|---------|------|
| 行级标记 | `# @internal` | 单行 | 行为不变：纯注释行清空成空行；内联注释仅删注释片段 |
| 块起始 | `# @internal-start` | 圈定块起始 | 随 `line_marker` 派生 |
| 块结束 | `# @internal-end` | 圈定块结束 | 随 `line_marker` 派生 |
| docstring 整体 | `@internal-docstring`（docstring 内） | 整个 docstring | 随 `line_marker` 派生 |

**定界行匹配规则**：`^\s*{comment_prefix}\s*{marker}(?:\s|$)` —— 标记后须紧跟空白或行尾，避免 `@internal-started`、`@internalized` 等误匹配。定界行允许有前导空白（缩进）与标记后的任意说明文字。

## 删除语义

块区域 = `[start_line, end_line]` 闭区间（含两定界行）。块内每个注释按如下处理：

| 行类型 | 处理 |
|---|---|
| 纯注释行（行首到注释起点之间全为空白，含缩进注释） | **整行移除**（含换行符，不留空行）→ `end_col = -1` |
| 代码行 + 行尾内联注释 | 仅删注释文本，保留代码（rstrip 行尾空白）→ 部分删除 |
| 纯代码行（无注释） | 原样保留 |
| 空行 | 原样保留 |

两定界行本身是纯注释行 → 整行移除。

**与逐行 `@internal` 的差异**：逐行 `@internal` 的纯注释行清空成空行（保留换行、行数不变）；块标记的纯注释行整行移除（行数减少）。这是块标记的有意设计——过滤大段注释时不留空行残迹。

## 配置变更（`markstrip/core/config.py`）

新增 `block_start_marker` / `block_end_marker` 两字段；将 `docstring_marker` 默认值改为空串以统一派生模式；新增 `warnings` 瞬态回填字段。

```python
@dataclass
class StripConfig:
    line_marker: str = "@internal"
    docstring_marker: str = ""        # 空 → f"{line_marker}-docstring"
    block_start_marker: str = ""     # 空 → f"{line_marker}-start"
    block_end_marker: str = ""       # 空 → f"{line_marker}-end"
    preserve_docstrings: bool = True
    preserve_todo: bool = True
    custom_markers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def effective_docstring_marker(self) -> str:
        return self.docstring_marker or f"{self.line_marker}-docstring"

    def effective_block_start(self) -> str:
        return self.block_start_marker or f"{self.line_marker}-start"

    def effective_block_end(self) -> str:
        return self.block_end_marker or f"{self.line_marker}-end"
```

**向后兼容性**：
- 默认场景（`line_marker=@internal`）下，三标记有效值与现状一致（`@internal-docstring` 等），行为不变。
- **有意的行为变化**：当用户改 `line_marker=@private` 时，`docstring_marker` 由"保持 `@internal-docstring`"变为自动派生为 `@private-docstring`。这是预期的联动一致性改进；现有测试均使用默认 `line_marker`，不受影响。
- 新增字段全有默认值，旧代码无需改动。

**warnings 字段语义**：由引擎每次调用插件前 `clear()`，插件在处理过程中回填（如块错配警告），引擎**复制**（`list(config.warnings)`）后并入 `StripResult.warnings`。属引擎拥有的瞬态通道，非用户配置。须复制而非引用，避免下一次调用 `clear()` 误清空上一个结果。

## 新组件 `BlockScanner`（`markstrip/core/block_scanner.py`）

块语义的唯一真理源，供 Python 插件与 Markdown 兜底正则共用，避免重复实现。

```python
@dataclass
class BlockRange:
    start_line: int  # 1-based，含定界行
    end_line: int

@dataclass
class BlockScanResult:
    ranges: list[BlockRange]
    warnings: list[str]

def scan_blocks(
    lines: list[str],
    comment_prefix: str,   # "#", "//" 等，不含空白
    start_marker: str,
    end_marker: str,
) -> BlockScanResult: ...
```

**算法**（单趟扫描，严格容错，不支持嵌套）：

```
open_start = None
ranges = []
warnings = []
for i, line in enumerate(lines, 1):
    if is_start(line):
        if open_start is not None:
            warnings.append(f"行 {i}: 嵌套 {start_marker}，已忽略")
            continue
        open_start = i
    elif is_end(line):
        if open_start is None:
            warnings.append(f"行 {i}: 无匹配 {start_marker} 的 {end_marker}，已忽略")
            continue
        ranges.append(BlockRange(open_start, i))
        open_start = None
if open_start is not None:
    warnings.append(f"行 {open_start}: {start_marker} 缺少匹配 {end_marker}，已忽略")
return BlockScanResult(ranges, warnings)
```

`is_start` / `is_end` 用前述定界行正则匹配。范围判定为 `r.start_line <= line_num <= r.end_line`。

## Python 插件集成（`markstrip/languages/python_plugin.py`）

### tokenize 主路径 `strip_selective`

1. `scan = scan_blocks(lines, "#", config.effective_block_start(), config.effective_block_end())`
2. `config.warnings.extend(scan.warnings)`
3. 遍历 token，**对 COMMENT 先判 `in_block`，再判逐行 `@internal`**：
   - `in_block` 且 `_is_whole_line_comment(tok, lines)` → `comment_removals.append((line, 0, -1))` 整行移除
   - `in_block` 但内联 → `(line, start_col, end_col)` 仅删注释片段
   - 否则 `_has_marker(tok.string, config)` → 现有逐行行为 `(line, start_col, end_col)`（清空成空行）
4. docstring 处理沿用现有逻辑，但改用 `config.effective_docstring_marker()` 判定整体标记。
5. 复用 `_rebuild` 不变。

```python
def _is_whole_line_comment(
    self, tok: tokenize.TokenInfo, lines: list[str]
) -> bool:
    """行首到注释起点之间全为空白 → 纯注释行（覆盖缩进注释）。"""
    line_text = lines[tok.start[0] - 1]
    before = line_text[: tok.start[1]]
    return before.strip() == ""
```

### `_has_marker` 排除块定界标记

`@internal-start` / `@internal-end` 以 `@internal` 为前缀，须从逐行分支排除，避免错配定界行被清空成空行（错配定界行应保留为普通注释 + 警告）：

```python
def _has_marker(self, comment_text: str, config: StripConfig) -> bool:
    markers = [config.line_marker] + config.custom_markers
    stripped = comment_text.lstrip("#").strip()
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

### 正则回退路径 `_fallback_regex_selective`

按行扫描（无 tokenize）：

1. `scan_blocks(lines, "#", ...)` 取 ranges + warnings
2. 逐行：
   - 块内行：`^\s*#\s*.*$` 命中纯注释行 → 整行丢弃（含换行）；否则用 `\s*#.*$` 删内联注释片段，保留代码
   - 块外行：沿用现有逐行 `@internal` 正则逻辑（整行/内联两遍替换）

## Markdown 兜底集成（`markstrip/languages/markdown_plugin.py`）

- 围栏代码块内块标记：由委托的语言插件处理（Python 插件自带；`_process_code_blocks` 无需改动）
- `_fallback_strip`（未知语言 `#`/`//` 系列）增加块支持：复用 `scan_blocks`，`comment_prefix` 取自新增的 `FALLBACK_COMMENT_PREFIX` 映射表（与 `FALLBACK_PATTERNS` 的语言集合对齐）：

```python
FALLBACK_COMMENT_PREFIX = {
    "yaml": "#", "bash": "#", "shell": "#",
    "javascript": "//", "java": "//", "c": "//", "cpp": "//",
}
```

块内整行注释丢弃、内联注释删片段，逻辑同 Python 正则回退
- HTML 注释、Markdown prose 不支持块标记

## CLI 变更（`markstrip/cli.py`）

- `--docstring-marker` 默认值由 `"@internal-docstring"` 改为 `""`，走自动派生
- 新增两个**可选**覆盖参数，与 `--docstring-marker` 对称：

```python
parser.add_argument(
    "--block-start-marker", default="",
    help="块起始标记（默认自动派生为 {marker}-start）",
)
parser.add_argument(
    "--block-end-marker", default="",
    help="块结束标记（默认自动派生为 {marker}-end）",
)
```

```python
config = StripConfig(
    line_marker=args.marker,
    docstring_marker=args.docstring_marker,
    block_start_marker=args.block_start_marker,
    block_end_marker=args.block_end_marker,
    preserve_docstrings=args.preserve_docstrings,
)
```

- `--verbose` 模式额外打印 `result.warnings`（每条警告一行，前缀 `Warning:`）

典型用法：

```bash
# 默认块标记
markstrip app.py
# 自定义行级标记会自动联动块标记
markstrip app.py --marker @private   # → @private-start / @private-end / @private-docstring
# 显式覆盖块标记
markstrip app.py --block-start-marker @secret-begin --block-end-marker @secret-end
```

## 错误处理与边界

| 场景 | 行为 |
|---|---|
| `start` 后无 `end` | 忽略该 `start`，定界行作普通注释保留 + warning |
| `end` 前无 `start` | 忽略该 `end`，保留 + warning |
| 未闭合 `start` 期间再遇 `start` | 忽略内层 `start` + warning |
| 块内含 `# @internal` 逐行标记 | 走块分支（纯注释行整行移除），不重复处理 |
| 块定界行出现在 docstring 内 | 不触发块逻辑（docstring 走自身机制） |
| `full` 模式 | 块标记无意义，全量删除照常 |
| warnings 传播 | 引擎每次调用前 `config.warnings.clear()`，插件回填，引擎并入 `StripResult.warnings` |
| `@internal-started` 等伪前缀 | 定界正则要求标记后为空白/行尾，不误匹配 |
| 同行代码 + 块定界 | 不允许；定界行须为纯注释行（实际中定界正则已要求行首为注释） |

## 测试策略

### BlockScanner 单元测试（`tests/unit/test_block_scanner.py`）

| 用例 | 期望 |
|---|---|
| 单一配对块 | 1 个 range，无 warning |
| 多个配对块 | 多 range，无 warning |
| `start` 缺 `end` | 0 range，1 warning |
| `end` 缺 `start` | 0 range，1 warning |
| 嵌套 `start` | 外层 1 range，内层忽略 + 1 warning |
| 自定义前缀 `//` | 正确识别 |
| 标记后接非空白后缀（`@internal-started`） | 不误匹配 |
| 缩进定界行（`    # @internal-start`） | 正确识别 |

### 新增黄金用例（`tests/golden/`）

- `python/block_comment.py` + `.expected.py` — 纯注释块整行移除（对照 `temp.log` 场景，17 行块消失不留空行）
- `python/block_with_code.py` + `.expected.py` — 块内代码行保留、仅剥内联注释
- `python/block_mismatched_start.py` + `.expected.py` — 缺 `end`，定界行保留 + warning
- `python/block_mismatched_end.py` + `.expected.py` — 缺 `start`，保留 + warning
- `python/block_nested.py` + `.expected.py` — 内层忽略 + warning
- `python/block_custom_marker.py` + `.expected.py` — `line_marker=@private` 联动
- `markdown/block_in_yaml.md` + `.expected.md` — 兜底语言块标记

### 回归

现有 `internal_comment`、`docstring_selective`、`docstring_whole`、`string_with_hash`、`syntax_error` 等用例不变，验证逐行 `@internal` 与 docstring 行为未被破坏。

## 数据流

```
strip(content, language="python", mode="selective")
  → StripEngine.strip
    → config.warnings.clear()
    → PythonPlugin.strip_selective(content, config)
      → scan_blocks(lines, "#", ...) → ranges + warnings
      → config.warnings.extend(warnings)
      → tokenize COMMENT token 遍历：in_block 优先，否则 _has_marker
      → _rebuild(lines, comment_removals)
    → StripResult(cleaned_content, removed_count, warnings=list(config.warnings))
```

## 实现要点摘要

1. `config.py`：3 派生字段 + `effective_*()` + `warnings` 字段
2. `core/block_scanner.py`：新建，纯函数扫描器 + `BlockRange` / `BlockScanResult`
3. `python_plugin.py`：`strip_selective` 接入块扫描、`_is_whole_line_comment`、`_has_marker` 排除定界、`_process_docstring` 改用 `effective_docstring_marker`、`_fallback_regex_selective` 接入块
4. `markdown_plugin.py`：`_fallback_strip` 接入块（按语言前缀）
5. `engine.py`：`strip()` 中 `config.warnings.clear()` 前置 + 回填并入 `StripResult`
6. `cli.py`：`--docstring-marker` 默认改空、新增两可选参数、verbose 打印 warnings
7. 测试：BlockScanner 单测 + 7 组黄金用例 + 现有用例回归
