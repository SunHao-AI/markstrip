# markstrip

标记式选择性注释过滤库。

markstrip 是一个 Python 库 + CLI 工具，用于基于标记的选择性注释过滤。在多分支代码管理场景中（如 master 保留完整代码/注释，release 分发给第三方时需隐藏核心设计注释），通过在注释中添加 `@internal` 等标记，markstrip 可自动过滤含标记的注释，保留普通注释不动。

## 核心特性

- **选择性过滤**：仅删除含 `@internal` 标记的注释，普通注释原样保留
- **行级精确删除**：行尾标记注释仅删除注释部分，保留同行的代码
- **Docstring 整体删除**：`@internal-docstring` 标记可整体删除 docstring
- **Markdown 支持**：解析代码块并委托对应语言插件处理，支持嵌套代码块删除和 HTML 注释过滤
- **全量模式**：`full` 模式删除所有注释（保留 shebang/TODO/编码声明等）
- **插件架构**：支持通过 `entry_points` 自动发现第三方语言插件
- **语法错误容错**：`tokenize` 失败时自动回退到正则匹配

## 安装

```bash
pip install markstrip
```

开发安装：

```bash
cd markstrip
pip install -e .
```

## 标记类型

| 标记 | 作用域 | 行为 |
|------|--------|------|
| `@internal` | 行级 | 删除含此标记的注释行或行尾注释部分 |
| `@internal-docstring` | docstring 级 | 整体删除包含此标记的 docstring |
| `<!-- @internal -->` | Markdown HTML 注释 | 删除含此标记的 HTML 注释 |

### Python 示例

**输入：**

```python
# 普通注释，应保留
# @internal 这行应被删除
x = 1  # @internal 行尾标记也应删除
# 另一条普通注释
y = 2
```

**输出（selective 模式）：**

```python
# 普通注释，应保留

x = 1
# 另一条普通注释
y = 2
```

### Docstring 逐行过滤

**输入：**

```python
def online_predict():
    """
    Online 推理任务调度

    @internal 本模块调度任务到 native worker
    @internal native worker 使用 solo pool 模式

    Online 任务双重超时控制:
    Layer 1: requests.timeout
    """

    timeout = 1
    return timeout
```

**输出：**

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

### Docstring 整体删除

**输入：**

```python
def online_predict():
    """
    @internal-docstring
    Online 推理任务调度 - 自适应超时策略

    本模块调度任务到 native worker
    native worker 使用 solo pool 模式
    """

    timeout = 1
    return timeout
```

**输出：**

```python
def online_predict():

    timeout = 1
    return timeout
```

## 使用方式

### CLI 命令行

```bash
# 预览清理结果（不修改文件）
markstrip source.py --dry-run

# 清理单个文件并输出到指定路径
markstrip input.py -o output.py

# 原地清理单个文件
markstrip source.py

# 递归清理目录下所有 .py/.md 文件
markstrip src/ --recursive

# 使用 full 模式（删除所有注释，保留 shebang/TODO）
markstrip source.py --mode full

# 自定义标记符号
markstrip source.py --marker @private --dry-run

# full 模式下保留 docstring
markstrip source.py --mode full --preserve-docstrings

# 显示详细处理信息
markstrip src/ -r -v
```

### Python API

```python
from markstrip import strip, strip_file, strip_directory, StripConfig

# 清理字符串内容
result = strip(
    content,
    language="python",  # 或 filename="source.py"
    mode="selective",   # 或 "full"
)
print(result.cleaned_content)
print(f"移除了 {result.removed_count} 处")

# 清理单个文件（原地修改）
strip_file("source.py", inplace=True)

# 清理单个文件（输出到新文件）
result = strip_file("source.py")
# result.cleaned_content 为清理后的内容

# 批量清理目录
results = strip_directory("src/", mode="selective", inplace=True)
for r in results:
    print(f"移除了 {r.removed_count} 处")
```

### 自定义配置

```python
from markstrip import strip, StripConfig

config = StripConfig(
    line_marker="@private",           # 自定义行级标记
    docstring_marker="@private-doc",  # 自定义 docstring 标记
    preserve_docstrings=True,         # full 模式保留 docstring
    preserve_todo=True,              # full 模式保留 TODO/FIXME
    custom_markers=["@confidential"], # 额外标记列表
)

result = strip(content, filename="source.py", config=config)
```

## Markdown 支持

markstrip 可以处理 Markdown 文件中的代码块，将代码块内容委托给对应语言插件处理。

### 代码块委托

Markdown 中的 `` ```python `` 代码块会委托给 PythonPlugin 处理，`@internal` 标记注释会被过滤：

**输入：**

```markdown
# 文档标题

```python
# @internal 这行应删除
# 普通注释保留
x = 1  # @internal 行尾标记删除
```
```

**输出：**

```markdown
# 文档标题

```python

# 普通注释保留
x = 1
```
```

### HTML 注释过滤

Markdown 中的 HTML 注释也可以用 `@internal` 标记过滤：

**输入：**

```markdown
# 文档

<!-- @internal 这条 HTML 注释应删除 -->
<!-- 这条 HTML 注释应保留 -->
```

**输出：**

```markdown
# 文档

<!-- 这条 HTML 注释应保留 -->
```

### 嵌套代码块删除

在 Markdown 代码块内部，缩进的 `` ``` 围栏会被识别为嵌套代码块。当外层代码块是 Python 时，嵌套的纯文本代码块（无语言标识）会被整体删除：

**输入：**

````markdown
## 核心算法

```python
def process_data(data):
    """数据处理"""
    clean_data = preprocess(data)

    ```
    核心算法细节：
    1. 使用TensorRT加速
    2. batch_size=4最优
    ```

    result = model.predict(clean_data)
    return result
```
````

**输出：**

```markdown
## 核心算法

```python
def process_data(data):
    """数据处理"""
    clean_data = preprocess(data)

    result = model.predict(clean_data)
    return result
```
```

## 支持的语言

| 语言 | 扩展名 | 实现方式 |
|------|--------|----------|
| Python | `.py` `.pyw` `.pyi` | `tokenize` 词法分析 |
| Markdown | `.md` `.markdown` | 正则解析代码块 + 委托语言插件 |

后续可扩展 Java、JavaScript、C++ 等语言。

## 插件系统

markstrip 采用插件注册表架构，每个语言是独立的插件。第三方插件通过 `entry_points` 自动发现。

### 自定义插件示例

```python
from markstrip.core.config import StripConfig
from markstrip.languages.base import LanguagePlugin


class JavaScriptPlugin(LanguagePlugin):
    @property
    def name(self) -> str:
        return "javascript"

    @property
    def file_extensions(self) -> list[str]:
        return [".js", ".mjs"]

    def strip_selective(self, content: str, config: StripConfig) -> str:
        # 实现 selective 模式过滤逻辑
        ...

    def strip_full(self, content: str, config: StripConfig) -> str:
        # 实现 full 模式过滤逻辑
        ...


# 注册插件
from markstrip import register_plugin
register_plugin(JavaScriptPlugin())
```

### entry_points 自动发现

在 `pyproject.toml` 中注册 entry point，markstrip 启动时自动加载：

```toml
[project.entry-points."markstrip.plugins"]
javascript = "my_plugin:JavaScriptPlugin"
```

## 运行模式

### selective 模式（默认）

仅删除含标记的注释，保留所有普通注释和代码。适用于 release 分支清理场景。

### full 模式

删除所有注释，但保留以下内容：
- shebang（`#!`）
- 编码声明（`# -*- coding: utf-8 -*-`）
- TODO/FIXME 注释（可通过 `preserve_todo=False` 关闭）
- 类型注释（`# type: ignore`）
- docstring（默认保留，可通过 `preserve_docstrings=False` 删除）

## 已知限制

- **语法错误时的正则回退**：当 Python 代码存在语法错误导致 `tokenize` 失败时，回退到正则匹配。正则模式 `^\s*#\s*@internal` 仅能匹配行首注释（含缩进），**无法处理行尾内联标记注释**（如 `x = 1  # @internal`）。此类注释在回退模式下会被保留。
- **Markdown 嵌套代码块**：仅支持删除无语言标识的嵌套代码块。有语言标识的嵌套代码块不会被删除。

## 测试

```bash
# 运行全部测试
python -m pytest tests/ -v

# 仅运行单元测试
python -m pytest tests/unit/ -v

# 仅运行 CLI 集成测试
python -m pytest tests/integration/ -v
```

测试采用 Golden File 测试策略：每个测试用例包含输入文件（`xxx.py`）和期望输出文件（`xxx.expected.py`），通过参数化测试自动验证。

## 项目结构

```
markstrip/
├── markstrip/
│   ├── __init__.py          # 公共 API: strip(), strip_file(), strip_directory()
│   ├── cli.py               # CLI 命令行工具
│   ├── py.typed             # PEP 561 类型标记
│   ├── core/
│   │   ├── config.py        # StripConfig 配置
│   │   ├── result.py        # StripResult 结果
│   │   ├── errors.py        # 异常定义
│   │   └── engine.py        # StripEngine 核心引擎
│   └── languages/
│       ├── base.py           # LanguagePlugin 抽象基类
│       ├── registry.py       # LanguageRegistry 插件注册表
│       ├── python_plugin.py  # Python 语言插件
│       ├── markdown_plugin.py # Markdown 语言插件
│       └── _builtin.py       # 默认插件注册
├── tests/
│   ├── conftest.py           # Golden file 测试辅助
│   ├── unit/                 # 单元测试
│   ├── integration/          # 集成测试
│   └── golden/               # Golden 测试文件
│       ├── python/           # Python 测试用例
│       └── markdown/         # Markdown 测试用例
├── docs/
│   └── markstrip-design.md   # 设计文档
└── pyproject.toml
```

## License

MIT
