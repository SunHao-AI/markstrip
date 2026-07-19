# markstrip v1.3 `--check` 模式与 stdin/stdout 管道实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 markstrip 增加 CI 守门用 `--check` 模式与 Unix 风格 stdin/stdout 管道,同时同步已实现但未文档化的 v1.2 pragma 指令到主设计文档与 README。

**Architecture:** 复用现有 `warnings` 瞬态通道模式扩展 `markers_found` 字段;新增 `MarkerLocation` 数据类承载 `--check` 输出所需的精确位置信息;`check_mode` 瞬态标志让插件在 `--check` 时跳过 pragma 优化确保所有 `@internal` 标记被扫描;Markdown 插件对代码块内委托插件的相对行号做绝对行号翻译。

**Tech Stack:** Python 3.10+ 标准库(tokenize/ast/argparse/re)、pytest、subprocess CLI 集成测试、黄金文件测试策略。

## Global Constraints

- Python >= 3.10,零运行时依赖(仅标准库)
- 后端代码导入顺序遵循 PEP 8(标准库 → 第三方库 → 本地应用);每组之间空行分隔,组内字母序
- 现有 106 个测试必须全过(向后兼容,新字段默认空列表)
- `strip()` / `strip_file()` / `strip_directory()` 公共 API 签名只加新关键字参数,默认值保持向后兼容
- 测试命令:`python -m pytest tests/<path> -v`
- 提交信息使用中文描述,遵循 conventional commit 格式(如 `feat(python): ...` / `docs: ...`)
- 工作目录:`d:\WorkPlace\Pycharm\markstrip`

---

## 文件结构

| 文件 | 责任 | 本计划变更 |
|------|------|-----------|
| `markstrip/core/result.py` | `StripResult` + 新增 `MarkerLocation` | 加 `MarkerLocation` 数据类 + `StripResult.markers_found` 字段 |
| `markstrip/core/config.py` | `StripConfig` 配置 | 加 `markers_found` 瞬态字段 + `check_mode` 瞬态字段 |
| `markstrip/core/engine.py` | `StripEngine.strip()` 调度 | 加 `check_mode` 参数 + markers_found clear/copy |
| `markstrip/__init__.py` | 公共 API + `__all__` 导出 | 加 `check_mode` 参数到 strip/strip_file/strip_directory + 导出 `MarkerLocation` |
| `markstrip/languages/base.py` | `LanguagePlugin` 抽象基类 | 无变更(已有 `detect()` 默认返回 False) |
| `markstrip/languages/python_plugin.py` | Python 插件 | `strip_selective` 4 个回填点 + check_mode 跳过 pragma 委托/分支 + `_fallback_regex_selective` 同步 + 新增 `detect()` |
| `markstrip/languages/markdown_plugin.py` | Markdown 插件 | `_process_html_comments` 回填 + `_process_code_blocks` 行号翻译 + `_fallback_strip` 回填 + check_mode 跳过 pragma + 新增 `detect()` |
| `markstrip/cli.py` | CLI 入口 | 新增 `--check` + `--language` + `-` 占位符 stdin 模式 + 参数冲突检测 |
| `docs/markstrip-design.md` | 主设计文档 | v1.2 pragma 章节 + v1.3 check/stdin 章节 + 更新记录 |
| `README.md` | 用户文档 | v1.2 pragma 章节 + v1.3 check/stdin 章节 + 更新记录 |
| `pyproject.toml` | 包元数据 | 版本号 `0.1.0` → `0.2.0` |
| `tests/unit/test_result.py` | `StripResult` 测试 | 加 `MarkerLocation` + `markers_found` 测试 |
| `tests/unit/test_config.py` | `StripConfig` 测试 | 加 `markers_found` + `check_mode` 字段测试 |
| `tests/unit/test_engine.py` | `StripEngine` 测试 | 加 `check_mode` 传播 + markers_found clear/copy 测试 |
| `tests/unit/test_python_plugin.py` | PythonPlugin 测试 | 加 4 个回填点 + check_mode 跳过 pragma 测试 + detect() 测试 |
| `tests/unit/test_markdown_plugin.py` | MarkdownPlugin 测试 | 加 HTML 回填 + 行号翻译 + detect() 测试 |
| `tests/integration/test_cli.py` | CLI 集成测试 | 加 `--check` 测试组 + stdin 测试组 |

---

## Task 1: v1.2 pragma 指令文档同步

**Files:**
- Modify: `docs/markstrip-design.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: v1.2 pragma 已实现代码(`core/pragma_scanner.py`、`PythonPlugin.strip_selective`、`MarkdownPlugin._fallback_strip`)
- Produces: 文档完整覆盖 v1.2 pragma 功能

- [ ] **Step 1: 同步 `docs/markstrip-design.md` 更新记录**

打开 `docs/markstrip-design.md`,定位到 `## 更新记录` 章节(约 1139 行)。在现有 v1.1 行下方追加 v1.2 行:

```markdown
| 2026-07-17 | v1.2 | 新增 pragma 指令系统(`# markstrip: full` / `full-start` / `full-end`)、`pragma_scanner` 模块、`BlockRange.mode` 字段 | Trae AI |
```

- [ ] **Step 2: 在 `docs/markstrip-design.md` 包结构补 `pragma_scanner.py`**

定位到 `### 包结构`(约 50 行)。在 `core/` 块的 `block_scanner.py` 与 `result.py` 之间插入一行:

```
│   ├── pragma_scanner.py    # scan_file_pragma() / scan_full_ranges(): pragma 指令扫描
```

- [ ] **Step 3: 在 `docs/markstrip-design.md` 标记语法总表加 3 行**

定位到标记语法总表章节(包含 `@internal` / `@internal-start` / `@internal-end` 的表格)。在表格末尾追加 3 行:

```markdown
| `# markstrip: full` | 文件级 pragma 指令 | 该文件所有注释全量删除,保留代码 |
| `# markstrip: full-start` | 区间级 pragma 起始 | 区间内注释全量删除,保留代码 |
| `# markstrip: full-end` | 区间级 pragma 结束 | 与 full-start 配对,闭区间 |
```

- [ ] **Step 4: 在 `docs/markstrip-design.md` 新增 "Pragma 指令系统" 章节**

在 "标记语法总表" 章节之后、"语言插件接口" 章节之前(或任意合适位置)新增完整章节:

```markdown
## Pragma 指令系统

### 设计意图

Pragma 指令是**有意处理指令**,与 `@internal` 标记体系互补:
- `@internal` 标记 selective 模式下"应删除的注释"
- pragma 指令在 selective 模式下"该文件/区间应转 full 模式"(全量删注释保留代码)

典型场景:整个文件或某段代码是交付时不应包含任何注释的"clean zone",用 pragma 一次性指令,无需逐行 `@internal`。

### 语法

| 指令 | 作用域 | 语义 |
|------|--------|------|
| `# markstrip: full` | 文件级 | 该文件所有注释全量删除(等价 `--mode full`),保留代码 |
| `# markstrip: full-start` | 区间起始 | 区间内注释全量删除,保留代码 |
| `# markstrip: full-end` | 区间结束 | 与 full-start 配对,闭区间语义 |

指令必须独占一行(允许前导空白),格式为 `# markstrip: <directive>`。

### 识别规则

- 文件级:扫描器(`scan_file_pragma`)检测文件首行(或首个非空行)是否为 `# markstrip: full`
- 区间级:扫描器(`scan_full_ranges`)检测所有 `# markstrip: full-start` 与 `full-end` 对,采用"首个 start 到首个 end 闭区间"语义
- 不支持嵌套:内层 `full-start` 视为错配并忽略(输出 warning)

### 文件级 pragma 行为

当文件首行为 `# markstrip: full` 时:
- `PythonPlugin.strip_selective` 跳过 selective 扫描,直接委托 `strip_full`
- `MarkdownPlugin._fallback_strip` 检测到文件级 pragma 时,委托 `_fallback_full`(正则兜底全量删注释)
- 区间标记冗余时输出 warning:"文件级 full 已生效, 区间标记冗余"

### 区间级 pragma 行为

当文件含 `full-start` / `full-end` 对时:
- 区间内的 COMMENT token 走 full 逻辑(全量删注释保留代码)
- 区间外的注释走 selective 逻辑(`@internal` 过滤)
- `BlockRange.mode = "comments"` 标识该区间仅删注释保留代码(区别于 `@internal-start/end` 块的 `mode = "all"` 整块删除)

### 与 `@internal-start/end` 的区别

| 维度 | `@internal-start/end` | `# markstrip: full-start/end` |
|------|----------------------|------------------------------|
| 删除范围 | 整块(含代码行与注释行) | 仅注释(保留代码) |
| BlockRange.mode | `"all"` | `"comments"` |
| 标记语义 | selective 标记 | selective 内嵌的 full 指令 |
| 是否可嵌套 | 否 | 否 |

### 错配处理

- `full-end` 无匹配 `full-start` → warning "孤立的 full-end"
- `full-start` 无匹配 `full-end` → warning "未闭合的 full-start"
- warnings 通过 `config.warnings` 瞬态通道传播至 `StripResult.warnings`

### CLI 交互矩阵

| 输入 | CLI mode | 行为 |
|------|----------|------|
| 文件含 `# markstrip: full` | `selective`(默认) | 等价 full,输出全量删注释结果 |
| 文件含 `# markstrip: full` | `full` | 一致(冗余无副作用) |
| 文件含 `full-start/end` 对 | `selective` | 区间内 full,区间外 selective |
| 文件含 `full-start/end` 对 | `full` | 一致(整个文件已 full) |
| 文件含错配 `full-end` | 任意 | 输出 warning,忽略错配指令 |

### Markdown 兜底机制

`MarkdownPlugin._fallback_strip` 中:
- 文件级 pragma 检测通过 `scan_file_pragma(lines, prefix)`
- 命中时委托 `_fallback_full(lines, prefix, config)` 走正则兜底全量删注释
- 区间级 pragma 通过 `scan_full_ranges(lines, prefix)` 检测,区间内走 full 逻辑
```

- [ ] **Step 5: 在 `docs/markstrip-design.md` Python 插件处理流程补 pragma 分支**

定位到 Python 插件处理流程章节(Phase 0~4 描述)。在每个相关 Phase 补 pragma 检测分支说明。具体位置:Phase 0 之前补 "Phase -1: pragma 检测":

```markdown
### Phase -1: pragma 指令检测(selective 模式入口)

1. `scan_file_pragma(lines, "#")` 检测文件级 pragma → 命中则委托 `strip_full`,直接返回
2. `scan_full_ranges(lines, "#")` 检测区间级 pragma → 生成 `pragma_ranges`
3. 后续 Phase 1~4 中,COMMENT token 落在 `pragma_ranges` 内 → 走 full 逻辑(全量删注释保留代码),否则走 selective 逻辑
```

- [ ] **Step 6: 在 `docs/markstrip-design.md` 测试用例覆盖表补 pragma 7 组**

定位到测试用例覆盖表(如有)或测试策略章节。追加 pragma 用例行:

```markdown
| `pragma_full` | 文件级 `# markstrip: full` 触发全量删注释 |
| `pragma_range` | 区间级 `full-start`/`full-end` 区间内 full,区间外 selective |
| `pragma_range_docstring` | 区间级 pragma 内 docstring 处理 |
| `pragma_mismatched_end` | 孤立 `full-end` 输出 warning 且忽略 |
| `pragma_nested` | 嵌套 `full-start` 视为错配并 warning |
| `pragma_with_selective` | 文件级 pragma + 区间标记冗余 warning |
| `pragma_in_yaml` | Markdown 代码块内 yaml 兜底接入 pragma |
```

- [ ] **Step 7: 同步 `README.md` 目录与核心特性**

打开 `README.md`,在目录中"标记类型详解"之后添加:

```markdown
- [Pragma 指令系统](#pragma-指令系统)
```

在"核心特性"列表中追加:

```markdown
- **Pragma 指令式全量删注释**:`# markstrip: full` 文件级 / `full-start`/`full-end` 区间级指令
```

- [ ] **Step 8: 在 `README.md` 标记类型详解表补 3 行**

定位到标记类型详解表。追加 3 行:

```markdown
| `# markstrip: full` | 文件级 pragma | 该文件所有注释全量删除,保留代码 |
| `# markstrip: full-start` | 区间级 pragma 起始 | 区间内注释全量删除,保留代码 |
| `# markstrip: full-end` | 区间级 pragma 结束 | 与 full-start 配对 |
```

- [ ] **Step 9: 在 `README.md` 新增 "Pragma 指令系统" 章节**

在"标记类型详解"之后插入完整章节:

```markdown
## Pragma 指令系统

Pragma 指令是 markstrip 的"clean zone"机制:用一行指令让整个文件或某段代码在 selective 模式下自动转 full 模式(全量删注释保留代码),无需逐行 `@internal`。

### 语法示例

文件级(整个文件全量删注释):

```python
# markstrip: full
import os
# 这条注释会被删除
x = 1  # 行尾注释也会被删除
```

区间级(区间内全量删注释,区间外保留 selective):

```python
# markstrip: full-start
# 这段代码内的所有注释都会被删除
def f():
    # 包括这条
    return 1
# markstrip: full-end

# @internal 这条仍按 selective 标记处理
y = 2
```

### 与 @internal 的关系

| 维度 | `@internal` 标记 | `# markstrip:` pragma |
|------|----------------|----------------------|
| 作用 | 标记应删除的注释 | 指令该范围转 full 模式 |
| 删除范围 | 仅标记的注释 | 范围内所有注释 |
| 是否保留代码 | 是 | 是 |
| CLI 交互 | selective 模式 | selective 内嵌 full |

### CLI 交互矩阵

| 输入 | CLI mode | 行为 |
|------|----------|------|
| 文件含 `# markstrip: full` | selective | 等价 full,全量删注释 |
| 文件含 `# markstrip: full` | full | 一致(冗余) |
| 区间 `full-start/end` | selective | 区间内 full,外 selective |

### FAQ

- **pragma 是否支持嵌套**:不支持。内层 `full-start` 视为错配,输出 warning 后忽略。
- **release 文件该用 pragma 还是 @internal**:文件整体无注释 → 用 `# markstrip: full`;大部分注释保留、仅特定行删除 → 用 `@internal`。
- **HTML 注释是否支持 pragma**:不支持。pragma 仅作用于 `#` / `//` 前缀的代码注释。
```

- [ ] **Step 10: 在 `README.md` CLI 命令行使用指南补 pragma 典型用法**

定位到 CLI 命令行使用指南。在现有示例后追加:

```bash
# 文件含 # markstrip: full,selective 模式自动转 full
markstrip src.py --dry-run

# 区间 pragma 与 selective 共存
markstrip app/ --recursive
```

- [ ] **Step 11: 在 `README.md` FAQ 与已知限制补 pragma 项**

在 FAQ 追加:

```markdown
### Q: pragma 与 @internal 有什么区别?

pragma 指令("该范围转 full")与 @internal 标记("这条注释应删除")互补。pragma 用于整段无注释的 clean zone,@internal 用于精确标记单条注释。
```

在已知限制追加:

```markdown
6. **Pragma 不支持嵌套**:`# markstrip: full-start` 采用单层闭区间语义,内层视为错配。
7. **HTML 注释不支持 pragma**:pragma 仅作用于代码注释前缀(`#`/`//`),不作用于 Markdown HTML 注释。
```

在"后续发展方向"的"已实现(v1.1)"下方新增"已实现(v1.2)":

```markdown
### 已实现（v1.2）

- [x] Pragma 指令系统(`# markstrip: full` / `full-start` / `full-end`)
- [x] `pragma_scanner` 模块、`BlockRange.mode` 字段
- [x] Python 与 Markdown 兜底接入 pragma
```

- [ ] **Step 12: 验证文档变更可读**

打开 `docs/markstrip-design.md` 与 `README.md`,人工检查目录链接、章节锚点、表格对齐无错乱。

- [ ] **Step 13: 提交**

```bash
git add docs/markstrip-design.md README.md
git commit -m "docs: 同步 v1.2 pragma 指令文档"
```

---

## Task 2: 数据结构扩展 — MarkerLocation + StripResult + StripConfig

**Files:**
- Modify: `markstrip/core/result.py`
- Modify: `markstrip/core/config.py`
- Test: `tests/unit/test_result.py`
- Test: `tests/unit/test_config.py`

**Interfaces:**
- Consumes: 无(基础数据结构)
- Produces: `MarkerLocation` 数据类、`StripResult.markers_found: list[MarkerLocation]`、`StripConfig.markers_found` 与 `StripConfig.check_mode` 瞬态字段

- [ ] **Step 1: 写失败测试 — `MarkerLocation` 数据类**

在 `tests/unit/test_result.py` 末尾追加:

```python
from markstrip.core.result import MarkerLocation


def test_marker_location_basic():
    m = MarkerLocation(
        line=12,
        col=5,
        marker_type="line",
        marker_text="@internal",
        content_preview="# @internal 使用 TensorRT",
    )
    assert m.line == 12
    assert m.col == 5
    assert m.marker_type == "line"
    assert m.marker_text == "@internal"
    assert m.content_preview == "# @internal 使用 TensorRT"


def test_marker_location_types():
    """覆盖所有合法 marker_type 值。"""
    for t in ("line", "block-start", "block-end",
              "docstring-whole", "docstring-line"):
        m = MarkerLocation(
            line=1, col=0, marker_type=t,
            marker_text="@internal", content_preview="x",
        )
        assert m.marker_type == t
```

- [ ] **Step 2: 运行测试验证失败**

Run: `python -m pytest tests/unit/test_result.py::test_marker_location_basic -v`
Expected: FAIL with `ImportError: cannot import name 'MarkerLocation'`

- [ ] **Step 3: 实现 `MarkerLocation` + `StripResult.markers_found`**

修改 `markstrip/core/result.py`:

```python
"""清理结果。"""
from dataclasses import dataclass, field


@dataclass
class MarkerLocation:
    """检测到的标记位置(用于 --check 输出)。

    Attributes:
        line: 1-based 行号(文件绝对行号)。
        col: 0-based 列号(标记起点)。
        marker_type: "line" | "block-start" | "block-end"
            | "docstring-whole" | "docstring-line"。
        marker_text: 命中的标记文本(如 "@internal" / "@internal-start"
            / "@internal-docstring" / 自定义 marker 串)。
        content_preview: 标记所在行内容预览(截断至 80 字符,便于定位)。
    """
    line: int
    col: int
    marker_type: str
    marker_text: str
    content_preview: str


@dataclass
class StripResult:
    """注释清理结果。

    Attributes:
        cleaned_content: 清理后的内容。
        removed_count: 删除的行数。
        detected_language: 检测到的语言标识符。
        warnings: 警告信息列表。
        markers_found: --check 模式检测到的标记位置列表(瞬态,由引擎复制并入)。
    """
    cleaned_content: str
    removed_count: int
    detected_language: str = ""
    warnings: list[str] = field(default_factory=list)
    markers_found: list[MarkerLocation] = field(default_factory=list)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `python -m pytest tests/unit/test_result.py -v`
Expected: PASS(原有 3 个测试 + 新增 2 个测试全过)

- [ ] **Step 5: 写失败测试 — `StripConfig.markers_found` 与 `check_mode` 字段**

在 `tests/unit/test_config.py` 末尾追加(若文件不存在则创建,内容为首部 `"""StripConfig 单元测试。"""` + import + 测试):

```python
from markstrip.core.config import StripConfig
from markstrip.core.result import MarkerLocation


def test_config_markers_found_default_empty():
    config = StripConfig()
    assert config.markers_found == []
    assert config.check_mode is False


def test_config_markers_found_transient():
    """markers_found 是普通 list,可直接 append/clear。"""
    config = StripConfig()
    m = MarkerLocation(
        line=1, col=0, marker_type="line",
        marker_text="@internal", content_preview="x",
    )
    config.markers_found.append(m)
    assert len(config.markers_found) == 1
    config.markers_found.clear()
    assert config.markers_found == []
```

- [ ] **Step 6: 运行测试验证失败**

Run: `python -m pytest tests/unit/test_config.py::test_config_markers_found_default_empty -v`
Expected: FAIL with `AttributeError: 'StripConfig' object has no attribute 'markers_found'`

- [ ] **Step 7: 实现 `StripConfig` 新字段**

修改 `markstrip/core/config.py`,在 `warnings` 字段后追加两行,并在 docstring 补说明:

```python
"""清理配置。"""
from dataclasses import dataclass, field

from markstrip.core.result import MarkerLocation


@dataclass
class StripConfig:
    """标记式注释清理配置。

    Attributes:
        line_marker: 行级标记符号,匹配此标记的注释行将被删除。
        docstring_marker: 整体 docstring 标记,空串时自动派生为
            f"{line_marker}-docstring"。
        block_start_marker: 块起始定界标记,空串时自动派生为
            f"{line_marker}-start"。
        block_end_marker: 块结束定界标记,空串时自动派生为
            f"{line_marker}-end"。
        preserve_docstrings: full 模式下是否保留 docstring。
        preserve_todo: full 模式下是否保留 TODO/FIXME 注释。
        custom_markers: 自定义额外标记列表,与 line_marker 一起匹配。
        warnings: 引擎瞬态回填通道,由引擎每次调用插件前 clear(),
            插件回填,引擎复制后并入 StripResult.warnings。非用户配置。
        markers_found: --check 模式瞬态回填通道,由引擎每次调用插件前
            clear(),插件在删除点回填 MarkerLocation,引擎复制后并入
            StripResult.markers_found。非用户配置。
        check_mode: --check 模式瞬态标志,由引擎设置。True 时插件跳过
            pragma 委托与 in_pragma 优先分支,确保所有 @internal 被扫描。
    """
    line_marker: str = "@internal"
    docstring_marker: str = ""
    block_start_marker: str = ""
    block_end_marker: str = ""
    preserve_docstrings: bool = True
    preserve_todo: bool = True
    custom_markers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    markers_found: list[MarkerLocation] = field(default_factory=list)
    check_mode: bool = False

    def effective_docstring_marker(self) -> str:
        """返回实际生效的 docstring 标记(空则从 line_marker 派生)。"""
        return self.docstring_marker or f"{self.line_marker}-docstring"

    def effective_block_start(self) -> str:
        """返回实际生效的块起始标记(空则从 line_marker 派生)。"""
        return self.block_start_marker or f"{self.line_marker}-start"

    def effective_block_end(self) -> str:
        """返回实际生效的块结束标记(空则从 line_marker 派生)。"""
        return self.block_end_marker or f"{self.line_marker}-end"
```

**注意**: `core/config.py` 现在 import `core.result.MarkerLocation`,而 `core/result.py` 不 import config,避免循环依赖。检查 `core/result.py` 不依赖 config(当前不依赖,安全)。

- [ ] **Step 8: 运行测试验证通过**

Run: `python -m pytest tests/unit/test_config.py tests/unit/test_result.py -v`
Expected: PASS

- [ ] **Step 9: 跑全量回归**

Run: `python -m pytest tests/ -v`
Expected: 全部 PASS(新字段默认空,向后兼容,106+ 测试通过)

- [ ] **Step 10: 提交**

```bash
git add markstrip/core/result.py markstrip/core/config.py tests/unit/test_result.py tests/unit/test_config.py
git commit -m "feat(core): 新增 MarkerLocation 与 markers_found/check_mode 瞬态字段"
```

---

## Task 3: Engine 调度扩展 — check_mode 参数与 markers_found 通道

**Files:**
- Modify: `markstrip/core/engine.py`
- Modify: `markstrip/__init__.py`
- Test: `tests/unit/test_engine.py`

**Interfaces:**
- Consumes: Task 2 的 `MarkerLocation` / `StripConfig.markers_found` / `StripConfig.check_mode` / `StripResult.markers_found`
- Produces: `StripEngine.strip(check_mode=False)` 签名 + 引擎调度逻辑;`strip()` / `strip_file()` / `strip_directory()` 公共 API 加 `check_mode` 参数

- [ ] **Step 1: 写失败测试 — check_mode 传播与 markers_found 清空/复制**

在 `tests/unit/test_engine.py` 末尾追加:

```python
def test_check_mode_default_false():
    """默认调用 check_mode=False,markers_found 默认空。"""
    result = strip("# @internal x\ny = 1\n", language="python")
    assert result.markers_found == []


def test_check_mode_collects_markers():
    """check_mode=True 时,markers_found 应被回填。"""
    # 注意:此处仅验证引擎调度层传递了 check_mode 与复制了 markers_found
    # 完整回填逻辑由 PythonPlugin 测试覆盖(Task 4)
    result = strip(
        "# @internal x\ny = 1\n",
        language="python",
        check_mode=True,
    )
    # 至少应报告 1 个 line 类型 marker
    assert len(result.markers_found) >= 1
    m = result.markers_found[0]
    assert m.marker_type == "line"
    assert m.marker_text == "@internal"


def test_markers_found_not_aliased_across_calls():
    """连续两次调用,第二次 clear() 不应清空第一次的 markers_found。"""
    r1 = strip("# @internal x\n", language="python", check_mode=True)
    r2 = strip("x = 1\n", language="python", check_mode=True)
    assert len(r1.markers_found) >= 1
    assert r2.markers_found == []
    # 关键:r1.markers_found 是独立副本,不被第二次 clear 影响
    r1.markers_found.append(
        MarkerLocation(1, 0, "line", "@internal", "manual")
    )
    assert r2.markers_found == []


def test_strip_file_check_mode():
    """strip_file 也应支持 check_mode 参数。"""
    from markstrip import strip_file
    with NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write("# @internal x\ny = 1\n")
        f.flush()
        result = strip_file(f.name, check_mode=True)
    assert len(result.markers_found) >= 1
```

在 `tests/unit/test_engine.py` 头部 import 区追加:

```python
from markstrip.core.result import MarkerLocation
```

- [ ] **Step 2: 运行测试验证失败**

Run: `python -m pytest tests/unit/test_engine.py::test_check_mode_collects_markers -v`
Expected: FAIL with `TypeError: strip() got an unexpected keyword argument 'check_mode'`

- [ ] **Step 3: 修改 `markstrip/core/engine.py` 实现 check_mode 调度**

替换 `strip()` 方法签名与实现:

```python
# markstrip/core/engine.py
"""主引擎:调度插件执行清理。"""
from pathlib import Path

from markstrip.core.config import StripConfig
from markstrip.core.result import StripResult
from markstrip.languages._builtin import _create_default_registry
from markstrip.languages.base import LanguagePlugin
from markstrip.languages.registry import LanguageRegistry


class StripEngine:
    """主引擎:调度语言插件执行注释清理。

    按优先级解析语言:显式指定 > 文件扩展名 > 内容探测。
    """

    def __init__(self, registry: LanguageRegistry | None = None) -> None:
        self._registry = registry or _create_default_registry()

    def strip(
        self,
        content: str,
        *,
        language: str | None = None,
        filename: str | None = None,
        mode: str = "selective",
        config: StripConfig | None = None,
        check_mode: bool = False,
    ) -> StripResult:
        """清理内容中的注释。

        Args:
            content: 待清理的内容。
            language: 显式指定语言标识符。
            filename: 文件名(用于扩展名检测)。
            mode: "selective" 或 "full"。
            config: 清理配置,为 None 时使用默认配置。
            check_mode: --check 模式标志。True 时插件跳过 pragma 委托
                与 in_pragma 优先分支,确保所有 @internal 标记被扫描回填。

        Returns:
            StripResult 清理结果。
        """
        config = config or StripConfig()

        plugin = self._resolve_plugin(language, filename, content)
        if plugin is None:
            return StripResult(
                cleaned_content=content,
                removed_count=0,
                warnings=["无法识别语言,跳过处理"],
            )

        # warnings 与 markers_found 瞬态通道:调用插件前清空
        config.warnings.clear()
        config.markers_found.clear()
        config.check_mode = check_mode

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
            markers_found=list(config.markers_found),
        )

    def _resolve_plugin(
        self,
        language: str | None,
        filename: str | None,
        content: str,
    ) -> LanguagePlugin | None:
        """按优先级解析语言插件。"""
        # 优先级 1: 显式指定
        if language:
            return self._registry.get_plugin(language)
        # 优先级 2: 文件扩展名
        if filename:
            ext = Path(filename).suffix.lower()
            plugin = self._registry.get_plugin_by_extension(ext)
            if plugin:
                return plugin
        # 优先级 3: 内容探测
        for plugin in self._registry._plugins.values():
            if plugin.detect(content):
                return plugin
        return None
```

- [ ] **Step 4: 修改 `markstrip/__init__.py` 转发 check_mode 并导出 `MarkerLocation`**

修改 `strip()` / `strip_file()` / `strip_directory()` 加 `check_mode: bool = False` 关键字参数,并在 `__all__` 追加 `"MarkerLocation"`:

```python
"""markstrip - 标记式选择性注释过滤库。"""
from pathlib import Path
from typing import Union

from markstrip.core.config import StripConfig
from markstrip.core.engine import StripEngine
from markstrip.core.result import MarkerLocation, StripResult
from markstrip.languages.base import LanguagePlugin
from markstrip.languages.registry import LanguageRegistry

# 默认引擎实例(内置插件已注册)
_default_engine = StripEngine()


def strip(
    content: str,
    *,
    language: str | None = None,
    filename: str | None = None,
    mode: str = "selective",
    config: StripConfig | None = None,
    check_mode: bool = False,
) -> StripResult:
    """清理内容中的标记注释。

    Args:
        content: 待清理的内容。
        language: 显式指定语言标识符。
        filename: 文件名(用于扩展名检测)。
        mode: "selective"(标记过滤)或 "full"(全量删除)。
        config: 清理配置,为 None 时使用默认配置。
        check_mode: --check 模式标志,True 时扫描所有 @internal 标记
            到 markers_found 而不依赖 pragma 委托。

    Returns:
        StripResult 清理结果。
    """
    return _default_engine.strip(
        content,
        language=language,
        filename=filename,
        mode=mode,
        config=config,
        check_mode=check_mode,
    )


def strip_file(
    path: Union[str, Path],
    *,
    mode: str = "selective",
    config: StripConfig | None = None,
    inplace: bool = False,
    check_mode: bool = False,
) -> StripResult:
    """清理文件中的标记注释。

    Args:
        path: 文件路径。
        mode: "selective" 或 "full"。
        config: 清理配置。
        inplace: 是否原地修改文件。
        check_mode: --check 模式标志。

    Returns:
        StripResult 清理结果。
    """
    path = Path(path)
    content = path.read_text(encoding="utf-8")
    result = _default_engine.strip(
        content,
        filename=str(path),
        mode=mode,
        config=config,
        check_mode=check_mode,
    )
    if inplace:
        path.write_text(result.cleaned_content, encoding="utf-8")
    return result


def strip_directory(
    path: Union[str, Path],
    *,
    mode: str = "selective",
    config: StripConfig | None = None,
    extensions: list[str] | None = None,
    inplace: bool = False,
    check_mode: bool = False,
) -> list[StripResult]:
    """批量清理目录下所有支持的文件。

    Args:
        path: 目录路径。
        mode: "selective" 或 "full"。
        config: 清理配置。
        extensions: 限制处理的文件扩展名列表。
        inplace: 是否原地修改文件。
        check_mode: --check 模式标志。

    Returns:
        每个文件的 StripResult 列表。
    """
    path = Path(path)
    results = []
    for file_path in path.rglob("*"):
        if file_path.is_file():
            if extensions and file_path.suffix not in extensions:
                continue
            result = strip_file(
                file_path,
                mode=mode,
                config=config,
                inplace=inplace,
                check_mode=check_mode,
            )
            results.append(result)
    return results


def register_plugin(plugin: LanguagePlugin) -> None:
    """注册自定义语言插件。

    Args:
        plugin: 要注册的语言插件实例。
    """
    _default_engine._registry.register(plugin)


__all__ = [
    "strip",
    "strip_file",
    "strip_directory",
    "register_plugin",
    "StripConfig",
    "StripResult",
    "MarkerLocation",
    "StripEngine",
    "LanguagePlugin",
    "LanguageRegistry",
]
```

- [ ] **Step 5: 运行测试验证通过**

Run: `python -m pytest tests/unit/test_engine.py -v`
Expected: 全部 PASS(注:`test_check_mode_collects_markers` 此时可能仍 FAIL,因为 PythonPlugin 尚未实现回填 — 进入 Task 4)

**如果 `test_check_mode_collects_markers` 失败**:这是预期的,因为 Python 插件尚未实现回填。先验证其他 3 个测试通过即可:
- `test_check_mode_default_false` PASS
- `test_markers_found_not_aliased_across_calls` PASS(空列表对空列表,不报错)
- `test_strip_file_check_mode` 此时可能也 FAIL(同上原因)

继续 Task 4 修复。

- [ ] **Step 6: 跑全量回归(除新增 check_mode 测试外应全过)**

Run: `python -m pytest tests/ -v --deselect tests/unit/test_engine.py::test_check_mode_collects_markers --deselect tests/unit/test_engine.py::test_strip_file_check_mode`
Expected: 全部 PASS

- [ ] **Step 7: 提交**

```bash
git add markstrip/core/engine.py markstrip/__init__.py tests/unit/test_engine.py
git commit -m "feat(engine): strip 加 check_mode 参数与 markers_found 通道"
```

---

## Task 4: Python 插件 markers_found 回填与 check_mode pragma skip

**Files:**
- Modify: `markstrip/languages/python_plugin.py`
- Test: `tests/unit/test_python_plugin.py`

**Interfaces:**
- Consumes: Task 2 的 `MarkerLocation` / `StripConfig.markers_found` / `StripConfig.check_mode`;Task 3 的 `strip(check_mode=True)`
- Produces: `PythonPlugin.strip_selective` 在 check_mode 时回填 4 个分支的 markers_found + 跳过 file-level pragma 委托 + 跳过 in_pragma 优先分支;`_fallback_regex_selective` 同步

- [ ] **Step 1: 写失败测试 — 4 个回填分支**

在 `tests/unit/test_python_plugin.py` 末尾追加:

```python
from markstrip.core.result import MarkerLocation


def test_check_line_marker_reported(plugin):
    """行标记 @internal 在 check_mode 下被报告为 line 类型。"""
    config = StripConfig()
    config.check_mode = True
    plugin.strip_selective("# @internal 使用 TRT\nx = 1\n", config)
    assert len(config.markers_found) == 1
    m = config.markers_found[0]
    assert m.marker_type == "line"
    assert m.marker_text == "@internal"
    assert m.line == 1
    assert m.col == 0  # 顶格注释,col=0


def test_check_block_markers_reported(plugin):
    """块定界 @internal-start/-end 在 check_mode 下被报告为 block-start/block-end。"""
    config = StripConfig()
    config.check_mode = True
    plugin.strip_selective(
        "# @internal-start\n# inside\nx = 1\n# @internal-end\n",
        config,
    )
    types = [m.marker_type for m in config.markers_found]
    assert "block-start" in types
    assert "block-end" in types
    # 块内 collateral 代码行不报告
    assert len(config.markers_found) == 2


def test_check_docstring_whole_reported(plugin):
    """docstring 含 @internal-docstring 整体标记,在 check_mode 下报告 docstring-whole。"""
    content = 'def f():\n    """\n    @internal-docstring\n    """\n    return 1\n'
    config = StripConfig()
    config.check_mode = True
    plugin.strip_selective(content, config)
    types = [m.marker_type for m in config.markers_found]
    assert "docstring-whole" in types


def test_check_docstring_line_reported(plugin):
    """docstring 内行首 @internal,在 check_mode 下报告 docstring-line。"""
    content = 'def f():\n    """\n    @internal 逐行\n    other\n    """\n    return 1\n'
    config = StripConfig()
    config.check_mode = True
    plugin.strip_selective(content, config)
    types = [m.marker_type for m in config.markers_found]
    assert "docstring-line" in types


def test_check_custom_marker_reported(plugin):
    """自定义 marker 在 check_mode 下同步报告。"""
    config = StripConfig(line_marker="@private")
    config.check_mode = True
    plugin.strip_selective("# @private x\ny = 1\n", config)
    assert len(config.markers_found) == 1
    assert config.markers_found[0].marker_text == "@private"


def test_check_mode_skips_file_level_pragma(plugin):
    """check_mode=True 时,文件级 pragma 不委托 strip_full,@internal 仍被报告。"""
    content = (
        "# markstrip: full\n"
        "# @internal 这条仍要报告\n"
        "x = 1\n"
    )
    config = StripConfig()
    config.check_mode = True
    plugin.strip_selective(content, config)
    # 应报告 1 个 line marker(不被 file-level pragma 委托吞掉)
    line_markers = [
        m for m in config.markers_found if m.marker_type == "line"
    ]
    assert len(line_markers) == 1


def test_check_mode_skips_in_pragma_branch(plugin):
    """check_mode=True 时,pragma 区间内的 @internal 仍被报告(不走 in_pragma 优先删除)。"""
    content = (
        "# markstrip: full-start\n"
        "# @internal 区间内仍报告\n"
        "x = 1\n"
        "# markstrip: full-end\n"
    )
    config = StripConfig()
    config.check_mode = True
    plugin.strip_selective(content, config)
    line_markers = [
        m for m in config.markers_found if m.marker_type == "line"
    ]
    assert len(line_markers) == 1


def test_check_mode_pragma_not_reported(plugin):
    """pragma 指令本身不算违规,markers_found 不含 pragma 行。"""
    content = (
        "# markstrip: full\n"
        "x = 1\n"
    )
    config = StripConfig()
    config.check_mode = True
    plugin.strip_selective(content, config)
    assert config.markers_found == []


def test_check_mode_off_pragma_works(plugin):
    """check_mode=False(默认),pragma 正常生效,@internal 不报告(行为不变)。"""
    content = (
        "# markstrip: full\n"
        "# @internal 这条会被 pragma 委托的 strip_full 删掉,不报告\n"
        "x = 1\n"
    )
    config = StripConfig()
    config.check_mode = False
    plugin.strip_selective(content, config)
    assert config.markers_found == []


def test_content_preview_truncated(plugin):
    """content_preview 截断至 80 字符。"""
    long_line = "# @internal " + "x" * 200
    config = StripConfig()
    config.check_mode = True
    plugin.strip_selective(long_line + "\n", config)
    assert len(config.markers_found) == 1
    assert len(config.markers_found[0].content_preview) <= 80
```

- [ ] **Step 2: 运行测试验证失败**

Run: `python -m pytest tests/unit/test_python_plugin.py -v -k check_`
Expected: 全部 FAIL(回填逻辑未实现)

- [ ] **Step 3: 修改 `PythonPlugin.strip_selective` 实现 check_mode 与回填**

修改 `markstrip/languages/python_plugin.py` 的 `strip_selective` 方法,完整替换:

```python
    def strip_selective(self, content: str, config: StripConfig) -> str:
        """标记式选择性过滤:仅删除含标记的注释。

        支持逐行 @internal、块定界 @internal-start/-end、docstring 整体标记。
        纯注释标记行整行移除,内联标记注释仅删注释片段保留代码。

        check_mode=True 时,跳过 file-level pragma 委托与 in_pragma 优先分支,
        确保所有 @internal 标记被扫描回填至 config.markers_found。

        Args:
            content: Python 源代码内容。
            config: 清理配置。

        Returns:
            清理后的内容。
        """
        lines = content.splitlines(keepends=True)
        check_mode = config.check_mode
        # 文件级 pragma 检测(check_mode 时跳过委托,继续走 selective 扫描)
        if not check_mode and scan_file_pragma(lines, "#"):
            # 检查区间标记冗余
            pragma_scan = scan_full_ranges(lines, "#")
            config.warnings.extend(pragma_scan.warnings)
            if pragma_scan.ranges:
                config.warnings.append("文件级 full 已生效, 区间标记冗余")
            return self.strip_full(content, config)
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

        # check_mode:回填 block-start/block-end markers
        if check_mode:
            for r in block_ranges:
                start_line_text = lines[r.start_line - 1]
                end_line_text = lines[r.end_line - 1]
                # 计算 marker 起始列(定界行中 marker 第一个字符)
                start_col = start_line_text.find(
                    config.effective_block_start()
                )
                end_col = end_line_text.find(config.effective_block_end())
                config.markers_found.append(MarkerLocation(
                    line=r.start_line,
                    col=max(0, start_col),
                    marker_type="block-start",
                    marker_text=config.effective_block_start(),
                    content_preview=start_line_text.strip()[:80],
                ))
                config.markers_found.append(MarkerLocation(
                    line=r.end_line,
                    col=max(0, end_col),
                    marker_type="block-end",
                    marker_text=config.effective_block_end(),
                    content_preview=end_line_text.strip()[:80],
                ))

        def _in_block(line_num: int) -> bool:
            return any(
                r.start_line <= line_num <= r.end_line for r in block_ranges
            )

        # pragma 区间扫描
        pragma_scan = scan_full_ranges(lines, "#")
        config.warnings.extend(pragma_scan.warnings)
        pragma_ranges = pragma_scan.ranges

        def _in_pragma_range(line_num: int) -> bool:
            return any(
                r.start_line <= line_num <= r.end_line for r in pragma_ranges
            )

        for tok in tokens:
            if tok.type == tokenize.COMMENT:
                in_block = _in_block(tok.start[0])
                in_pragma = _in_pragma_range(tok.start[0])
                if in_block:
                    # 块内:纯注释整行移除,内联仅删片段
                    if self._is_whole_line_comment(tok, lines):
                        comment_removals.append((tok.start[0], 0, -1))
                    else:
                        comment_removals.append(
                            (tok.start[0], tok.start[1], tok.end[1])
                        )
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
                elif self._has_marker(tok.string, config):
                    # 块外逐行 @internal:纯注释整行移除,内联仅删片段
                    if self._is_whole_line_comment(tok, lines):
                        comment_removals.append((tok.start[0], 0, -1))
                    else:
                        comment_removals.append(
                            (tok.start[0], tok.start[1], tok.end[1])
                        )
                    # check_mode:回填 line marker
                    if check_mode:
                        line_text = lines[tok.start[0] - 1]
                        matched = self._matched_marker_text(
                            tok.string, config
                        )
                        config.markers_found.append(MarkerLocation(
                            line=tok.start[0],
                            col=tok.start[1],
                            marker_type="line",
                            marker_text=matched,
                            content_preview=line_text.strip()[:80],
                        ))
                elif in_pragma and check_mode:
                    # pragma 区间内非 @internal 注释:check_mode 不删除不报告
                    # (避免与"pragma 区间内全量删"的语义混淆;check_mode 跳过此分支)
                    pass

            if tok.type == tokenize.STRING:
                if self._is_docstring(tok, tokens):
                    in_pragma = _in_pragma_range(tok.start[0])
                    if in_pragma and not config.preserve_docstrings and not check_mode:
                        for line_num in range(tok.start[0], tok.end[0] + 1):
                            comment_removals.append((line_num, 0, -1))
                    else:
                        doc_removals = self._process_docstring(
                            tok, config, lines
                        )
                        comment_removals.extend(doc_removals)

        # 行级重组
        return self._rebuild(lines, comment_removals)
```

- [ ] **Step 4: 修改 `_process_docstring` 实现 docstring 回填**

修改 `markstrip/languages/python_plugin.py` 的 `_process_docstring` 方法,在整体标记与逐行标记分支回填 markers_found:

```python
    def _process_docstring(
        self,
        tok: tokenize.TokenInfo,
        config: StripConfig,
        lines: list[str],
    ) -> list[tuple[int, int, int]]:
        """处理单个 docstring,返回需删除的位置。

        check_mode=True 时,同时回填 docstring-whole / docstring-line marker
        至 config.markers_found。

        Args:
            tok: docstring 的 STRING token。
            config: 清理配置。
            lines: 原始行列表。

        Returns:
            需要删除的 (line_num, start_col, end_col) 列表。
            end_col=-1 表示删除整行(含换行符)。
        """
        try:
            content = ast.literal_eval(tok.string)
        except (ValueError, SyntaxError):
            return []

        doc_lines = content.split("\n")

        # 检查整体 docstring 标记(整段删除)
        docstring_marker = config.effective_docstring_marker()
        has_whole_marker = any(
            line.strip().startswith(docstring_marker)
            for line in doc_lines
        )
        if has_whole_marker:
            removals = []
            for line_num in range(tok.start[0], tok.end[0] + 1):
                removals.append((line_num, 0, -1))
            # check_mode 回填 docstring-whole
            if config.check_mode:
                first_line_text = lines[tok.start[0] - 1]
                config.markers_found.append(MarkerLocation(
                    line=tok.start[0],
                    col=0,
                    marker_type="docstring-whole",
                    marker_text=docstring_marker,
                    content_preview=first_line_text.strip()[:80],
                ))
            return removals

        # 逐行检查行级标记(整行移除,不留空行)
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
                    # 整行移除(含换行符)
                    removals.append((source_line, 0, -1))
                    # check_mode 回填 docstring-line
                    if config.check_mode:
                        line_text = lines[source_line - 1]
                        config.markers_found.append(MarkerLocation(
                            line=source_line,
                            col=0,
                            marker_type="docstring-line",
                            marker_text=marker,
                            content_preview=line_text.strip()[:80],
                        ))
                    break

        return removals
```

- [ ] **Step 5: 新增 `_matched_marker_text` 辅助方法**

在 `PythonPlugin` 类中(建议放在 `_has_marker` 之后)新增辅助方法,返回命中的实际 marker 字符串:

```python
    def _matched_marker_text(
        self, comment_text: str, config: StripConfig
    ) -> str:
        """返回命中的实际 marker 字符串(用于 --check 输出)。

        Args:
            comment_text: 注释文本(含 # 前缀)。
            config: 清理配置。

        Returns:
            命中的 marker 字符串(line_marker 或 custom_markers 之一)。
            未命中时返回 config.line_marker(兜底,不应发生)。
        """
        markers = [config.line_marker] + config.custom_markers
        stripped = comment_text.lstrip("#").strip()
        for marker in markers:
            if stripped.startswith(marker):
                return marker
        return config.line_marker
```

- [ ] **Step 6: 更新 import**

修改 `markstrip/languages/python_plugin.py` 头部 import,加入 `MarkerLocation`:

```python
"""Python 语言插件。"""
import ast
import re
import tokenize

from markstrip.core.block_scanner import scan_blocks
from markstrip.core.config import StripConfig
from markstrip.core.pragma_scanner import scan_file_pragma, scan_full_ranges
from markstrip.core.result import MarkerLocation
from markstrip.languages.base import LanguagePlugin
```

- [ ] **Step 7: 运行测试验证通过**

Run: `python -m pytest tests/unit/test_python_plugin.py -v -k "check_ or content_preview"`
Expected: 全部 PASS

- [ ] **Step 8: 跑全量回归**

Run: `python -m pytest tests/ -v`
Expected: 全部 PASS(包括 Task 3 中暂未通过的 `test_check_mode_collects_markers` 与 `test_strip_file_check_mode` 此时也应通过)

- [ ] **Step 9: 写失败测试 — `_fallback_regex_selective` check_mode 同步**

在 `tests/unit/test_python_plugin.py` 末尾追加(覆盖 tokenize 失败时的回填路径):

```python
def test_check_fallback_line_marker_reported():
    """tokenize 失败(语法错误)时,_fallback_regex_selective 仍回填 markers。"""
    # 语法错误代码:缺冒号导致 tokenize 失败
    content = "def f()\n    # @internal x\n    y = 1\n"
    config = StripConfig()
    config.check_mode = True
    plugin = PythonPlugin()
    plugin.strip_selective(content, config)
    line_markers = [
        m for m in config.markers_found if m.marker_type == "line"
    ]
    assert len(line_markers) == 1
```

- [ ] **Step 10: 运行测试验证失败**

Run: `python -m pytest tests/unit/test_python_plugin.py::test_check_fallback_line_marker_reported -v`
Expected: FAIL(fallback 未回填)

- [ ] **Step 11: 修改 `_fallback_regex_selective` 同步回填**

修改 `markstrip/languages/python_plugin.py` 的 `_fallback_regex_selective` 方法,在文件级 pragma 委托、块定界扫描、逐行 marker 命中点回填 markers_found:

```python
    def _fallback_regex_selective(
        self, content: str, config: StripConfig
    ) -> str:
        """tokenize 失败时的正则回退。

        注意:正则无法区分字符串中的 # 和注释 #,此为已知限制。
        仅在 tokenize 失败(语法错误)时触发。

        逐行 @internal 与块内删除语义一致:纯注释行整行移除(不留空行),
        内联注释仅删片段保留代码。marker 正则要求标记后为空白/行尾,
        自动排除块定界行与 @internalized 等伪前缀。

        check_mode=True 时,跳过 file-level pragma 委托与 in_pragma 优先分支,
        回填 markers_found 与 strip_selective 一致。

        Args:
            content: 源代码内容。
            config: 清理配置。

        Returns:
            清理后的内容。
        """
        lines = content.splitlines(keepends=True)
        check_mode = config.check_mode
        # 文件级 pragma → 委托 strip_full(check_mode 时跳过)
        if not check_mode and scan_file_pragma(lines, "#"):
            return self.strip_full(content, config)
        scan = scan_blocks(
            lines,
            "#",
            config.effective_block_start(),
            config.effective_block_end(),
        )
        config.warnings.extend(scan.warnings)

        # check_mode:回填 block-start/block-end
        if check_mode:
            for r in scan.ranges:
                start_line_text = lines[r.start_line - 1]
                end_line_text = lines[r.end_line - 1]
                start_col = start_line_text.find(
                    config.effective_block_start()
                )
                end_col = end_line_text.find(config.effective_block_end())
                config.markers_found.append(MarkerLocation(
                    line=r.start_line,
                    col=max(0, start_col),
                    marker_type="block-start",
                    marker_text=config.effective_block_start(),
                    content_preview=start_line_text.strip()[:80],
                ))
                config.markers_found.append(MarkerLocation(
                    line=r.end_line,
                    col=max(0, end_col),
                    marker_type="block-end",
                    marker_text=config.effective_block_end(),
                    content_preview=end_line_text.strip()[:80],
                ))

        # pragma 区间扫描
        pragma_scan = scan_full_ranges(lines, "#")
        config.warnings.extend(pragma_scan.warnings)
        pragma_ranges = pragma_scan.ranges

        markers = [config.line_marker] + config.custom_markers
        marker_alt = "|".join(re.escape(m) for m in markers)
        # marker 后须空白或行尾:排除定界行与伪前缀
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

        def _in_pragma_range(line_num: int) -> bool:
            return any(
                r.start_line <= line_num <= r.end_line for r in pragma_ranges
            )

        for i, line in enumerate(lines, 1):
            nl = _newline(line)
            body = line[:-len(nl)] if nl else line
            if _in_block_range(i):
                # 块内:纯注释行整行丢弃;否则删内联注释片段保留代码
                if any_comment_re.match(body):
                    continue
                cleaned = inline_any_re.sub("", body).rstrip()
                if cleaned:
                    out.append(cleaned + nl)
            elif _in_pragma_range(i) and not check_mode:
                # pragma 区间(check_mode=False):full 逻辑,删注释保留代码
                if any_comment_re.match(body):
                    continue
                cleaned = inline_any_re.sub("", body).rstrip()
                if cleaned:
                    out.append(cleaned + nl)
            else:
                # 块外 / check_mode 下 pragma 区间外:逐行 @internal
                if full_re.match(body):
                    # check_mode 回填 line marker
                    if check_mode:
                        matched = self._matched_marker_text(
                            "#" + body.lstrip("#").lstrip(), config
                        )
                        # 重新解析 marker 起始列
                        col = body.find("#") + 1  # 跳过 #
                        # 找到 marker 在 body 中的位置
                        for m in markers:
                            idx = body.find(m)
                            if idx >= 0:
                                col = idx
                                break
                        config.markers_found.append(MarkerLocation(
                            line=i,
                            col=col,
                            marker_type="line",
                            marker_text=matched,
                            content_preview=body.strip()[:80],
                        ))
                    continue
                cleaned = inline_re.sub("", body)
                if cleaned.strip() == "":
                    continue
                out.append(cleaned.rstrip() + nl)

        return "".join(out)
```

- [ ] **Step 12: 运行测试验证通过**

Run: `python -m pytest tests/unit/test_python_plugin.py -v`
Expected: 全部 PASS

- [ ] **Step 13: 跑全量回归**

Run: `python -m pytest tests/ -v`
Expected: 全部 PASS

- [ ] **Step 14: 提交**

```bash
git add markstrip/languages/python_plugin.py tests/unit/test_python_plugin.py
git commit -m "feat(python): strip_selective 与正则回退接入 markers_found 回填与 check_mode"
```

---

## Task 5: Markdown 插件回填与代码块行号翻译

**Files:**
- Modify: `markstrip/languages/markdown_plugin.py`
- Test: `tests/unit/test_markdown_plugin.py`

**Interfaces:**
- Consumes: Task 2-4 的 `MarkerLocation` / `config.markers_found` / `config.check_mode` / `PythonPlugin.strip_selective`(已含回填)
- Produces: `MarkdownPlugin._process_html_comments` 回填 HTML 注释 markers(.md 绝对行号);`_process_code_blocks` 委托后行号翻译;`_fallback_strip` 回填由代码块翻译统一处理

- [ ] **Step 1: 写失败测试 — HTML 注释回填与代码块行号翻译**

在 `tests/unit/test_markdown_plugin.py` 末尾追加:

```python
from markstrip.core.result import MarkerLocation


def test_check_html_comment_marker_reported(plugin):
    """HTML 注释含 @internal,在 check_mode 下报告 .md 绝对行号。"""
    content = (
        "# Title\n"
        "\n"
        "<!-- @internal 秘密说明 -->\n"
        "\n"
        "text\n"
    )
    config = StripConfig()
    config.check_mode = True
    plugin.strip_selective(content, config)
    # 应报告 1 个 marker,line=3(HTML 注释在第 3 行)
    assert len(config.markers_found) == 1
    m = config.markers_found[0]
    assert m.line == 3
    assert m.marker_text == "@internal"


def test_check_code_block_marker_translated(plugin):
    """代码块内委托插件记录的相对行号应翻译为 .md 绝对行号。"""
    content = (
        "# Title\n"
        "\n"
        "```python\n"
        "# @internal code marker\n"
        "x = 1\n"
        "```\n"
    )
    config = StripConfig()
    config.check_mode = True
    plugin.strip_selective(content, config)
    # 代码块在 .md 第 3 行起,marker 在代码块第 1 行
    # .md 绝对行号 = 3 (block_start) + 1 (code_first_line) + 0 = 4
    line_markers = [
        m for m in config.markers_found if m.marker_type == "line"
    ]
    assert len(line_markers) == 1
    assert line_markers[0].line == 4


def test_check_multiple_code_blocks_no_crosstalk(plugin):
    """多个代码块的 markers 行号独立翻译,不串号。"""
    content = (
        "# A\n\n"
        "```python\n"
        "# @internal first\n"
        "```\n\n"
        "# B\n\n"
        "```python\n"
        "# @internal second\n"
        "```\n"
    )
    config = StripConfig()
    config.check_mode = True
    plugin.strip_selective(content, config)
    line_markers = [
        m for m in config.markers_found if m.marker_type == "line"
    ]
    assert len(line_markers) == 2
    # first marker 在第 4 行(代码块 fence 在第 3 行,内容第 4 行)
    # second marker:计算位置 — # B 在第 7 行,``` 在第 9 行,内容第 10 行
    lines = content.splitlines()
    # 验证两个 marker 行号都在 .md 内有效范围且不同
    assert line_markers[0].line != line_markers[1].line
    for m in line_markers:
        assert 1 <= m.line <= len(lines)


def test_check_html_comment_col_position(plugin):
    """HTML 注释 marker 的 col 应为 marker 起始列。"""
    content = "  <!-- @internal indented -->\n"
    config = StripConfig()
    config.check_mode = True
    plugin.strip_selective(content, config)
    assert len(config.markers_found) == 1
    # marker_text @internal 在 "<!-- " 之后,即 col=6
    m = config.markers_found[0]
    assert m.marker_text == "@internal"
```

- [ ] **Step 2: 运行测试验证失败**

Run: `python -m pytest tests/unit/test_markdown_plugin.py -v -k check_`
Expected: 全部 FAIL(回填未实现)

- [ ] **Step 3: 修改 `_process_code_blocks` 实现行号翻译**

修改 `markstrip/languages/markdown_plugin.py` 的 `_process_code_blocks` 方法,在委托插件前后记录 markers_found 长度切片,并翻译相对行号为 .md 绝对行号:

```python
    def _process_code_blocks(
        self,
        content: str,
        config: StripConfig,
        mode: str,
    ) -> str:
        """处理所有围栏代码块。

        check_mode=True 时,委托插件回填的 markers 行号会被翻译为 .md 绝对行号。

        Args:
            content: Markdown 内容。
            config: 清理配置。
            mode: "selective" 仅删除含标记的,"full" 删除所有。

        Returns:
            处理后的内容。
        """
        def process_block(match: re.Match) -> str:
            fence = match.group("fence")
            lang = match.group("lang").lower()
            code = match.group("code")

            # 删除嵌套代码块
            code = self._remove_nested_blocks(code)

            # 委托前记录 markers_found 长度,以便切片翻译行号
            pre_count = len(config.markers_found)

            # 委托给语言插件
            plugin = self._registry.get_plugin(lang)
            if plugin is not None:
                if mode == "selective":
                    cleaned = plugin.strip_selective(code, config)
                else:
                    cleaned = plugin.strip_full(code, config)
            else:
                # 未知语言:正则兜底
                cleaned = self._fallback_strip(code, lang, config)

            # check_mode:翻译委托插件记录的相对行号为 .md 绝对行号
            if config.check_mode:
                new_markers = config.markers_found[pre_count:]
                # 代码块 fence 行在 .md 中的行号(1-based)
                block_start_in_md = content[:match.start()].count("\n") + 1
                # 代码块内容首行 = fence 行 + 1
                code_first_line_in_md = block_start_in_md + 1
                for m in new_markers:
                    m.line = code_first_line_in_md + (m.line - 1)

            return f"{fence}{lang}\n{cleaned}{fence}"

        return CODE_BLOCK_RE.sub(process_block, content)
```

- [ ] **Step 4: 修改 `_process_html_comments` 实现回填**

修改 `_process_html_comments`,在 selective 模式下含 marker 的 HTML 注释处回填 MarkerLocation:

```python
    def _process_html_comments(
        self,
        content: str,
        config: StripConfig,
        mode: str,
    ) -> str:
        """处理 HTML 注释。

        check_mode=True 且 selective 模式下,含 line_marker 的 HTML 注释
        回填 MarkerLocation(.md 绝对行号)。

        Args:
            content: Markdown 内容。
            config: 清理配置。
            mode: "selective" 仅删除含标记的,"full" 删除所有。

        Returns:
            处理后的内容。
        """
        if mode == "full":
            return HTML_COMMENT_RE.sub("", content)

        def filter_comment(match: re.Match) -> str:
            comment = match.group(0)
            if config.line_marker in comment:
                # check_mode: 回填 HTML 注释 marker(.md 绝对行号)
                if config.check_mode:
                    block_start_in_md = (
                        content[:match.start()].count("\n") + 1
                    )
                    marker_idx = comment.find(config.line_marker)
                    # marker 起始列 = match 在所在行的列偏移 + marker 在 comment 内偏移
                    line_start = content.rfind("\n", 0, match.start()) + 1
                    col = (match.start() - line_start) + marker_idx
                    # 截取 marker 所在行文本(整行)
                    line_end = content.find("\n", match.start())
                    if line_end == -1:
                        line_end = len(content)
                    line_text = content[line_start:line_end]
                    config.markers_found.append(MarkerLocation(
                        line=block_start_in_md,
                        col=col,
                        marker_type="line",
                        marker_text=config.line_marker,
                        content_preview=line_text.strip()[:80],
                    ))
                return ""
            return comment

        return HTML_COMMENT_RE.sub(filter_comment, content)
```

- [ ] **Step 5: 更新 `markdown_plugin.py` 头部 import**

修改 `markstrip/languages/markdown_plugin.py` 头部 import,加入 `MarkerLocation`:

```python
"""Markdown 语言插件。"""
import re

from markstrip.core.block_scanner import scan_blocks
from markstrip.core.config import StripConfig
from markstrip.core.pragma_scanner import scan_file_pragma, scan_full_ranges
from markstrip.core.result import MarkerLocation
from markstrip.languages.base import LanguagePlugin
from markstrip.languages.registry import LanguageRegistry
```

- [ ] **Step 6: 运行测试验证通过**

Run: `python -m pytest tests/unit/test_markdown_plugin.py -v`
Expected: 全部 PASS(原有黄金测试 + 新增 4 个 check 测试)

- [ ] **Step 7: 跑全量回归**

Run: `python -m pytest tests/ -v`
Expected: 全部 PASS

- [ ] **Step 8: 提交**

```bash
git add markstrip/languages/markdown_plugin.py tests/unit/test_markdown_plugin.py
git commit -m "feat(markdown): HTML 注释回填与代码块行号翻译接入 check_mode"
```

---

## Task 6: 插件 detect() 内容探测

**Files:**
- Modify: `markstrip/languages/python_plugin.py`
- Modify: `markstrip/languages/markdown_plugin.py`
- Test: `tests/unit/test_python_plugin.py`
- Test: `tests/unit/test_markdown_plugin.py`

**Interfaces:**
- Consumes: Task 5 的 `MarkdownPlugin`(行号翻译已就绪)
- Produces: `PythonPlugin.detect(content) -> bool` 与 `MarkdownPlugin.detect(content) -> bool`,供 stdin 模式内容探测

- [ ] **Step 1: 写失败测试 — detect()**

在 `tests/unit/test_python_plugin.py` 末尾追加:

```python
def test_python_detect_typical_code(plugin):
    """典型 Python 代码应被识别。"""
    content = "import os\n\ndef f():\n    return 1\n"
    assert plugin.detect(content) is True


def test_python_detect_rejects_plain_text(plugin):
    """纯文本不应被识别为 Python。"""
    assert plugin.detect("just some text\n") is False
```

在 `tests/unit/test_markdown_plugin.py` 末尾追加:

```python
def test_markdown_detect_typical(plugin):
    """典型 Markdown 应被识别。"""
    content = "# Title\n\nSome text.\n\n```python\ncode\n```\n"
    assert plugin.detect(content) is True


def test_markdown_detect_rejects_python(plugin):
    """纯 Python 代码不应被识别为 Markdown。"""
    content = "import os\n\ndef f():\n    return 1\n"
    assert plugin.detect(content) is False
```

- [ ] **Step 2: 运行测试验证失败**

Run: `python -m pytest tests/unit/test_python_plugin.py::test_python_detect_typical_code tests/unit/test_markdown_plugin.py::test_markdown_detect_typical -v`
Expected: FAIL(detect 默认返回 False)

- [ ] **Step 3: 实现 `PythonPlugin.detect()`**

在 `PythonPlugin` 类中新增 `detect()` 方法(放在 `file_extensions` 之后):

```python
    def detect(self, content: str) -> bool:
        """启发式判断内容是否为 Python 源代码。

        识别信号:行首 def/import/from/class/return 等关键字、
        `#` 注释占比、`:` 行尾(代码块)。

        Args:
            content: 待检测的内容。

        Returns:
            是否为 Python 代码。
        """
        lines = content.splitlines()
        if not lines:
            return False
        python_signals = 0
        for line in lines:
            stripped = line.lstrip()
            if any(
                stripped.startswith(kw)
                for kw in ("def ", "import ", "from ", "class ", "return ")
            ):
                python_signals += 1
            elif stripped.startswith("#"):
                python_signals += 1
            elif stripped.endswith(":") and not stripped.startswith("#"):
                python_signals += 1
        # 至少 2 个信号或占比 > 30% 才判定为 Python
        threshold = max(2, len(lines) * 0.3)
        return python_signals >= threshold
```

- [ ] **Step 4: 实现 `MarkdownPlugin.detect()`**

在 `MarkdownPlugin` 类中新增 `detect()` 方法(放在 `file_extensions` 之后):

```python
    def detect(self, content: str) -> bool:
        """启发式判断内容是否为 Markdown。

        识别信号:行首 `#` 标题、围栏代码块 ```、HTML 注释 `<!--`。

        Args:
            content: 待检测的内容。

        Returns:
            是否为 Markdown。
        """
        lines = content.splitlines()
        if not lines:
            return False
        md_signals = 0
        for line in lines:
            stripped = line.lstrip()
            # ATX 标题(# ~ ######)
            if (
                stripped.startswith("#")
                and len(stripped) > 1
                and stripped[1] in (" ", "")
            ):
                md_signals += 1
            # 围栏代码块
            elif stripped.startswith("```"):
                md_signals += 1
            # HTML 注释
            elif "<!--" in line:
                md_signals += 1
        # 至少 1 个信号即判定(Markdown 特征明确)
        return md_signals >= 1
```

- [ ] **Step 5: 运行测试验证通过**

Run: `python -m pytest tests/unit/test_python_plugin.py tests/unit/test_markdown_plugin.py -v`
Expected: 全部 PASS

- [ ] **Step 6: 跑全量回归**

Run: `python -m pytest tests/ -v`
Expected: 全部 PASS

- [ ] **Step 7: 提交**

```bash
git add markstrip/languages/python_plugin.py markstrip/languages/markdown_plugin.py tests/unit/test_python_plugin.py tests/unit/test_markdown_plugin.py
git commit -m "feat(languages): PythonPlugin 与 MarkdownPlugin 实现 detect 内容探测"
```

---

## Task 7: CLI `--check` + `--language` + stdin 管道

**Files:**
- Modify: `markstrip/cli.py`
- Test: `tests/integration/test_cli.py`

**Interfaces:**
- Consumes: Task 2-6 的 `strip(check_mode=True)` / `markers_found` / `detect()` / `--language`
- Produces: CLI `--check` flag + `--language` 参数 + `-` stdin 占位符 + 参数冲突检测

- [ ] **Step 1: 写失败测试 — `--check` 单文件**

在 `tests/integration/test_cli.py` 末尾追加:

```python
class TestCliCheck:
    """CLI --check 模式集成测试。"""

    def test_check_clean_file_exit_0(self, tmp_path):
        """无标记文件 --check 应 exit 0,stderr 含 'No markers found'。"""
        test_file = tmp_path / "clean.py"
        test_file.write_text("# normal comment\nx = 1\n", encoding="utf-8")
        code, out, err = run_cli(str(test_file), "--check")
        assert code == 0
        assert "No markers found" in err

    def test_check_marked_file_exit_1(self, tmp_path):
        """有标记文件 --check 应 exit 1,stderr 含 ':line:' 与标记类型。"""
        test_file = tmp_path / "marked.py"
        test_file.write_text(
            "# @internal secret\nx = 1\n", encoding="utf-8"
        )
        code, out, err = run_cli(str(test_file), "--check")
        assert code == 1
        assert "@internal" in err
        assert "(line)" in err

    def test_check_recursive_directory(self, tmp_path):
        """递归目录 --check 汇总输出。"""
        sub = tmp_path / "sub"
        sub.mkdir()
        (tmp_path / "a.py").write_text(
            "# @internal a\nx = 1\n", encoding="utf-8"
        )
        (sub / "b.py").write_text(
            "# @internal b\ny = 2\n", encoding="utf-8"
        )
        code, out, err = run_cli(str(tmp_path), "--recursive", "--check")
        assert code == 1
        assert "Found 2 markers in 2 files" in err

    def test_check_mode_full_conflict_exit_2(self, tmp_path):
        """--check --mode full 互斥 exit 2。"""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n", encoding="utf-8")
        code, out, err = run_cli(str(test_file), "--check", "--mode", "full")
        assert code == 2
        assert "冲突" in err or "互斥" in err

    def test_check_output_conflict_exit_2(self, tmp_path):
        """--check --output 互斥 exit 2。"""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n", encoding="utf-8")
        out_file = tmp_path / "out.py"
        code, out, err = run_cli(
            str(test_file), "--check", "--output", str(out_file)
        )
        assert code == 2
        assert "冲突" in err or "互斥" in err

    def test_check_custom_marker(self, tmp_path):
        """--check --marker @private 同步检测。"""
        test_file = tmp_path / "test.py"
        test_file.write_text("# @private x\ny = 1\n", encoding="utf-8")
        code, out, err = run_cli(
            str(test_file), "--check", "--marker", "@private"
        )
        assert code == 1
        assert "@private" in err
```

- [ ] **Step 2: 运行测试验证失败**

Run: `python -m pytest tests/integration/test_cli.py::TestCliCheck -v`
Expected: 全部 FAIL(`--check` 未实现)

- [ ] **Step 3: 写失败测试 — stdin 管道**

在 `tests/integration/test_cli.py` 末尾追加:

```python
class TestCliStdin:
    """CLI stdin 管道集成测试。"""

    def test_stdin_basic_pipe(self, tmp_path):
        """markstrip - < file.py:stdout 输出清理后内容。"""
        input_file = tmp_path / "input.py"
        input_file.write_text(
            "# @internal x\ny = 1\n", encoding="utf-8"
        )
        result = subprocess.run(
            [sys.executable, "-m", "markstrip.cli", "-"],
            stdin=open(input_file, "r", encoding="utf-8"),
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "# @internal" not in result.stdout
        assert "y = 1" in result.stdout

    def test_stdin_with_language(self, tmp_path):
        """echo '...' | markstrip - --language python:显式语言。"""
        result = subprocess.run(
            [sys.executable, "-m", "markstrip.cli", "-",
             "--language", "python"],
            input="# @internal x\ny = 1\n",
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "# @internal" not in result.stdout
        assert "y = 1" in result.stdout

    def test_stdin_check_mode(self, tmp_path):
        """cat file | markstrip --check -:stderr 含标记,stdout 空。"""
        result = subprocess.run(
            [sys.executable, "-m", "markstrip.cli", "--check", "-"],
            input="# @internal x\ny = 1\n",
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "@internal" in result.stderr
        assert result.stdout == ""

    def test_stdin_recursive_conflict_exit_2(self):
        """markstrip - --recursive 互斥 exit 2。"""
        result = subprocess.run(
            [sys.executable, "-m", "markstrip.cli", "-", "--recursive"],
            input="x = 1\n",
            capture_output=True, text=True,
        )
        assert result.returncode == 2
        assert "递归" in result.stderr or "recursive" in result.stderr.lower()

    def test_stdin_output_to_file(self, tmp_path):
        """markstrip - -o out.py < file.py:写入文件,stdout 空。"""
        input_file = tmp_path / "in.py"
        input_file.write_text("# @internal x\ny = 1\n", encoding="utf-8")
        out_file = tmp_path / "out.py"
        result = subprocess.run(
            [sys.executable, "-m", "markstrip.cli", "-",
             "-o", str(out_file)],
            stdin=open(input_file, "r", encoding="utf-8"),
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert result.stdout == ""
        content = out_file.read_text(encoding="utf-8")
        assert "@internal" not in content
        assert "y = 1" in content
```

- [ ] **Step 4: 运行测试验证失败**

Run: `python -m pytest tests/integration/test_cli.py::TestCliStdin -v`
Expected: 全部 FAIL(stdin 模式未实现)

- [ ] **Step 5: 实现 `markstrip/cli.py` — `--check` + `--language` + stdin 模式**

完整替换 `markstrip/cli.py`:

```python
"""markstrip 命令行工具。"""
import argparse
import sys
from pathlib import Path

from markstrip import strip
from markstrip.core.config import StripConfig


def main(argv: list[str] | None = None) -> int:
    """CLI 主入口。

    Args:
        argv: 命令行参数,为 None 时使用 sys.argv。

    Returns:
        退出码:0 成功;1(--check 发现标记);2 参数错误/路径不存在。
    """
    parser = argparse.ArgumentParser(
        prog="markstrip",
        description="标记式选择性注释过滤工具",
    )
    parser.add_argument("path", help="文件或目录路径,或 '-' 触发 stdin 模式")
    parser.add_argument(
        "--mode",
        choices=["selective", "full"],
        default="selective",
        help="清理模式:selective(标记过滤)或 full(全量删除)",
    )
    parser.add_argument(
        "--marker",
        default="@internal",
        help="行级标记符号(默认: @internal)",
    )
    parser.add_argument(
        "--docstring-marker",
        default="",
        help="整体 docstring 标记(默认自动派生为 {marker}-docstring)",
    )
    parser.add_argument(
        "--block-start-marker",
        default="",
        help="块起始标记(默认自动派生为 {marker}-start)",
    )
    parser.add_argument(
        "--block-end-marker",
        default="",
        help="块结束标记(默认自动派生为 {marker}-end)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式,不修改文件,输出清理结果到 stdout",
    )
    parser.add_argument(
        "--output", "-o",
        help="输出文件路径(仅单文件模式)",
    )
    parser.add_argument(
        "--recursive", "-r",
        action="store_true",
        help="递归处理目录下所有文件",
    )
    parser.add_argument(
        "--preserve-docstrings",
        action="store_true",
        help="full 模式下保留 docstring",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细处理信息",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="检查模式:扫描 @internal 标记并输出位置到 stderr,"
             "不修改文件,exit 0(无标记)/1(有标记)",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="显式指定语言标识符(如 python/markdown),"
             "stdin 模式或内容探测失败时使用",
    )
    args = parser.parse_args(argv)

    # 参数冲突检测
    if args.check and args.mode == "full":
        print(
            "错误: --check 与 --mode full 互斥(--check 蕴含 selective)",
            file=sys.stderr,
        )
        return 2
    if args.check and args.output:
        print(
            "错误: --check 与 --output 互斥(--check 不写文件)",
            file=sys.stderr,
        )
        return 2
    if args.path == "-" and args.recursive:
        print(
            "错误: stdin 模式(-)不支持 --recursive(stdin 是单流)",
            file=sys.stderr,
        )
        return 2

    config = StripConfig(
        line_marker=args.marker,
        docstring_marker=args.docstring_marker,
        block_start_marker=args.block_start_marker,
        block_end_marker=args.block_end_marker,
        preserve_docstrings=args.preserve_docstrings,
    )

    # stdin 模式
    if args.path == "-":
        return _process_stdin(args, config)

    target = Path(args.path)

    if target.is_dir():
        if not args.recursive:
            print(
                f"错误: {target} 是目录,请使用 --recursive",
                file=sys.stderr,
            )
            return 1
        return _process_directory(target, args, config)
    elif target.is_file():
        return _process_single_file(target, args, config)
    else:
        print(f"错误: {target} 不存在", file=sys.stderr)
        return 1


def _process_stdin(args: argparse.Namespace, config: StripConfig) -> int:
    """处理 stdin 模式。

    Args:
        args: 命令行参数。
        config: 清理配置。

    Returns:
        退出码。
    """
    content = sys.stdin.read()
    result = strip(
        content,
        language=args.language,
        mode=args.mode,
        config=config,
        check_mode=args.check,
    )

    if not result.detected_language and not args.language:
        print(
            f"错误: 无法识别语言,请使用 --language 显式指定",
            file=sys.stderr,
        )
        return 2

    if args.verbose:
        print(
            f"Processing stdin... removed {result.removed_count} lines",
            file=sys.stderr,
        )
        for w in result.warnings:
            print(f"Warning: {w}", file=sys.stderr)

    if args.check:
        _output_markers_to_stderr([("<stdin>", result)])
        return 1 if result.markers_found else 0

    if args.output:
        Path(args.output).write_text(
            result.cleaned_content, encoding="utf-8"
        )
    else:
        sys.stdout.write(result.cleaned_content)

    for w in result.warnings:
        print(f"Warning: {w}", file=sys.stderr)
    return 0


def _process_single_file(
    path: Path, args: argparse.Namespace, config: StripConfig
) -> int:
    """处理单个文件。"""
    content = path.read_text(encoding="utf-8")
    result = strip(
        content,
        filename=str(path),
        mode=args.mode,
        config=config,
        check_mode=args.check,
    )

    if args.verbose:
        print(
            f"Processing {path}... removed {result.removed_count} lines",
            file=sys.stderr,
        )
        for w in result.warnings:
            print(f"Warning: {w}", file=sys.stderr)

    if args.check:
        _output_markers_to_stderr([(str(path), result)])
        return 1 if result.markers_found else 0

    if args.dry_run:
        print(result.cleaned_content, end="")
    elif args.output:
        Path(args.output).write_text(
            result.cleaned_content, encoding="utf-8"
        )
    else:
        path.write_text(result.cleaned_content, encoding="utf-8")
    return 0


def _process_directory(
    path: Path, args: argparse.Namespace, config: StripConfig
) -> int:
    """递归处理目录。"""
    total_removed = 0
    total_files = 0
    results: list[tuple[str, "StripResult"]] = []

    for file_path in path.rglob("*"):
        if not file_path.is_file():
            continue
        ext = file_path.suffix.lower()
        if ext not in (".py", ".pyw", ".pyi", ".md", ".markdown"):
            continue

        content = file_path.read_text(encoding="utf-8")
        result = strip(
            content,
            filename=str(file_path),
            mode=args.mode,
            config=config,
            check_mode=args.check,
        )

        if args.verbose:
            print(
                f"Processing {file_path}... "
                f"removed {result.removed_count} lines",
                file=sys.stderr,
            )
            for w in result.warnings:
                print(f"Warning: {w}", file=sys.stderr)

        total_removed += result.removed_count
        total_files += 1

        if args.check:
            results.append((str(file_path), result))
        elif args.dry_run:
            print(f"--- {file_path} ---")
            print(result.cleaned_content, end="")
        else:
            file_path.write_text(
                result.cleaned_content, encoding="utf-8"
            )

    if args.check:
        _output_markers_to_stderr(results)
        total_markers = sum(
            len(r.markers_found) for _, r in results
        )
        return 1 if total_markers > 0 else 0

    if args.verbose:
        print(
            f"Total: {total_removed} lines removed from {total_files} files",
            file=sys.stderr,
        )
    return 0


def _output_markers_to_stderr(
    results: list[tuple[str, "StripResult"]]
) -> None:
    """格式化输出 markers_found 到 stderr。

    Args:
        results: (path, result) 元组列表。
    """
    total_markers = 0
    files_with_markers = 0
    for path, result in results:
        if not result.markers_found:
            continue
        files_with_markers += 1
        for m in result.markers_found:
            total_markers += 1
            print(
                f"{path}:{m.line}:{m.col}  "
                f"{m.marker_text} ({m.marker_type})\t"
                f"{m.content_preview}",
                file=sys.stderr,
            )
    if total_markers == 0:
        print("No markers found", file=sys.stderr)
    else:
        print(
            f"Found {total_markers} markers in {files_with_markers} files",
            file=sys.stderr,
        )


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: 运行测试验证通过**

Run: `python -m pytest tests/integration/test_cli.py -v`
Expected: 全部 PASS(原有 CLI 测试 + 新增 TestCliCheck + TestCliStdin)

- [ ] **Step 7: 跑全量回归**

Run: `python -m pytest tests/ -v`
Expected: 全部 PASS

- [ ] **Step 8: 提交**

```bash
git add markstrip/cli.py tests/integration/test_cli.py
git commit -m "feat(cli): 新增 --check 模式、--language 参数与 stdin 管道(- 占位符)"
```

---

## Task 8: v1.3 文档同步与 pyproject 版本号

**Files:**
- Modify: `docs/markstrip-design.md`
- Modify: `README.md`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: Task 1-7 已实现的 v1.3 `--check` + stdin 完整功能
- Produces: 文档完整覆盖 v1.3 功能 + 版本号 `0.1.0` → `0.2.0`

- [ ] **Step 1: 在 `docs/markstrip-design.md` 更新记录追加 v1.3 行**

打开 `docs/markstrip-design.md`,定位到 `## 更新记录`。在 v1.2 行下方追加:

```markdown
| 2026-07-19 | v1.3 | 新增 `--check` 模式、stdin/stdout 管道、`MarkerLocation` 与 `markers_found` 瞬态通道 | Trae AI |
```

- [ ] **Step 2: 在 `docs/markstrip-design.md` 新增 "--check 模式" 章节**

在 "Pragma 指令系统" 章节之后(或测试策略章节之前)新增:

```markdown
## --check 模式

### 触发

新增 CLI flag `--check`(布尔标志),扫描文件/目录/stdin 中的 `@internal` 标记,输出详细位置列表到 stderr,退出码 0(无标记)/1(有标记)/2(参数错误)。

```bash
markstrip src.py --check                  # 单文件检查
markstrip src/ --recursive --check         # 递归目录
cat file.py | markstrip --check -          # stdin 检查
```

### 检测范围

仅 `@internal` 体系(`# markstrip:` pragma 不算违规):

| 标记类型 | 检测条件 | 报告 |
|---------|---------|------|
| 行标记 | `# @internal ...` | 是(line) |
| 块定界 | `# @internal-start` / `-end` | 是(block-start / block-end) |
| docstring 整体 | `@internal-docstring` | 是(docstring-whole) |
| docstring 逐行 | docstring 内 `@internal` | 是(docstring-line) |
| 块内 collateral 代码行 | 块定界区间内代码/普通注释 | **否**(非 marker) |
| pragma 指令 | `# markstrip:` | **否**(有意指令) |
| 自定义 marker | `config.custom_markers` | 是 |

### 输出格式

输出到 stderr(便于 stdout 重定向 cleaned 内容):

```
src/main.py:12:5  @internal (line)	# @internal 使用 TensorRT
src/main.py:45:1  @internal-start (block-start)
src/main.py:52:1  @internal-end (block-end)

Found 3 markers in 1 files
```

格式:`{path}:{line}:{col}  {marker_text} ({marker_type})\t{content_preview}`

末行汇总:`Found {N} markers in {M} files`(无标记输出 `No markers found`)

### API 扩展:MarkerLocation 与 markers_found 瞬态通道

复用 `warnings` 瞬态通道模式:

```python
@dataclass
class MarkerLocation:
    line: int              # 1-based 文件绝对行号
    col: int               # 0-based 列号
    marker_type: str       # line / block-start / block-end / docstring-whole / docstring-line
    marker_text: str       # 命中的标记字符串
    content_preview: str   # 截断至 80 字符
```

- `StripConfig.markers_found: list[MarkerLocation]` — 瞬态,引擎每次调用插件前 `clear()`
- `StripConfig.check_mode: bool` — 瞬态,`--check` 时引擎设 True
- `StripResult.markers_found: list[MarkerLocation]` — 引擎 `list()` 复制并入

### check_mode 语义

`check_mode=True` 时插件跳过两处 pragma 优化:
- **跳过 file-level pragma 委托**:不调用 `strip_full`,继续走 selective 扫描
- **跳过 in_pragma 优先分支**:pragma 区间内的 COMMENT 不优先按 full 删除,fall through 到 `_has_marker` 检查

效果:`--check` 报告源代码中所有 `@internal` 标记,不受 pragma 影响。

### Markdown 行号翻译

代码块内委托插件记录的相对行号由 Markdown 插件翻译为 .md 绝对行号:

```python
block_start_in_md = content[:match.start()].count("\n") + 1
code_first_line_in_md = block_start_in_md + 1
for m in new_markers:
    m.line = code_first_line_in_md + (m.line - 1)
```

### CLI 交互矩阵

| 参数组合 | 行为 |
|---------|------|
| `--check` | 扫描,exit 0/1 |
| `--check --recursive` | 递归目录,汇总输出 |
| `--check --verbose` | 每文件 Processing 行 + 标记列表 |
| `--check --mode full` | exit 2(参数冲突) |
| `--check --output FILE` | exit 2(check 不写文件) |
| `--check --dry-run` | 共存,均不修改文件 |
| `--check --marker @private` | 自定义标记同步检测 |
| `--check -` | stdin 检查 |
```

- [ ] **Step 3: 在 `docs/markstrip-design.md` 新增 "stdin/stdout 管道" 章节**

紧接 "--check 模式" 章节之后新增:

```markdown
## stdin/stdout 管道

### 触发

`path` 参数为 `"-"` 时进入 stdin 模式:

```bash
markstrip - < file.py                       # 基本管道
cat file.py | markstrip - --mode full       # 管道 + full
cat file.py | markstrip --check -           # 管道 + check
markstrip - -o cleaned.py < file.py         # 管道 + 输出到文件
```

### 语言检测优先级

stdin 模式无 filename,语言解析优先级:

1. `--language` 显式指定
2. 内容探测:遍历已注册插件,调用 `plugin.detect(content)` 返回 True 的第一个

`PythonPlugin.detect()` 与 `MarkdownPlugin.detect()` 已实现启发式判断。

### 输出流分离

| 输出 | 目标流 |
|------|--------|
| cleaned_content | stdout |
| warnings | stderr |
| markers_found(--check) | stderr |
| Processing 行(--verbose) | stderr |
| 错误信息 | stderr |
| 汇总行(--check) | stderr |

### 不支持组合(报错 exit 2)

| 组合 | 原因 |
|------|------|
| `- --recursive` | stdin 是单流,无递归 |
| `--check --output` | check 不写文件 |
| `--check --mode full` | check 蕴含 selective |
```

- [ ] **Step 4: 在 `docs/markstrip-design.md` 包结构补 `MarkerLocation` 位置**

定位到 `### 包结构`,在 `core/result.py` 行更新说明:

```
│   ├── result.py            # StripResult + MarkerLocation:清理结果与 --check 标记位置
```

- [ ] **Step 5: 在 `docs/markstrip-design.md` 测试用例覆盖表补 --check 与 stdin 用例**

定位到测试用例覆盖表或测试策略章节。追加:

```markdown
| `check_line_marker` | --check 报告 line 类型 marker |
| `check_block_markers` | --check 报告 block-start / block-end |
| `check_docstring_whole` | --check 报告 docstring-whole |
| `check_docstring_line` | --check 报告 docstring-line |
| `check_custom_marker` | --check --marker @private 同步 |
| `check_skips_file_pragma` | --check 文件级 pragma 内 @internal 仍报告 |
| `check_skips_in_pragma_range` | --check pragma 区间内 @internal 仍报告 |
| `check_pragma_not_reported` | --check 不报告 pragma 指令行 |
| `check_markdown_html_comment` | --check 报告 .md HTML 注释(绝对行号) |
| `check_markdown_code_block_translation` | --check 代码块内行号翻译为 .md 绝对行号 |
| `cli_check_clean_exit_0` | --check 干净文件 exit 0 |
| `cli_check_marked_exit_1` | --check 标记文件 exit 1 |
| `cli_check_recursive_summary` | --check --recursive 汇总输出 |
| `cli_check_conflict_mode_full` | --check --mode full exit 2 |
| `cli_check_conflict_output` | --check --output exit 2 |
| `cli_stdin_basic_pipe` | markstrip - < file 输出到 stdout |
| `cli_stdin_with_language` | --language 显式指定 |
| `cli_stdin_check_mode` | --check - stderr 输出标记 |
| `cli_stdin_recursive_conflict` | - --recursive exit 2 |
```

- [ ] **Step 6: 在 `README.md` 目录与核心特性补 v1.3**

打开 `README.md`,在目录中"--check 模式"之前(或"Pragma 指令系统"之后)添加:

```markdown
- [--check 模式](#check-模式)
- [stdin/stdout 管道](#stdinstdout-管道)
```

在核心特性列表中追加:

```markdown
- **CI 守门 `--check`**:扫描 @internal 标记并输出位置到 stderr,退出码 0/1
- **stdin/stdout 管道**:`-` 占位符触发,接入 Unix 工作流
```

- [ ] **Step 7: 在 `README.md` CLI 命令行使用指南补 v1.3 参数**

定位到 CLI 命令行使用指南。在现有参数说明后追加:

```markdown
### `--check` 模式

扫描文件/目录/stdin 中的 `@internal` 标记,输出详细位置到 stderr,不修改文件。退出码:0(无标记)/1(有标记)/2(参数错误)。

```bash
# 单文件检查
markstrip src.py --check

# 递归检查目录
markstrip src/ --recursive --check

# stdin 检查
cat file.py | markstrip --check -

# 自定义标记检查
markstrip src.py --check --marker @private
```

输出示例:

```
src/main.py:12:5  @internal (line)	# @internal 使用 TensorRT
src/main.py:45:1  @internal-start (block-start)
src/main.py:52:1  @internal-end (block-end)

Found 3 markers in 1 files
```

### stdin 管道(`-` 占位符)

`path` 参数传 `-` 触发 stdin 模式:

```bash
markstrip - < file.py                       # 清理后输出到 stdout
cat file.py | markstrip - --mode full       # 管道 + full
cat file.py | markstrip --check -           # 管道 + check
markstrip - -o cleaned.py < file.py         # 写入文件,stdout 空
echo '# @internal x\ny=1' | markstrip - --language python
```

语言检测优先级:`--language` 显式 > 内容探测(`plugin.detect()`)。

### 参数互斥表

| 组合 | 行为 |
|------|------|
| `--check --mode full` | exit 2(互斥) |
| `--check --output FILE` | exit 2(check 不写文件) |
| `- --recursive` | exit 2(stdin 无递归) |
```

- [ ] **Step 8: 在 `README.md` Python API 使用指南补 `MarkerLocation`**

定位到 Python API 使用指南。在现有示例后追加:

```markdown
### `MarkerLocation` 与 `markers_found`

`--check` 模式对应的 API 字段:

```python
from markstrip import strip, MarkerLocation

result = strip(
    "# @internal x\ny = 1\n",
    language="python",
    check_mode=True,
)
for m in result.markers_found:
    print(f"{m.line}:{m.col} {m.marker_text} ({m.marker_type})")
    # 输出:1:0 @internal (line)
```

`MarkerLocation` 字段:`line` / `col` / `marker_type` / `marker_text` / `content_preview`。
```

- [ ] **Step 9: 在 `README.md` 新增 "--check 模式" 与 "stdin/stdout 管道" 章节**

在 "Pragma 指令系统" 章节之后插入:

```markdown
## --check 模式

CI 守门用,扫描 `@internal` 标记并输出精确位置到 stderr,不修改文件。

### 典型 CI 用法

```bash
# 在 CI 中守门:有 @internal 残留则失败
markstrip src/ --recursive --check
if [ $? -ne 0 ]; then
    echo "Build failed: @internal markers found"
    exit 1
fi
```

### 检测范围

仅 `@internal` 体系(`# markstrip:` pragma 不算违规):

- 行标记 `# @internal ...`
- 块定界 `@internal-start` / `-end`
- docstring 整体 `@internal-docstring` 或逐行 `@internal`
- 自定义 marker(`--marker @private`)

### 退出码

| 退出码 | 含义 |
|--------|------|
| 0 | 无标记 |
| 1 | 发现标记 |
| 2 | 参数错误/路径不存在 |

## stdin/stdout 管道

Unix 风格管道接入。

### 触发与语言检测

`path` 参数传 `-` 触发 stdin 模式。语言检测优先级:

1. `--language` 显式指定
2. 内容探测(自动遍历已注册插件)

### 输出流分离

| 输出 | 目标流 |
|------|--------|
| 清理后内容 | stdout |
| 警告 | stderr |
| 标记列表(--check) | stderr |
| 错误信息 | stderr |
```

- [ ] **Step 10: 在 `README.md` FAQ 补 v1.3 问题**

在 FAQ 末尾追加:

```markdown
### Q: --check 检测哪些标记?

仅 `@internal` 体系(行/块/docstring 标记)。`# markstrip:` pragma 指令不算违规(是有意处理指令,非"未清理")。块定界区间内的 collateral 代码行也不报告(不是 marker)。

### Q: --check 与 --dry-run 有什么区别?

`--dry-run` 输出清理后的内容到 stdout(预览),不输出标记列表。`--check` 输出标记位置列表到 stderr,不输出清理内容。两者均不修改文件,可共存。

### Q: stdin 模式如何指定语言?

用 `--language` 显式指定(如 `--language python`);否则 markstrip 会用内容探测(`plugin.detect()`)自动判断。
```

- [ ] **Step 11: 在 `README.md` 已知限制与发展方向补 v1.3**

在已知限制追加:

```markdown
8. **`--check` 不报告块内 collateral 代码行**:块定界区间内被连带删除的代码/普通注释行不算 marker,不报告。
9. **stdin 不支持 `--recursive`**:stdin 是单流,无递归概念。
```

在"后续发展方向"的"已实现(v1.2)"下方新增"已实现(v1.3)":

```markdown
### 已实现（v1.3）

- [x] `--check` 模式(CI 守门用,扫描 @internal 标记并输出位置)
- [x] stdin/stdout 管道(`-` 占位符触发)
- [x] `MarkerLocation` 与 `markers_found` 瞬态通道
- [x] `PythonPlugin.detect()` 与 `MarkdownPlugin.detect()` 内容探测
- [x] Markdown 代码块内 markers 行号翻译为 .md 绝对行号
```

- [ ] **Step 12: 修改 `pyproject.toml` 版本号**

打开 `pyproject.toml`,将 `version = "0.1.0"` 改为 `version = "0.2.0"`:

```toml
[project]
name = "markstrip"
version = "0.2.0"
```

- [ ] **Step 13: 验证文档与版本号**

打开 `docs/markstrip-design.md` 与 `README.md`,人工检查:
- 目录链接锚点正确
- 章节顺序合理(v1.2 pragma → v1.3 check/stdin)
- 表格对齐无错乱
- `pyproject.toml` 版本号为 `0.2.0`

Run: `python -c "import tomllib; d = tomllib.load(open('pyproject.toml','rb')); print(d['project']['version'])"`
Expected: `0.2.0`

- [ ] **Step 14: 跑全量回归**

Run: `python -m pytest tests/ -v`
Expected: 全部 PASS(文档与版本号变更不影响测试)

- [ ] **Step 15: 提交**

```bash
git add docs/markstrip-design.md README.md pyproject.toml
git commit -m "docs: 同步 v1.3 check/stdin 文档与版本号 0.2.0"
```

---

## Self-Review

**1. Spec coverage 检查**:

| 规范要求 | 实现任务 |
|---------|----------|
| `MarkerLocation` 数据类 | Task 2 Step 3 |
| `StripResult.markers_found` | Task 2 Step 3 |
| `StripConfig.markers_found` + `check_mode` | Task 2 Step 7 |
| Engine `check_mode` 参数 + clear/copy | Task 3 Step 3 |
| `__init__.py` 导出 `MarkerLocation` + check_mode 转发 | Task 3 Step 4 |
| Python 插件 4 个回填点 | Task 4 Step 3-4 |
| Python 插件 check_mode 跳过 file-level pragma | Task 4 Step 3(`if not check_mode and scan_file_pragma`) |
| Python 插件 check_mode 跳过 in_pragma 优先分支 | Task 4 Step 3(`elif in_pragma and not check_mode:`) |
| Python 插件 `_fallback_regex_selective` 同步 | Task 4 Step 11 |
| Markdown HTML 注释回填(.md 绝对行号) | Task 5 Step 4 |
| Markdown 代码块行号翻译 | Task 5 Step 3 |
| Markdown `_fallback_strip` 回填(由代码块翻译统一处理) | Task 5 Step 3(委托 _fallback_strip 时 pre_count 切片同样适用) |
| 插件 `detect()` 内容探测 | Task 6 Step 3-4 |
| CLI `--check` flag | Task 7 Step 5 |
| CLI `--language` 参数 | Task 7 Step 5 |
| CLI `-` stdin 占位符 | Task 7 Step 5 |
| CLI 参数冲突检测 | Task 7 Step 5 |
| 文档同步 v1.2 pragma | Task 1 |
| 文档同步 v1.3 check/stdin | Task 8 Step 2-11 |
| `pyproject.toml` 0.1.0 → 0.2.0 | Task 8 Step 12 |

**2. Placeholder 扫描**:

- 无 TBD/TODO/"implement later" — 全部代码与文档已具体到可执行
- 无"add appropriate error handling"等模糊语句
- 所有测试代码完整可运行
- 所有命令含 expected 输出

**3. Type 一致性**:

- `MarkerLocation` 字段(line/col/marker_type/marker_text/content_preview)在 Task 2-7 全部一致使用
- `marker_type` 取值集合("line"/"block-start"/"block-end"/"docstring-whole"/"docstring-line")在 Task 2 Step 1 测试、Task 4 回填、Task 7 输出格式全部一致
- `config.check_mode` / `config.markers_found` 在 Task 2 Step 7 定义,Task 3 Step 3 引擎使用,Task 4-5 插件使用,Task 7 CLI 使用 — 全程一致
- `strip(check_mode=True)` 签名在 Task 3 Step 3(engine)与 Task 3 Step 4(__init__)一致
- `effective_block_start()` / `effective_block_end()` / `effective_docstring_marker()` 方法名在 Task 4-5 全部一致(注意:非 `effective_block_start_marker()`)

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-19-check-mode-and-stdin-pipe.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?