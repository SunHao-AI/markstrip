# markstrip `--check` 模式与 stdin/stdout 管道设计

> **日期**: 2026-07-19
> **状态**: 已批准(待实现)
> **作者**: Trae AI
> **关联**: markstrip v1.2 pragma 指令后续演进;同时包含对 v1.2 pragma 已实现功能的文档同步

## 背景与动机

markstrip v1.2 已实现 pragma 指令系统(`# markstrip: full` / `full-start` / `full-end`,提交 `d3d4bff`~`f2afd19`),但文档(主设计文档与 README)未同步。同时,在实际 CI/CD 与 Unix 工作流场景中,还存在两类未覆盖的痛点:

1. **CI 守门缺位**:release 分支构建时,需要验证"无 `@internal` 标记残留"才允许出包,但当前只能跑 `--dry-run` 肉眼对比,无机器可读的退出码与精确位置报告。
2. **管道缺位**:Unix 哲学下 `cat file | tool` / `tool < file > out` 是基础范式,当前 markstrip 必须传文件路径,无法接入管道流式处理(CI 中常需 `curl source | markstrip | next-step`)。

### 需求确认(经澄清)

- **`--check` 检测范围**:仅 `@internal` 体系(行/块/docstring 标记);pragma 指令是有意处理指令,不算"未清理违规"
- **`--check` 输出**:详细列表(文件:行:列 + 标记类型 + 内容预览),便于开发者快速定位
- **stdin 触发**:`-` 占位符(显式、与现有"path 必填"语义最小冲突)
- **stdin 语言检测**:优先 `--language` 显式指定,否则内容探测(`plugin.detect(content)`)
- **实现方案**:复用 `warnings` 瞬态通道模式(方案 1),`StripConfig` 加 `markers_found` 字段,插件在删除点回填,引擎复制并入 `StripResult`
- **Markdown 行号**:完整翻译——Markdown 插件将代码块内委托插件记录的相对行号翻译为 .md 文件绝对行号

## 目标

1. 新增 `--check` CLI flag,扫描文件/目录/stdin 中的 `@internal` 标记,输出详细位置列表到 stderr,退出码 0(无标记)/1(有标记)
2. 新增 `-` 占位符触发 stdin 模式,清理后内容输出到 stdout,警告与标记输出到 stderr
3. 扩展 `StripResult` 与 `StripConfig`,加 `markers_found` 瞬态通道(复用 warnings 模式)
4. Markdown 插件将代码块内委托插件的 markers_found 行号翻译为 .md 绝对行号
5. 同步 v1.2 pragma 指令功能到 `docs/markstrip-design.md` 与 `README.md`(当前文档完全缺失该章节)
6. 同步本设计(v1.3 `--check` + stdin)到上述文档

## 非目标(YAGNI)

本期**不实现**:

- `--check` 检测 `# markstrip:` pragma 指令(pragma 是有意指令,不算违规;如需严格检查 release 无 markstrip 痕迹,后续可加 `--strict` 切换)
- `--check` 报告块内 collateral 代码行(块定界 `@internal-start/end` 整体删除的块内代码行不是 marker,不报告)
- stdin 模式支持 `--recursive`(stdin 是单流,无递归概念)
- stdin 模式无 path 且无 `-` 时自动检测 tty 进入 stdin(用户已选择显式 `-` 占位符,不做隐式触发)
- `--config` 配置文件、`--ignore` 忽略规则(列入后续方向)
- `--check` 输出 JSON/SARIF 等机器可读格式(本期仅人类可读文本;机器可读格式后续可加 `--format json`)
- 新语言插件(JS/Java/C++;列入后续方向)

## 功能 A:`--check` 模式

### 触发与语义

新增 CLI flag `--check`(布尔标志):

```bash
markstrip source.py --check                 # 单文件检查
markstrip src/ --recursive --check          # 递归检查目录
cat file.py | markstrip --check -            # stdin 检查
markstrip src/ --recursive --check --verbose # 详细输出
```

**语义**:
- `--check` 蕴含 selective 模式(`--check` 即"检查 selective 模式会删除的标记")
- 与 `--mode full` 互斥:同时传 `--check --mode full` 报错退出 2(参数冲突)
- 不修改文件(等价于 `--dry-run` 的"不改文件"语义,但额外输出标记列表)
- 与 `--dry-run` 可共存(均不修改文件,`--check` 额外输出标记);典型用法仅传 `--check`
- 与 `--output` 互斥:`--check` 不写文件,同时传报错退出 2(参数冲突)

### 检测范围

仅 `@internal` 体系(`# markstrip:` pragma 指令不算违规):

| 标记类型 | 检测条件 | 报告行 |
|---------|---------|--------|
| 行标记 | `# @internal ...` 含 line_marker | 该行 |
| 块定界起始 | `# @internal-start` 定界行 | 该定界行 |
| 块定界结束 | `# @internal-end` 定界行 | 该定界行 |
| docstring 整体 | docstring 内首行(或任意行)含 `@internal-docstring` | docstring 起始行 |
| docstring 逐行 | docstring 内行首含 `@internal` | 该行 |
| 块内 collateral 代码行 | 块定界区间内的代码/普通注释行 | **不报告**(非 marker) |
| pragma 指令 | `# markstrip: full` / `full-start` / `full-end` | **不报告**(有意指令) |
| 自定义 marker | `config.custom_markers` 命中 | 该行 |

**关键语义**:--check 报告的是开发者 intentional 写下的标记,而非"被 strip 删除的所有行"。这与 diff-based 方案有本质区别——块定界会连带删除块内代码行,但那些代码行不是 marker,不应误报。

### API 扩展(方案 1:瞬态通道)

#### 新增 `MarkerLocation` 数据结构

```python
# core/result.py
@dataclass
class MarkerLocation:
    """检测到的标记位置(用于 --check 输出)。"""
    line: int              # 1-based 行号(文件绝对行号)
    col: int               # 0-based 列号(标记起点)
    marker_type: str       # "line" | "block-start" | "block-end"
                           #  | "docstring-whole" | "docstring-line"
    marker_text: str       # 命中的标记文本(如 "@internal" / "@internal-start"
                           #  / "@internal-docstring" / 自定义 marker 串)
                           #  用于 --check 输出格式 `{marker_text} ({marker_type})`
    content_preview: str   # 标记所在行内容预览(截断至 80 字符,便于定位)
```

#### `StripConfig` 加瞬态字段

```python
# core/config.py
@dataclass
class StripConfig:
    # ... 现有字段不变 ...
    markers_found: list[MarkerLocation] = field(default_factory=list)
    check_mode: bool = False  # 瞬态,非用户配置;--check 时引擎设 True
```

**`markers_found` 语义**(与 `warnings` 完全对称):
- 非用户配置字段,由引擎每次调用插件前 `clear()`
- 插件在 `strip_selective` 的删除点回填
- 引擎调用后 `list(config.markers_found)` 复制并入 `StripResult.markers_found`
- 须复制而非引用,避免下一次调用 `clear()` 误清空上一个结果

**`check_mode` 语义**(瞬态,由引擎设置,非用户配置):
- `--check` 时引擎设 `config.check_mode = True`,普通 strip 调用为 `False`(默认)
- 插件 `strip_selective` 检测 `config.check_mode`:
  - **跳过 file-level pragma 委托**:不调用 `strip_full`,继续走 selective 扫描路径(确保 file-level pragma 文件内的 @internal 仍被扫描)
  - **跳过 in_pragma 分支**:COMMENT token 在 pragma 区间内时,不优先按 full 逻辑删除,而是 fall through 到 `_has_marker` 检查(确保 pragma 区间内的 @internal 仍被报告)
- 效果:`--check` 报告源代码中所有 @internal 标记,不受 pragma 影响(符合"检查源代码标记卫生"语义)

#### `StripResult` 加字段

```python
# core/result.py
@dataclass
class StripResult:
    cleaned_content: str
    removed_count: int
    detected_language: str = ""
    warnings: list[str] = field(default_factory=list)
    markers_found: list[MarkerLocation] = field(default_factory=list)
```

向后兼容:新字段默认空列表,旧代码不受影响。

#### 公共 API 导出

```python
# __init__.py __all__ 追加
"MarkerLocation",
```

### 插件回填点

#### Python 插件(`languages/python_plugin.py`)

在 `strip_selective` 中,4 个回填点(每个 `MarkerLocation` 均需回填 `marker_text`,取实际命中的标记字符串):

1. **块定界扫描后**(`scan_blocks` 返回 `BlockScanResult` 后):
   - 对每个 `BlockRange`,回填两个 `MarkerLocation`:
     - `(start_line, col_of_marker, "block-start", block_start_marker_text, line_preview)`
     - `(end_line, col_of_marker, "block-end", block_end_marker_text, line_preview)`
   - 列号取定界行中 marker 起始列(可由 `re.match().start()` 计算)
   - `marker_text` 取 `config.effective_block_start()` / `effective_block_end()`(支持自定义 marker)

2. **`_has_marker` 命中点**(COMMENT token 遍历,块外逐行分支):
   - 回填 `(tok.start[0], tok.start[1], "line", matched_marker_text, line_preview)`
   - `matched_marker_text` 从 `_has_marker` 命中的实际 marker 串取(可能是 `line_marker` 或 `custom_markers` 中之一)
   - 仅在"块外 + 非 pragma 区间 + `_has_marker` 命中"分支回填

3. **`_process_docstring` 整体标记**(`has_whole_marker` 分支):
   - 回填 `(tok.start[0], tok.start[1], "docstring-whole", docstring_marker_text, docstring_first_line_preview)`
   - `marker_text` 取 `config.effective_docstring_marker()`

4. **`_process_docstring` 逐行标记**(`for i, line in enumerate(doc_lines)` 分支):
   - 回填 `(source_line, col, "docstring-line", matched_marker_text, line_preview)`
   - `source_line = tok.start[0] + i`
   - `marker_text` 取命中的实际 marker 串(`line_marker` 或 `custom_markers` 之一)

#### Markdown 插件(`languages/markdown_plugin.py`)

**HTML 注释标记**(selective 模式 `_process_html_comments` 中,含 `line_marker` 的 HTML 注释):
- 直接回填 .md 文件绝对行号(由 `HTML_COMMENT_RE` 的 match 位置计算)

**代码块内委托插件**(`_process_code_blocks` 中,委托 Python/兜底插件处理代码块):
- 委托插件回填的 `MarkerLocation.line` 是**代码块内相对行号**(1-based 从代码块首行算)
- Markdown 插件在委托返回后,**翻译行号**为 .md 文件绝对行号:

```python
def process_block(match: re.Match) -> str:
    fence = match.group("fence")
    lang = match.group("lang").lower()
    code = match.group("code")

    # 委托前记录 markers_found 长度,以便切片
    pre_count = len(config.markers_found)
    cleaned = plugin.strip_selective(code, config)  # 或 strip_full
    # 取出本次委托新增的 markers
    new_markers = config.markers_found[pre_count:]

    # 计算代码块在 .md 内容中的起始行(1-based)
    block_start_in_md = content[:match.start()].count("\n") + 1
    # 代码块内容的首行偏移:`{fence}{lang}\n` 之后第一行
    # new_markers.line 是相对 code 的 1-based 行号
    # .md 绝对行号 = block_start_in_md + (代码块首行在 .md 中的相对位置) + (marker.line - 1)
    # 简化:code 首行在 .md 中的行号 = block_start_in_md + 1(fence 行后)
    code_first_line_in_md = block_start_in_md + 1
    for m in new_markers:
        m.line = code_first_line_in_md + (m.line - 1)

    # _fallback_strip 同样适用此翻译
    return f"{fence}{lang}\n{cleaned}{fence}"
```

**关键约束**:委托插件时,`config.markers_found` 是共享列表(瞬态通道)。Markdown 插件在多次委托(多个代码块)间,需要每次委托前后记录长度切片,以便对每段做行号翻译。最终由引擎统一 `list(config.markers_found)` 复制并入结果。

#### 兜底语言插件(`_fallback_strip`)

兜底语言(yaml/bash/js 等)的 `--check` 同样需要回填:
- 块定界扫描后回填 block-start/block-end
- `full_re.match` 命中点回填 "line" 类型
- 行号是兜底代码块内相对行号,由 Markdown 插件的翻译逻辑统一处理

### 引擎调度

```python
# core/engine.py
def strip(self, content, *, language=None, filename=None, mode="selective",
          config=None, check_mode=False) -> StripResult:
    config = config or StripConfig()
    # ... 解析 plugin ...
    config.warnings.clear()
    config.markers_found.clear()       # 新增:清空瞬态通道
    config.check_mode = check_mode     # 新增:传递 check 模式标志
    # ... 调用 plugin.strip_selective / strip_full ...
    return StripResult(
        cleaned_content=cleaned,
        removed_count=removed_count,
        detected_language=plugin.name,
        warnings=list(config.warnings),
        markers_found=list(config.markers_found),  # 新增:复制并入
    )
```

**公共 API**:在 `strip()` 与 `strip_file()` / `strip_directory()` 加 `check_mode: bool = False` 关键字参数(向后兼容,默认 False)。CLI `--check` 时传 `check_mode=True`。

**注意**:`markers_found` 仅在 selective 模式有语义(full 模式删除所有注释,无"标记"概念,不回填;`--mode full` + `--check` 已在 CLI 层互斥拦截)。`check_mode=True` 时插件跳过 pragma 委托与 in_pragma 分支,确保所有 @internal 都被扫描。

### CLI 输出格式

`--check` 扫描后输出到 stderr(便于 stdout 重定向 cleaned 内容时仍可见):

```
src/main.py:12:5  @internal (line)         # @internal 使用 TensorRT 加速
src/main.py:45:1  @internal-start (block-start)
src/main.py:52:1  @internal-end (block-end)
src/utils.py:8:5  @internal-docstring (docstring-whole)
src/utils.py:20:9  @internal (docstring-line)   @internal native worker 使用 solo pool

Found 5 markers in 2 files
```

- 格式:`{path}:{line}:{col}  {marker_text} ({marker_type}){tab}{content_preview}`
- `content_preview` 截断至 80 字符,前导空白 stripped
- 末行汇总:`Found {N} markers in {M} files`(无标记时输出 `No markers found`)
- `--verbose` 时额外输出每个文件的 Processing 行(与现有 verbose 模式一致)

**退出码**:
- 0:无标记
- 1:发现标记(CI 守门用)
- 2:错误(路径不存在、参数冲突等)

### `--check` 与其他参数交互矩阵

| 参数组合 | 行为 |
|---------|------|
| `--check`(单文件) | 扫描,输出标记,exit 0/1 |
| `--check --recursive` | 递归扫描目录,汇总输出 |
| `--check --verbose` | 输出每个文件 Processing 行 + 标记列表 |
| `--check --mode full` | 报错退出 2(check 蕴含 selective) |
| `--check --output FILE` | 报错退出 2(check 不写文件) |
| `--check --dry-run` | 共存,均不修改文件,check 额外输出标记 |
| `--check --marker @private` | 自定义标记同步检测 |
| `--check -`(stdin) | 从 stdin 读,输出标记到 stderr,exit 0/1 |
| `--check - --language python` | stdin + 显式语言 |

## 功能 B:stdin/stdout 管道

### 触发

`path` 参数为 `"-"` 时进入 stdin 模式:

```bash
markstrip - < file.py                       # 基本管道
cat file.py | markstrip - --mode full       # 管道 + full
cat file.py | markstrip --check -           # 管道 + check
markstrip - -o cleaned.py < file.py         # 管道 + 输出到文件
echo '# @internal x\ny=1' | markstrip - --language python
```

**argparse 变更**:`path` 参数保留为位置参数,接受文件路径或 `"-"`。运行时检测 `args.path == "-"` 进入 stdin 模式。

### 语言检测优先级

stdin 模式无 filename,语言解析优先级:

1. `--language` 显式指定(新增 CLI 参数)
2. 内容探测:遍历已注册插件,调用 `plugin.detect(content)` 返回 True 的第一个

**新增 CLI 参数**:

```python
parser.add_argument(
    "--language",
    default=None,
    help="显式指定语言标识符(如 python/markdown),stdin 模式或内容探测失败时使用",
)
```

**`detect()` 实现现状**:
- `LanguagePlugin.detect()` 默认返回 `False`
- `PythonPlugin` 与 `MarkdownPlugin` 当前未实现 `detect()`,需新增:
  - `PythonPlugin.detect(content)`:启发式判断(如行首 `def `/`import `/`from ` 占比、`#` 注释占比)
  - `MarkdownPlugin.detect(content)`:识别 `#` 标题、围栏代码块 ```` ``` ```` 等 Markdown 语法

### 输出流分离

| 输出内容 | 目标流 |
|---------|--------|
| cleaned_content | stdout |
| warnings(每行 `Warning: ...`) | stderr |
| markers_found(--check 时) | stderr |
| Processing 行(--verbose 时) | stderr |
| 错误信息 | stderr |
| 汇总行(--check 时) | stderr |

退出码:0 成功;`--check` 时 1=发现标记;2=参数错误。

### 不支持组合(报错退出 2)

| 组合 | 原因 |
|------|------|
| `- --recursive` | stdin 是单流,无递归 |
| `--check --output FILE` | check 不写文件 |
| `--check --mode full` | check 蕴含 selective |
| `-`(stdin)+ 目录路径 | path 为 `-` 时强制单流 |

## 文档同步范围

### `docs/markstrip-design.md`(主设计文档)

**v1.2 pragma 同步**(已实现但文档缺失):

- 更新记录追加 v1.2 行:`2026-07-17 | v1.2 | 新增 pragma 指令系统(# markstrip: full / full-start / full-end)、pragma_scanner 模块、BlockRange.mode 字段 | Trae AI`
- [包结构](file:///d:/WorkPlace/Pycharm/markstrip/docs/markstrip-design.md)补 `core/pragma_scanner.py` 行
- [标记语法总表](file:///d:/WorkPlace/Pycharm/markstrip/docs/markstrip-design.md)加 3 行:`# markstrip: full` / `full-start` / `full-end`
- 新增 "Pragma 指令系统" 章节(完整描述:语法、识别规则、文件级/区间级行为、CLI 交互矩阵、与 @internal-start/end 的区别、错配处理、warnings 传播)
- Python 插件处理流程([Phase 0~4](file:///d:/WorkPlace/Pycharm/markstrip/docs/markstrip-design.md))补 pragma 检测分支:文件级 pragma → 委托 strip_full;区间级 pragma → mode="comments" 区间内 full 逻辑删注释保留代码
- Markdown 兜底机制([FALLBACK_COMMENT_PREFIX 与 _fallback_strip](file:///d:/WorkPlace/Pycharm/markstrip/docs/markstrip-design.md))补 pragma 接入说明 + `_fallback_full` 方法
- 测试用例覆盖表补 pragma 7 组:`pragma_full` / `pragma_range` / `pragma_range_docstring` / `pragma_mismatched_end` / `pragma_nested` / `pragma_with_selective` / `pragma_in_yaml`

**v1.3 `--check` + stdin 同步**(本设计):

- 更新记录追加 v1.3 行:`2026-07-19 | v1.3 | 新增 --check 模式、stdin/stdout 管道、MarkerLocation 与 markers_found 瞬态通道 | Trae AI`
- 包结构补 `MarkerLocation` 在 `core/result.py` 的位置说明
- 新增 "--check 模式" 章节(触发、检测范围、输出格式、退出码、交互矩阵)
- 新增 "stdin/stdout 管道" 章节(触发、语言检测、输出流分离、不支持组合)
- 标记语法总表无变化(--check/stdin 是 CLI 增强,非新标记类型)
- 测试用例覆盖表补 --check 与 stdin 用例
- 配置数据结构补 `markers_found` 瞬态字段说明
- 结果数据结构补 `MarkerLocation` 与 `StripResult.markers_found`

### `README.md`

**v1.2 pragma 同步**:

- 目录补 "Pragma 指令系统" 节
- 核心特性补:pragma 指令式全量删注释(文件级 + 区间级)
- 标记类型详解表补 3 行:`# markstrip: full` / `full-start` / `full-end`
- 新增 "Pragma 指令系统" 章节(语法示例 + CLI 交互矩阵 + 与 @internal 关系)
- CLI 命令行使用指南补 pragma 典型用法示例
- FAQ 补:pragma 与 @internal 区别;pragma 是否支持嵌套;release 文件该用 pragma 还是 @internal
- 已知限制补:pragma 不支持嵌套、HTML 注释 pragma 不支持
- 后续发展方向:pragma 项移入"已实现(v1.2)"

**v1.3 `--check` + stdin 同步**:

- 目录补 "--check 模式" 与 "stdin/stdout 管道" 节
- 核心特性补:CI 守门 `--check`、stdin 管道
- 标记类型详解无变化
- CLI 命令行使用指南补 `--check` 与 `-` 占位符参数
- Python API 使用指南补 `MarkerLocation` 数据类 + `StripResult.markers_found` 字段
- 新增 "--check 模式" 章节(典型 CI 用法 + 输出示例 + 退出码)
- 新增 "stdin/stdout 管道" 章节(管道示例 + 语言检测 + 输出流分离)
- FAQ 补:--check 检测哪些标记;--check 与 --dry-run 区别;stdin 如何指定语言
- 已知限制补:--check 不报告块内 collateral 代码行;stdin 不支持 --recursive
- 后续发展方向:--check/stdin 项移入"已实现(v1.3)"

### `pyproject.toml`

版本号:`0.1.0` → `0.2.0`(主版本号不变,次版本号 +1 反映新增 CLI 功能)

## 测试策略

### 单元测试

#### `tests/unit/test_engine.py` 追加(或新建 `tests/unit/test_check.py`)

| 用例 | 期望 |
|------|------|
| 单文件无标记 | `result.markers_found == []`,CLI exit 0 |
| 单文件有行标记 | `len(result.markers_found) == 1`,marker_type="line",exit 1 |
| 块定界配对 | 报告 block-start + block-end 两个 marker,不报告块内代码行 |
| docstring 整体标记 | 报告 docstring-whole 在 docstring 起始行 |
| docstring 逐行标记 | 报告 docstring-line 在对应行 |
| 自定义 marker | `--marker @private` 同步识别 |
| 与 pragma 共存 | pragma 指令不算违规,markers_found 不含 pragma 行 |
| 文件级 pragma + 内含 @internal | @internal 仍被报告(check_mode 跳过 file-level 委托) |
| 区间级 pragma 内含 @internal | @internal 仍被报告(check_mode 跳过 in_pragma 优先分支,fall through 到 _has_marker) |
| Markdown HTML 注释标记 | 报告 .md 绝对行号 |
| Markdown 代码块内标记 | 委托插件回填后行号翻译为 .md 绝对行号 |
| 多代码块行号翻译 | 每个代码块的 markers 行号独立翻译,不串号 |

#### `tests/unit/test_python_plugin.py` 追加

- `strip_selective` 回填 markers_found 的 4 个分支覆盖
- `MarkerLocation.content_preview` 截断至 80 字符

#### `tests/unit/test_markdown_plugin.py` 追加

- `_process_code_blocks` 委托后行号翻译正确性
- `_fallback_strip` 兜底语言 markers 回填

### CLI 集成测试(`tests/integration/test_cli.py`)

#### `--check` 测试

| 用例 | 期望 |
|------|------|
| `markstrip clean.py --check` | exit 0,stderr 含 `No markers found` |
| `markstrip marked.py --check` | exit 1,stderr 含 `:line:` 与标记类型 |
| `markstrip src/ --recursive --check` | 多文件汇总 `Found N markers in M files` |
| `markstrip src/ --recursive --check --verbose` | 每文件 Processing 行 + 标记列表 |
| `markstrip src.py --check --mode full` | exit 2,stderr 含参数冲突错误 |
| `markstrip src.py --check --output out.py` | exit 2,stderr 含参数冲突错误 |
| `markstrip src.py --check --marker @private` | 自定义标记同步检测 |
| `markstrip src.py --check --dry-run` | 共存,exit 0/1,无文件修改 |

#### stdin 测试

| 用例 | 期望 |
|------|------|
| `markstrip - < file.py` | stdout = 清理后内容,无文件修改 |
| `cat file.py \| markstrip - --mode full` | stdout = full 模式清理结果 |
| `cat file.py \| markstrip --check -` | stderr 含标记,exit 0/1,stdout 空 |
| `echo '...' \| markstrip - --language python` | 显式语言,内容探测未触发 |
| `markstrip - --recursive` | exit 2,stderr 含"stdin 不支持 --recursive" |
| `markstrip - -o out.py < file.py` | 写入 out.py,stdout 空 |
| `markstrip - < unknown_lang.txt` | 内容探测失败,exit 2 + 警告 |

### 黄金测试

无新增黄金文件(`--check` 与 stdin 是 CLI 层功能,行为由单元 + 集成测试覆盖)。现有 7 组 pragma 黄金测试保持不变(回归)。

### 回归保护

- 现有 106 个测试全过(`markers_found` 默认空,向后兼容)
- `warnings` 瞬态通道行为不变
- `strip()` / `strip_file()` / `strip_directory()` 公共 API 签名不变(只加新字段)

## 数据流

### `--check` 模式数据流

```
markstrip src/ --recursive --check
  → CLI 遍历目录
    → 对每个文件:strip(content, filename=str(path), mode="selective",
                         config, check_mode=True)
      → StripEngine.strip
        → config.warnings.clear()
        → config.markers_found.clear()        # 新增
        → config.check_mode = True            # 新增
        → PythonPlugin.strip_selective(content, config)
          → 检测 check_mode=True → 跳过 file-level pragma 委托
          → scan_blocks(...) → 回填 block-start/end markers
          → scan_full_ranges(...) → 不回填(pragma 不算违规)
          → tokenize COMMENT 遍历:
              in_block → 不回填(已在 scan_blocks 回填定界行)
              in_pragma + check_mode=True → fall through 到 _has_marker
                                          (不优先按 full 删除,确保 @internal 被报告)
              _has_marker 命中 → 回填 "line" marker
          → _process_docstring:
              whole_marker → 回填 "docstring-whole"
              line_marker → 回填 "docstring-line"
        → StripResult(markers_found=list(config.markers_found))  # 新增
  → CLI 收集 result.markers_found,格式化输出到 stderr
  → exit 1 if any markers found
```

**关键**:`check_mode=True` 让插件跳过两处 pragma 优化(file-level 委托、in_pragma 优先删除),确保所有 @internal 标记都走 `_has_marker`/`scan_blocks`/`_process_docstring` 路径被回填。普通 strip 调用 `check_mode=False`,行为不变(pragma 正常生效)。

### stdin 模式数据流

```
markstrip - --language python < file.py
  → CLI 检测 args.path == "-"
  → content = sys.stdin.read()
  → strip(content, language="python", mode="selective", config)
    → StripEngine.strip → PythonPlugin.strip_selective
  → sys.stdout.write(result.cleaned_content)
  → for w in result.warnings: sys.stderr.write(f"Warning: {w}\n")
  → exit 0
```

## 实现要点摘要

1. **[core/result.py](file:///d:/WorkPlace/Pycharm/markstrip/markstrip/core/result.py)**:新增 `MarkerLocation` dataclass + `StripResult.markers_found: list[MarkerLocation]` 字段
2. **[core/config.py](file:///d:/WorkPlace/Pycharm/markstrip/markstrip/core/config.py)**:`StripConfig` 加 `markers_found: list[MarkerLocation]` 瞬态字段 + `check_mode: bool = False` 瞬态字段(语义同 `warnings`)
3. **[core/engine.py](file:///d:/WorkPlace/Pycharm/markstrip/markstrip/core/engine.py)**:`strip()` 加 `check_mode: bool = False` 关键字参数;前置 `config.markers_found.clear()` + `config.check_mode = check_mode`;返回时 `list(config.markers_found)` 复制并入
4. **[markstrip/__init__.py](file:///d:/WorkPlace/Pycharm/markstrip/markstrip/__init__.py)**:`strip()` / `strip_file()` / `strip_directory()` 加 `check_mode` 关键字参数(向后兼容);`__all__` 追加 `"MarkerLocation"`
5. **[languages/python_plugin.py](file:///d:/WorkPlace/Pycharm/markstrip/markstrip/languages/python_plugin.py)**:`strip_selective` 4 个回填点(scan_blocks 后、_has_marker 命中、docstring 整体、docstring 逐行);`check_mode=True` 时跳过 file-level pragma 委托 + 跳过 in_pragma 优先分支;`_fallback_regex_selective` 同步回填与 check_mode 处理
6. **[languages/markdown_plugin.py](file:///d:/WorkPlace/Pycharm/markstrip/markstrip/languages/markdown_plugin.py)**:
   - `_process_html_comments` 回填 HTML 注释标记(.md 绝对行号)
   - `_process_code_blocks` 委托后翻译 markers 行号(.md 绝对行号)
   - `_fallback_strip` 回填兜底语言 markers(由 `_process_code_blocks` 统一翻译)
   - 兜底语言的 `_fallback_strip` 同样检测 `check_mode` 跳过 pragma 委托
7. **[languages/python_plugin.py](file:///d:/WorkPlace/Pycharm/markstrip/markstrip/languages/python_plugin.py) 与 [markdown_plugin.py](file:///d:/WorkPlace/Pycharm/markstrip/markstrip/languages/markdown_plugin.py)**:实现 `detect(content) -> bool` 内容探测方法(stdin 模式用)
8. **[languages/base.py](file:///d:/WorkPlace/Pycharm/markstrip/markstrip/languages/base.py)**:`LanguagePlugin.detect()` 默认实现保持 `return False`(向后兼容)
9. **[cli.py](file:///d:/WorkPlace/Pycharm/markstrip/markstrip/cli.py)**:
   - 新增 `--check` flag + `--language` 参数
   - `path == "-"` 进入 stdin 模式,`sys.stdin.read()` 读内容
   - `--check` 路径:`strip(..., check_mode=True)`,遍历 result.markers_found 输出到 stderr,汇总行,exit 0/1
   - stdin 模式:`sys.stdout.write(cleaned_content)`,warnings 到 stderr
   - 参数冲突检测(`--check --mode full` / `--check --output` / `- --recursive` / `--check - --output`)exit 2
10. **文档同步**:
    - [docs/markstrip-design.md](file:///d:/WorkPlace/Pycharm/markstrip/docs/markstrip-design.md):v1.2 pragma + v1.3 check/stdin 章节
    - [README.md](file:///d:/WorkPlace/Pycharm/markstrip/README.md):v1.2 pragma + v1.3 check/stdin 章节
    - [pyproject.toml](file:///d:/WorkPlace/Pycharm/markstrip/pyproject.toml):`0.1.0` → `0.2.0`
11. **测试**:`--check` 单元(含 check_mode 跳过 pragma 委托/分支)+ CLI 集成 + stdin CLI 集成 + Markdown 行号翻译测试

## 范围边界(YAGNI)

本期**不实现**:

- `--check` 检测 pragma 指令(后续可加 `--strict`)
- `--check` 输出 JSON/SARIF 等机器可读格式(后续可加 `--format json`)
- `--check` 报告块内 collateral 代码行
- stdin 模式无 path 隐式触发(用户已选显式 `-` 占位符)
- `--config` 配置文件
- `--ignore` 忽略规则
- 新语言插件(JS/Java/C++)
- `--check` 缓存/增量模式
- VS Code 扩展 / pre-commit hook
- tree-sitter 集成

## 更新记录

| 日期 | 版本 | 更新内容 | 作者 |
|------|------|----------|------|
| 2026-07-19 | v1.0 | 初始设计:`--check` 模式、stdin/stdout 管道、MarkerLocation 与 markers_found 瞬态通道、Markdown 行号翻译、v1.2/v1.3 文档同步 | Trae AI |
