# markstrip - 标记式选择性注释过滤库设计文档

## 概述

`markstrip` 是一个 Python 库 + CLI 工具，用于选择性过滤源代码和文档中的标记式注释。与市面上所有现有工具（全量注释删除）不同，`markstrip` 支持**标记式选择性过滤**——仅删除带有特定标记（如 `@internal`）的注释，保留其他注释。

### 核心价值

1. **标记式选择性过滤**：仅删除 `@internal` 标记的注释，保留普通注释
2. **块级定界过滤**：`@internal-start` / `@internal-end` 标记可一次性过滤连续的注释区域（含定界行整体删除）
3. **docstring 选择性清理**：支持逐行标记或整体删除文档字符串
4. **Markdown 代码块注释清理**：清理 Markdown 文档中代码块内的标记注释
5. **嵌套代码块删除**：整体删除代码块内的嵌套 ``` 标记对
6. **全量注释删除**（附加功能）：支持删除所有注释，保留 TODO/FIXME/shebang
7. **可扩展语言插件**：当前支持 Python 和 Markdown，可扩展 Java/JS/C++ 等

## 背景与市场调研

### 现有工具调研

| 工具 | 平台 | 核心功能 | 局限性 |
|------|------|---------|--------|
| [uncomment](https://github.com/Goldziher/uncomment) | Rust/CLI | tree-sitter AST 解析，306 语言，保留 TODO/FIXME | 全量删除，无选择性过滤 |
| [comment-bear](https://www.npmjs.com/package/comment-bear) | TypeScript/npm | 80+ 语言，字符串感知，API 设计优秀 | 全量删除，无标记过滤 |
| [comment-remover-cli](https://pypi.org/project/comment-remover-cli/) | Python/PyPI | 20+ 语言，JSON 配置 | 全量删除，无选择性 |
| [py-code-cleaner](https://pypi.org/project/py-code-cleaner/) | Python | 清理注释/docstring/注解 | 全量删除，仅 Python |
| [vexy-python-markdown-steroids](https://pypi.org/project/vexy-python-markdown-steroids/) | Python | Markdown HTML 注释剥离 | 仅 HTML 注释，无代码块处理 |

### 市场空白

**没有任何现有工具支持"标记式选择性注释过滤"** —— 即只过滤带有特定标记的注释，保留其他注释。`markstrip` 填补这一空白。

### 参考借鉴

- `uncomment` 的 tree-sitter 架构思路（精确，不误删字符串中的 `#`）
- `comment-bear` 的 API 设计（`removeComments(code, options)` 返回结果对象）
- `uncomment` 的保留规则（TODO/FIXME/license/linting directives 可配置保留）

## 设计方案：插件注册表 + 策略模式

### 核心设计原则

1. **插件隔离**：每种语言是一个独立插件，实现统一接口，互不依赖
2. **模式可切换**：`selective`（标记过滤）和 `full`（全量删除）两种模式可独立使用
3. **零硬编码**：标记符号通过配置传入，默认值在 `StripConfig`
4. **Markdown 委托机制**：Markdown 插件解析代码块后，委托给对应语言插件处理

### 包结构

```
markstrip/
├── __init__.py              # 公共 API: strip(), strip_file(), strip_directory()
├── core/
│   ├── engine.py            # StripEngine: 主引擎，接受 content + options
│   ├── config.py            # StripConfig: 标记规则配置（可自定义 marker，含 effective_* 派生）
│   ├── block_scanner.py     # scan_blocks(): 块定界扫描纯函数，块语义唯一真理源
│   ├── result.py            # StripResult: 清理结果（cleaned_content, stats, warnings）
│   └── errors.py            # 异常定义
├── languages/
│   ├── base.py              # LanguagePlugin: 抽象基类，定义接口契约
│   ├── registry.py          # LanguageRegistry: 插件注册与查找
│   ├── python_plugin.py     # Python 插件（tokenize + 块定界扫描 + 行级重组）
│   ├── markdown_plugin.py   # Markdown 插件（代码块解析 + 委托 + 块定界兜底）
│   └── _builtin.py          # 内置插件自动注册 + entry_points 发现
├── cli.py                   # CLI 入口
└── py.typed                 # 类型标记
```

> **设计说明**：模式逻辑（selective/full）内嵌在每个插件的 `strip_selective()` 和 `strip_full()` 方法中，无需独立的 modes 模块。块定界语义由 `core/block_scanner.py` 统一提供，Python 插件与 Markdown 兜底共用，确保块语义单一真理源。

## 语言插件接口

```python
# languages/base.py
class LanguagePlugin(ABC):
    """语言插件抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """语言标识符，如 'python', 'markdown'"""

    @property
    @abstractmethod
    def file_extensions(self) -> list[str]:
        """支持的文件扩展名，如 ['.py']"""

    @abstractmethod
    def strip_selective(self, content: str, config: StripConfig) -> str:
        """标记式选择性过滤：仅删除 @internal 标记的注释"""

    @abstractmethod
    def strip_full(self, content: str, config: StripConfig) -> str:
        """全量注释删除：删除所有注释"""

    def detect(self, content: str) -> bool:
        """检测内容是否属于该语言（可选实现）"""
        return False
```

### 配置数据结构

```python
# core/config.py
@dataclass
class StripConfig:
    """清理配置"""
    line_marker: str = "@internal"              # 行级标记
    docstring_marker: str = ""                   # 空→自动派生为 f"{line_marker}-docstring"
    block_start_marker: str = ""                 # 空→自动派生为 f"{line_marker}-start"
    block_end_marker: str = ""                   # 空→自动派生为 f"{line_marker}-end"
    preserve_docstrings: bool = True             # full 模式下是否保留 docstring
    preserve_todo: bool = True                   # full 模式下是否保留 TODO/FIXME
    custom_markers: list[str] = field(default_factory=list)  # 自定义额外标记
    warnings: list[str] = field(default_factory=list)  # 引擎瞬态回填通道（非用户配置）

    def effective_docstring_marker(self) -> str: ...  # 空则从 line_marker 派生
    def effective_block_start(self) -> str: ...        # 空则从 line_marker 派生
    def effective_block_end(self) -> str: ...          # 空则从 line_marker 派生
```

> **标记派生**：`docstring_marker` / `block_start_marker` / `block_end_marker` 默认为空字符串，运行时通过 `effective_*()` 方法从 `line_marker` 派生，实现"改一处 `line_marker`，全套标记联动"。显式赋值则覆盖派生值。

> **warnings 通道**：`warnings` 字段非用户配置，由 `StripEngine` 在每次调用插件前 `clear()`，插件回填，引擎复制后并入 `StripResult.warnings`，避免跨调用状态泄漏。

### 结果数据结构

```python
# core/result.py
@dataclass
class StripResult:
    """清理结果"""
    cleaned_content: str        # 清理后的内容
    removed_count: int          # 删除的行数
    detected_language: str = "" # 检测到的语言
    warnings: list[str] = field(default_factory=list)  # 警告信息
```

## Python 插件设计

Python 插件采用 **tokenize 精确定位 + 行级重组** 的混合策略。

### 处理流程

```
源代码
  ↓
Phase 0: 块定界扫描
  → scan_blocks() 识别 @internal-start / @internal-end 包裹的块范围
  → 块内所有行（含定界行、纯注释、代码）整体标记为待剔除
  → 错配（嵌套/未闭合/无匹配）写入 warnings
  ↓
Phase 1: tokenize 词法分析
  → 精确识别 COMMENT token 和 STRING token 的位置
  → 避免误删字符串中的 # 符号
  ↓
Phase 2: 注释处理
  → selective 模式: 仅删除含 @internal 标记的 COMMENT（块内行整体跳过）
  → full 模式: 删除所有 COMMENT token（保留 shebang/编码声明/coding cookie）
  ↓
Phase 3: 文档字符串处理
  → 识别 STRING token 中为 docstring 的（模块/类/函数首语句）
  → 检查 @internal-docstring → 整体删除
  → 检查 @internal 逐行 → 整行删除标记行
  → full 模式 + preserve_docstrings=False → 删除所有 docstring
  ↓
Phase 4: 行级重组
  → 按行号映射，构建清理后的代码，块范围行整体剔除
```

### 为什么用 tokenize 而非纯正则

```python
# 正则会误删的情况：
url = "https://example.com/path#fragment"  # 正则会误删这行

# tokenize 精确识别：
# Token(type=COMMENT, string='# 注释')  ← 会被处理
# Token(type=STRING, string='"https://..."')  ← 不会被触碰
```

### 关键实现逻辑

```python
# languages/python_plugin.py
class PythonPlugin(LanguagePlugin):

    @property
    def name(self) -> str:
        return "python"

    @property
    def file_extensions(self) -> list[str]:
        return [".py", ".pyw", ".pyi"]

    def strip_selective(self, content: str, config: StripConfig) -> str:
        """标记式选择性过滤"""
        lines = content.splitlines(keepends=True)
        remove_ranges = []  # 需要删除的行范围

        # Phase 1+2: tokenize 识别注释
        try:
            tokens = list(tokenize.tokenize(
                iter(content.encode().splitlines(True)).__next__
            ))
        except tokenize.TokenizeError:
            # 语法错误时回退到正则
            return self._fallback_regex_selective(content, config)

        for tok in tokens:
            if tok.type == tokenize.COMMENT:
                # 检查注释是否包含标记
                if self._has_marker(tok.string, config):
                    remove_ranges.append((tok.start[0], tok.end[0]))

            if tok.type == tokenize.STRING:
                # 检查是否为 docstring 并处理
                if self._is_docstring(tok, tokens):
                    doc_ranges = self._process_docstring(
                        tok, config
                    )
                    remove_ranges.extend(doc_ranges)

        # Phase 4: 行级重组
        return self._rebuild(lines, remove_ranges)

    def strip_full(self, content: str, config: StripConfig) -> str:
        """全量注释删除"""
        lines = content.splitlines(keepends=True)
        remove_ranges = []

        tokens = list(tokenize.tokenize(
            iter(content.encode().splitlines(True)).__next__
        ))

        for tok in tokens:
            if tok.type == tokenize.COMMENT:
                # 保留 shebang 和编码声明
                if self._is_preserved_comment(tok, config):
                    continue
                remove_ranges.append((tok.start[0], tok.end[0]))

            if tok.type == tokenize.STRING and self._is_docstring(tok, tokens):
                if not config.preserve_docstrings:
                    remove_ranges.append((tok.start[0], tok.end[0]))

        return self._rebuild(lines, remove_ranges)
```

### docstring 处理细节

```python
def _process_docstring(self, tok, config: StripConfig) -> list[tuple]:
    """处理单个 docstring，返回需删除的行范围"""
    content = ast.literal_eval(tok.string)  # 安全解析字符串内容
    lines = content.split('\n')

    # 检查 @internal-docstring 标记（整体删除）
    first_line = lines[0].strip() if lines else ""
    if first_line.startswith(config.docstring_marker):
        return [(tok.start[0], tok.end[0])]  # 删除整个 docstring

    # 逐行检查 @internal 标记
    marked_lines = []
    for i, line in enumerate(lines):
        if line.strip().startswith(config.line_marker):
            # 映射到源文件行号
            source_line = tok.start[0] + i
            marked_lines.append((source_line, source_line))

    return marked_lines
```

### 保留规则（full 模式）

```python
def _is_preserved_comment(self, tok, config: StripConfig) -> bool:
    """判断注释是否应被保留"""
    text = tok.string.strip()
    # 保留 shebang
    if text.startswith("#!"):
        return True
    # 保留编码声明
    if "coding:" in text or "coding=" in text:
        return True
    # 保留 TODO/FIXME
    if config.preserve_todo and ("TODO" in text or "FIXME" in text):
        return True
    # 保留类型注释
    if text.startswith("# type:"):
        return True
    return False
```

### 语法错误回退

```python
def _fallback_regex_selective(self, content: str, config: StripConfig) -> str:
    """tokenize 失败时的正则回退"""
    # 先用 scan_blocks 识别块范围并整体剔除
    # 再用 (?:\s|$) 边界匹配删除散落的 @internal 行注释
    ...
```

> **注意**：正则回退路径同样接入 `scan_blocks`，确保块定界语义在 tokenize 不可用时保持一致。

## 块定界扫描器设计

`core/block_scanner.py` 是块语义的**唯一真理源**，Python 插件与 Markdown 兜底共用，避免语义漂移。

### 核心数据结构

```python
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
```

### 定界行正则

```python
def _build_delimiter_regex(comment_prefix: str, marker: str) -> re.Pattern:
    r"""构造定界行正则：^\s*{prefix}\s*{marker}(?:\s|$)。

    要求标记后紧跟空白或行尾，避免 @internal-started 等伪前缀误匹配。
    """
    return re.compile(
        rf"^\s*{re.escape(comment_prefix)}\s*{re.escape(marker)}(?:\s|$)"
    )
```

### scan_blocks 扫描算法

```python
def scan_blocks(
    lines: list[str],
    comment_prefix: str,   # "#" 或 "//"
    start_marker: str,
    end_marker: str,
) -> BlockScanResult:
    """单趟扫描，严格容错，不支持嵌套。"""
    # 遇到 start：若已 open → 视为错配并警告；否则记录 open_start
    # 遇到 end：若无 open_start → 视为错配并警告；否则配对成 BlockRange
    # 扫描结束若仍 open → 警告"缺少匹配 end"
```

**语义要点**：

| 场景 | 行为 |
|------|------|
| 正常配对 `start ... end` | `BlockRange(start, end)`，含两端定界行整体剔除 |
| 嵌套 `start ... start ... end` | 内层 start 视为错配并忽略 + 警告 |
| 孤立 `end`（无 start） | 忽略 + 警告 |
| 未闭合 `start`（至 EOF） | 忽略该块 + 警告 |

## Markdown 插件设计

Markdown 插件是特殊的"容器插件"——它解析代码块后委托给对应语言插件处理。

### 处理流程

```
Markdown 源文档
  ↓
Phase 1: 解析围栏代码块
  → 识别 ```language ... ``` 结构
  → 提取语言标识符和代码内容
  ↓
Phase 2: 嵌套代码块处理
  → 识别代码块内的 ``` 标记对
  → 删除嵌套标记及其内容（整体删除）
  → selective 模式: 直接删除嵌套块
  → full 模式: 直接删除嵌套块
  ↓
Phase 3: 委托语言插件
  → 根据 language 标识符查找对应插件
  → 调用插件 strip_selective() 或 strip_full()
  → 替换原始代码块内容
  ↓
Phase 4: HTML 注释处理（可选）
  → full 模式: 删除 <!-- ... --> 注释
  → selective 模式: 删除含 @internal 的 HTML 注释
  ↓
Phase 5: 重组文档
```

### 关键实现逻辑

```python
# languages/markdown_plugin.py
class MarkdownPlugin(LanguagePlugin):

    def __init__(self, registry: LanguageRegistry):
        self._registry = registry

    @property
    def name(self) -> str:
        return "markdown"

    @property
    def file_extensions(self) -> list[str]:
        return [".md", ".markdown"]

    def strip_selective(self, content: str, config: StripConfig) -> str:
        """标记式选择性过滤"""
        # Phase 1+2: 处理代码块
        content = self._process_code_blocks(content, config, mode="selective")

        # Phase 4: 处理 HTML 注释中的 @internal
        content = self._process_html_comments(content, config, mode="selective")

        return content

    def strip_full(self, content: str, config: StripConfig) -> str:
        """全量注释删除"""
        # Phase 1+2: 处理代码块
        content = self._process_code_blocks(content, config, mode="full")

        # Phase 4: 删除所有 HTML 注释
        content = self._process_html_comments(content, config, mode="full")

        return content
```

### 代码块处理核心

```python
# 代码块正则：匹配 ```language\n...\n```
CODE_BLOCK_RE = re.compile(
    r'(?P<fence>```+)(?P<lang>\w*)\n(?P<code>.*?)```',
    re.DOTALL
)

def _process_code_blocks(
    self, content: str, config: StripConfig, mode: str
) -> str:
    """处理所有围栏代码块"""

    def process_block(match: re.Match) -> str:
        fence = match.group("fence")
        lang = match.group("lang").lower()
        code = match.group("code")

        # Phase 2: 删除嵌套代码块（``` ... ``` 整体删除）
        code = self._remove_nested_blocks(code, fence)

        # Phase 3: 委托给语言插件
        plugin = self._registry.get_plugin(lang)
        if plugin is not None:
            if mode == "selective":
                cleaned = plugin.strip_selective(code, config)
            else:
                cleaned = plugin.strip_full(code, config)
            return f"{fence}{lang}\n{cleaned}```"

        # 未知语言：正则兜底
        cleaned = self._fallback_strip(code, lang, config)
        return f"{fence}{lang}\n{cleaned}```"

    return CODE_BLOCK_RE.sub(process_block, content)
```

### 嵌套代码块处理

```python
# 嵌套代码块：代码块内的 ``` 标记对
NESTED_BLOCK_RE = re.compile(r'```\n.*?```\n?', re.DOTALL)

def _remove_nested_blocks(self, code: str, outer_fence: str) -> str:
    """删除代码块内的嵌套 ``` 标记对及其内容"""
    cleaned = NESTED_BLOCK_RE.sub('', code)
    return cleaned
```

### HTML 注释处理

```python
HTML_COMMENT_RE = re.compile(r'<!--.*?-->', re.DOTALL)

def _process_html_comments(
    self, content: str, config: StripConfig, mode: str
) -> str:
    """处理 HTML 注释"""
    if mode == "full":
        # 全量删除所有 HTML 注释
        return HTML_COMMENT_RE.sub('', content)

    # selective: 仅删除含 @internal 的 HTML 注释
    def filter_comment(match: re.Match) -> str:
        comment = match.group(0)
        if config.line_marker in comment:
            return ''
        return comment

    return HTML_COMMENT_RE.sub(filter_comment, content)
```

### 委托机制示意

```
Markdown 文档
    |
    +- ```python ------> PythonPlugin.strip_selective()
    |   # @internal      ->  删除
    |   code = "..."     ->  保留
    |   ```
    |   嵌套注释          ->  整体删除
    |   ```
    |   ```
    |
    +- ```javascript ---> JavaScriptPlugin.strip_selective()
    |   // @internal     ->  删除
    |   ```
    |
    +- ```yaml ----------> (无对应插件，正则兜底 + 块定界扫描)
    # @internal-start ->  块定界扫描
    # @internal        ->  正则删除
    # @internal-end    ->  块定界扫描
    ```
```

### 兜底机制

对于未注册语言（如 YAML、Bash），Markdown 插件使用正则兜底，并接入 `scan_blocks` 统一块语义：

```python
# 按注释语法定义前缀，运行时用于 scan_blocks 与散落行注释匹配
FALLBACK_COMMENT_PREFIX = {
    "yaml": "#", "bash": "#", "shell": "#",
    "javascript": "//", "java": "//", "c": "//", "cpp": "//",
}

def _fallback_strip(self, code: str, lang: str, config: StripConfig) -> str:
    """无对应插件时的正则兜底：先 scan_blocks 剔除块，再按边界匹配删散落行注释"""
    prefix = FALLBACK_COMMENT_PREFIX.get(lang)
    if prefix is None:
        return code
    lines = code.splitlines(keepends=True)
    # Phase 1: 块定界扫描
    scan = scan_blocks(lines, prefix, config.effective_block_start(), config.effective_block_end())
    # Phase 2: 块内行整体剔除；块外散落 @internal 行注释按 (?:\s|$) 边界删除
    ...
    # 回填 warnings 到 config.warnings
    config.warnings.extend(scan.warnings)
    return rebuilt_code
```

## 核心引擎与公共 API

### 引擎调度流程

```
用户调用 strip(content, language="python", mode="selective")
    ↓
StripEngine
    ↓
LanguageRegistry.get_plugin("python") -> PythonPlugin
    ↓
Plugin.strip_selective(content, config) -> cleaned_content
    ↓
StripResult(cleaned_content, removed_count, ...)
```

### LanguageRegistry

```python
# languages/registry.py
class LanguageRegistry:
    """语言插件注册表"""

    def __init__(self):
        self._plugins: dict[str, LanguagePlugin] = {}
        self._extension_map: dict[str, str] = {}  # ".py" -> "python"

    def register(self, plugin: LanguagePlugin) -> None:
        """注册语言插件"""
        self._plugins[plugin.name] = plugin
        for ext in plugin.file_extensions:
            self._extension_map[ext] = plugin.name

    def get_plugin(self, name: str) -> LanguagePlugin | None:
        """按语言名查找插件"""
        return self._plugins.get(name.lower())

    def get_plugin_by_extension(self, ext: str) -> LanguagePlugin | None:
        """按文件扩展名查找插件"""
        name = self._extension_map.get(ext)
        if name:
            return self._plugins.get(name)
        return None

    def list_languages(self) -> list[str]:
        """列出所有已注册语言"""
        return list(self._plugins.keys())
```

### StripEngine

```python
# core/engine.py
class StripEngine:
    """主引擎：调度插件执行清理"""

    def __init__(self, registry: LanguageRegistry | None = None):
        self._registry = registry or _create_default_registry()

    def strip(
        self,
        content: str,
        *,
        language: str | None = None,
        filename: str | None = None,
        mode: str = "selective",
        config: StripConfig | None = None,
    ) -> StripResult:
        """清理内容"""
        config = config or StripConfig()

        # 语言检测优先级：显式指定 > 文件扩展名 > 内容探测
        plugin = self._resolve_plugin(language, filename, content)
        if plugin is None:
            return StripResult(
                cleaned_content=content,
                removed_count=0,
                warnings=["无法识别语言，跳过处理"],
            )

        # 执行清理
        original_len = len(content.splitlines())
        config.warnings.clear()  # 清空瞬态通道，避免跨调用泄漏
        if mode == "full":
            cleaned = plugin.strip_full(content, config)
        else:
            cleaned = plugin.strip_selective(content, config)
        cleaned_len = len(cleaned.splitlines())

        return StripResult(
            cleaned_content=cleaned,
            removed_count=original_len - cleaned_len,
            detected_language=plugin.name,
            warnings=list(config.warnings),  # 复制副本，避免后续修改影响结果
        )

    def _resolve_plugin(
        self, language: str | None, filename: str | None, content: str
    ) -> LanguagePlugin | None:
        """按优先级解析插件"""
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

### 公共 API

```python
# __init__.py
from .core.engine import StripEngine
from .core.config import StripConfig
from .core.result import StripResult
from .languages.base import LanguagePlugin
from .languages.registry import LanguageRegistry

# 默认引擎实例（内置插件已注册）
_default_engine = StripEngine()

def strip(
    content: str,
    *,
    language: str | None = None,
    filename: str | None = None,
    mode: str = "selective",         # "selective" | "full"
    config: StripConfig | None = None,
) -> StripResult:
    """清理内容中的标记注释"""
    return _default_engine.strip(
        content, language=language, filename=filename,
        mode=mode, config=config,
    )

def strip_file(
    path: str | Path,
    *,
    mode: str = "selective",
    config: StripConfig | None = None,
    inplace: bool = False,
) -> StripResult:
    """清理文件"""
    path = Path(path)
    content = path.read_text(encoding="utf-8")
    result = _default_engine.strip(
        content, filename=str(path), mode=mode, config=config,
    )
    if inplace:
        path.write_text(result.cleaned_content, encoding="utf-8")
    return result

def strip_directory(
    path: str | Path,
    *,
    mode: str = "selective",
    config: StripConfig | None = None,
    extensions: list[str] | None = None,
    inplace: bool = False,
) -> list[StripResult]:
    """批量清理目录下所有支持的文件"""
    path = Path(path)
    results = []
    for file_path in path.rglob("*"):
        if file_path.is_file():
            if extensions and file_path.suffix not in extensions:
                continue
            result = strip_file(
                file_path, mode=mode, config=config, inplace=inplace
            )
            results.append(result)
    return results

def register_plugin(plugin: LanguagePlugin) -> None:
    """注册自定义语言插件"""
    _default_engine._registry.register(plugin)
```

### CLI 设计

```bash
# 标记式选择性过滤（默认）
markstrip app/main.py
markstrip docs/guide.md

# 全量注释删除
markstrip app/main.py --mode full

# 批量处理目录
markstrip src/ --recursive

# 自定义标记
markstrip app/main.py --marker "@private"

# 块级定界过滤（默认 @internal-start / @internal-end）
markstrip app/main.py

# 自定义块定界标记（成对使用）
markstrip app/main.py --marker @private --block-start-marker @private-start --block-end-marker @private-end

# 预览模式（不修改文件）
markstrip app/main.py --dry-run

# 输出到指定文件
markstrip app/main.py --output cleaned_main.py

# 保留 docstring（full 模式下）
markstrip app/main.py --mode full --preserve-docstrings

# 显示统计信息与警告
markstrip src/ --recursive --verbose
# 输出:
# Processing src/main.py... removed 15 lines
# Warning: 行 12: 嵌套 @internal-start，已忽略
# Processing src/utils.py... removed 3 lines
# Total: 18 lines removed from 2 files
```

```python
# cli.py
def main():
    parser = argparse.ArgumentParser(
        prog="markstrip",
        description="标记式选择性注释过滤工具",
    )
    parser.add_argument("path", help="文件或目录路径")
    parser.add_argument(
        "--mode", choices=["selective", "full"], default="selective"
    )
    parser.add_argument(
        "--marker", default="@internal", help="行级标记符号"
    )
    parser.add_argument(
        "--docstring-marker", default="",
        help="空则自动派生为 {marker}-docstring",
    )
    parser.add_argument(
        "--block-start-marker", default="",
        help="空则自动派生为 {marker}-start",
    )
    parser.add_argument(
        "--block-end-marker", default="",
        help="空则自动派生为 {marker}-end",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="预览不修改"
    )
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument(
        "--recursive", "-r", action="store_true", help="递归处理目录"
    )
    parser.add_argument(
        "--preserve-docstrings", action="store_true"
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    config = StripConfig(
        line_marker=args.marker,
        docstring_marker=args.docstring_marker,
        block_start_marker=args.block_start_marker,
        block_end_marker=args.block_end_marker,
        preserve_docstrings=args.preserve_docstrings,
    )

    # ... 执行清理逻辑，--verbose 时输出 result.warnings 到 stderr
```

## 扩展性设计

### 方式 1：代码内注册

```python
from markstrip import register_plugin, LanguagePlugin, StripConfig
import re

class JavaScriptPlugin(LanguagePlugin):
    """自定义 JavaScript 插件"""

    @property
    def name(self) -> str:
        return "javascript"

    @property
    def file_extensions(self) -> list[str]:
        return [".js", ".jsx", ".mjs"]

    def strip_selective(self, content: str, config: StripConfig) -> str:
        # 删除 // @internal 和 /* @internal */ 注释
        marker = re.escape(config.line_marker)
        pattern = rf'^\s*//\s*{marker}.*$\n?'
        content = re.sub(pattern, '', content, flags=re.MULTILINE)

        block_pattern = rf'/\*[^*]*{marker}.*?\*/'
        content = re.sub(block_pattern, '', content, flags=re.DOTALL)
        return content

    def strip_full(self, content: str, config: StripConfig) -> str:
        # 删除所有 // 注释和 /* */ 块注释
        content = re.sub(r'^\s*//.*$\n?', '', content, flags=re.MULTILINE)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        return content

# 注册插件
register_plugin(JavaScriptPlugin())
```

### 方式 2：entry_points 自动发现

```toml
# pyproject.toml (第三方包)
[project.entry-points."markstrip.plugins"]
javascript = "my_package.js_plugin:JavaScriptPlugin"
java = "my_package.java_plugin:JavaPlugin"
cpp = "my_package.cpp_plugin:CppPlugin"
```

```python
# languages/_builtin.py 中的自动发现逻辑
def _discover_entry_point_plugins() -> list[LanguagePlugin]:
    """通过 entry_points 自动发现第三方插件"""
    plugins = []
    if sys.version_info >= (3, 10):
        eps = importlib.metadata.entry_points(group="markstrip.plugins")
    else:
        eps = importlib.metadata.entry_points().get(
            "markstrip.plugins", []
        )

    for ep in eps:
        try:
            plugin_class = ep.load()
            plugins.append(plugin_class())
        except Exception as e:
            warnings.warn(f"加载插件 {ep.name} 失败: {e}")
    return plugins
```

### 语言插件开发指南

| 关注点 | 说明 |
|--------|------|
| `#` 注释语言 | Python/Ruby/YAML/Bash：使用正则 `^\s*#\s*@internal` 即可 |
| `//` 注释语言 | JS/Java/C++：使用正则 `^\s*//\s*@internal` + 块注释 `/\*@internal.*?\*/` |
| docstring | 仅 Python 有 docstring 概念，其他语言不需要实现 docstring 逻辑 |
| 字符串安全 | 如需精确处理（避免误删字符串中的 `#`），使用该语言的词法分析器 |

## 测试策略

### 测试目录结构

```
tests/
├── unit/
│   ├── test_python_plugin.py       # Python 插件单元测试
│   ├── test_markdown_plugin.py     # Markdown 插件单元测试
│   ├── test_registry.py            # 注册表测试
│   └── test_config.py              # 配置测试
├── integration/
│   ├── test_markdown_delegation.py # Markdown 委托语言插件
│   └── test_cli.py                 # CLI 集成测试
├── golden/                         # 黄金文件测试（输入->期望输出）
│   ├── python/
│   │   ├── internal_comment.py
│   │   ├── internal_comment.expected.py
│   │   ├── docstring_selective.py
│   │   ├── docstring_selective.expected.py
│   │   ├── docstring_whole.py
│   │   ├── docstring_whole.expected.py
│   │   ├── string_with_hash.py
│   │   ├── string_with_hash.expected.py
│   │   └── ...
│   └── markdown/
│       ├── nested_codeblock.md
│       ├── nested_codeblock.expected.md
│       ├── code_block_delegation.md
│       ├── code_block_delegation.expected.md
│       └── ...
└── conftest.py
```

### 黄金文件测试模式

```python
# tests/conftest.py
import pytest
from pathlib import Path

GOLDEN_DIR = Path(__file__).parent / "golden"

def collect_golden_cases(lang: str, suffix: str = ".py"):
    """收集黄金测试用例"""
    cases = []
    lang_dir = GOLDEN_DIR / lang
    for input_file in lang_dir.glob(f"*{suffix}"):
        if input_file.name.endswith(f".expected{suffix}"):
            continue
        expected_file = input_file.with_name(
            input_file.stem + f".expected{suffix}"
        )
        if expected_file.exists():
            cases.append((input_file, expected_file))
    return cases

# tests/unit/test_python_plugin.py
@pytest.mark.parametrize(
    "input_file,expected_file",
    collect_golden_cases("python")
)
def test_python_selective(input_file, expected_file):
    from markstrip import strip
    content = input_file.read_text()
    expected = expected_file.read_text()
    result = strip(content, language="python", mode="selective")
    assert result.cleaned_content == expected
```

### 关键测试用例覆盖

| 场景 | 测试用例 |
|------|---------|
| `# @internal` 行注释 | 标记的删除，未标记的保留 |
| 字符串中的 `#` | `url = "http://x#y"` 不被误删 |
| `@internal-docstring` | 整个 docstring 删除 |
| docstring 内逐行 `@internal` | 标记行整行删除 |
| 块定界 `@internal-start`/`@internal-end` | 块区域整体删除（含定界行与代码行） |
| 块错配：嵌套 start | 内层 start 忽略 + 警告 |
| 块错配：孤立 end / 未闭合 start | 忽略 + 警告 |
| 块内含行尾 `@internal` | 块整体删除，不重复处理 |
| Markdown 代码块委托 | ` ```python ` 内的 `@internal` 被清理 |
| Markdown 嵌套代码块 | ` ``` ` 内的嵌套块被整体删除 |
| Markdown yaml 块定界 | ` ```yaml ` 内 `@internal-start`/`end` 整体删除 |
| full 模式保留 shebang | `#!/usr/bin/env python` 保留 |
| full 模式保留 TODO | `# TODO: fix` 保留 |
| 语法错误回退 | tokenize 失败时回退正则（仍接入 scan_blocks） |
| 未知语言兜底 | Markdown 中 ` ```rust ` 使用正则兜底 |
| 自定义标记 | 使用 `@private` 替代 `@internal`，块标记自动派生 |
| HTML 注释选择性删除 | `<!-- @internal ... -->` 删除，其他保留 |
| warnings 传播 | 引擎不跨调用泄漏，`--verbose` 输出警告 |
| 自定义插件注册 | 第三方插件通过 `register_plugin()` 注册 |
| entry_points 发现 | 第三方包通过 entry_points 自动加载 |

## 注释标记规范

### 标记语法总表

| 标记类型 | 语法 | 作用范围 | 示例 |
|---------|------|---------|------|
| Python 行注释 | `# @internal` | 单行 | `# @internal 性能优化细节` |
| Python 块定界 | `# @internal-start` ... `# @internal-end` | 块区域整体 | 含定界行与其间所有行整体删除 |
| Python docstring 逐行 | `@internal` 在行首 | docstring 内单行 | `@internal 架构决策说明` |
| Python docstring 整体 | `@internal-docstring` 在首行 | 整个 docstring | `@internal-docstring` |
| JavaScript 行注释 | `// @internal` | 单行 | `// @internal 算法细节` |
| JavaScript 块注释 | `/* @internal ... */` | 块 | `/* @internal 性能数据 */` |
| YAML/Bash 块定界 | `# @internal-start` ... `# @internal-end` | 块区域整体 | yaml/bash 兜底同样支持 |
| YAML/Bash 注释 | `# @internal` | 单行 | `# @internal 内部配置` |
| Markdown 嵌套代码块 | ` ``` ... ``` ` 在代码块内 | 嵌套块整体 | 整体删除 |
| HTML 注释 | `<!-- @internal ... -->` | 整个注释 | `<!-- @internal 内部说明 -->` |

### 标记示例

**Python 行注释**：
```python
def predict_model(image_data):
    """模型预测接口"""

    # @internal 使用TensorRT加速，推理速度提升3倍
    # @internal batch_size=4时GPU利用率最优
    result = model.predict(image_data, batch_size=4)

    return result
```

**Python docstring 逐行标记**：
```python
def online_predict():
    """
    Online 推理任务调度

    @internal 本模块调度 multi_online_model_inference 任务到 native worker
    @internal native worker 使用 solo pool 模式

    Online 任务双重超时控制:
    -----------------------
    Layer 1: requests.timeout (HTTP 层)
    """

    timeout = calculate_timeout()
    return predict(timeout)
```

**Python docstring 整体标记**：
```python
def online_predict():
    """
    @internal-docstring
    Online 推理任务调度 - 自适应超时策略
    ======================================

    本模块调度 multi_online_model_inference 任务到 native worker
    native worker 使用 solo pool 模式
    """

    timeout = calculate_timeout()
    return predict(timeout)
```

**Markdown 嵌套代码块**：
```markdown
## 核心算法说明

```python
def process_data(data):
    """数据处理流程"""

    clean_data = preprocess(data)

    ```
    核心算法细节：
    1. 使用TensorRT加速，推理速度提升3倍
    2. batch_size=4时GPU利用率最优
    ```

    result = model.predict(clean_data)

    return result
```
```

**Python 块定界标记**：
```python
def predict_model(image_data):
    """模型预测接口"""

    # @internal-start
    # 以下为内部实现细节，发布时整体删除
    backend = _select_backend(image_data)  # 块内代码行也会被删除
    # @internal 使用 TensorRT 加速
    # @internal-end

    result = model.predict(image_data)
    return result
```

处理后 `@internal-start` 与 `@internal-end` 及其间所有行（含代码行与块内行尾 `@internal`）整体删除。

**YAML 块定界标记（Markdown 兜底）**：
````markdown
```yaml
# @internal-start
key: value
# 普通配置注释
# @internal-end
another: value
```
````

处理后 yaml 代码块内块区域整体删除，`another: value` 保留。

## 与 FastAPI-Hao 的集成

```bash
# 安装 markstrip
pip install markstrip

# 标记式清理（用于 release 分支）
markstrip app/ --recursive --mode selective

# 全量清理（用于 delivery 分支）
markstrip app/ --recursive --mode full --preserve-docstrings

# 预览清理效果（含块定界与警告）
markstrip app/ --recursive --dry-run --verbose
```

## 更新记录

| 日期 | 版本 | 更新内容 | 作者 |
|------|------|----------|------|
| 2026-07-15 | v1.0 | 初始设计文档 | Trae AI |
| 2026-07-17 | v1.1 | 新增块级定界标记（`@internal-start`/`@internal-end`）、`block_scanner` 模块、warnings 瞬态通道与传播、标记自动派生 | Trae AI |
