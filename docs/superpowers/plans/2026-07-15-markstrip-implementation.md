# markstrip 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 markstrip 标记式选择性注释过滤库，支持 Python 和 Markdown 两种语言的注释过滤。

**Architecture:** 插件注册表 + 策略模式。每种语言是一个独立插件，实现 `LanguagePlugin` 抽象基类。核心引擎 `StripEngine` 负责调度，通过 `LanguageRegistry` 查找插件。Markdown 插件解析代码块后委托给对应语言插件处理。

**Tech Stack:** Python 3.10+, tokenize（Python 词法分析）, re（正则兜底）, argparse（CLI）, pytest（测试）

## Global Constraints

- Python >= 3.10
- 零运行时依赖（仅标准库）
- 所有代码遵循 PEP 8 导入顺序：标准库 → 第三方 → 本地
- 代码注释使用中文
- 测试框架：pytest
- 项目根目录：`d:\WorkPlace\Pycharm\markstrip`

---

## File Structure

```
markstrip/
├── docs/
│   ├── markstrip-design.md
│   └── superpowers/plans/
│       └── 2026-07-15-markstrip-implementation.md  ← 本文件
├── markstrip/                          # 主包
│   ├── __init__.py                     # 公共 API
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                   # StripConfig
│   │   ├── result.py                   # StripResult
│   │   ├── errors.py                   # 异常定义
│   │   └── engine.py                   # StripEngine
│   ├── languages/
│   │   ├── __init__.py
│   │   ├── base.py                     # LanguagePlugin ABC
│   │   ├── registry.py                 # LanguageRegistry
│   │   ├── python_plugin.py            # PythonPlugin
│   │   ├── markdown_plugin.py          # MarkdownPlugin
│   │   └── _builtin.py                 # 内置插件注册 + entry_points
│   ├── cli.py                          # CLI 入口
│   └── py.typed                        # 类型标记
├── tests/
│   ├── __init__.py
│   ├── conftest.py                     # 黄金文件测试工具
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_config.py
│   │   ├── test_result.py
│   │   ├── test_registry.py
│   │   ├── test_python_plugin.py
│   │   ├── test_markdown_plugin.py
│   │   └── test_engine.py
│   ├── integration/
│   │   ├── __init__.py
│   │   └── test_cli.py
│   └── golden/
│       ├── python/
│       │   ├── internal_comment.py
│       │   ├── internal_comment.expected.py
│       │   ├── docstring_selective.py
│       │   ├── docstring_selective.expected.py
│       │   ├── docstring_whole.py
│       │   ├── docstring_whole.expected.py
│       │   ├── string_with_hash.py
│       │   ├── string_with_hash.expected.py
│       │   ├── full_mode.py
│       │   ├── full_mode.expected.py
│       │   ├── syntax_error.py
│       │   └── syntax_error.expected.py
│       └── markdown/
│           ├── code_block_delegation.md
│           ├── code_block_delegation.expected.md
│           ├── nested_codeblock.md
│           ├── nested_codeblock.expected.md
│           ├── html_comment.md
│           ├── html_comment.expected.md
│           ├── unknown_lang.md
│           └── unknown_lang.expected.md
├── pyproject.toml
└── README.md                           # 仅在最终阶段创建
```

---

### Task 1: 项目脚手架

**Files:**
- Create: `pyproject.toml`
- Create: `markstrip/__init__.py`
- Create: `markstrip/py.typed`
- Create: `markstrip/core/__init__.py`
- Create: `markstrip/languages/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/integration/__init__.py`
- Create: `tests/golden/python/.gitkeep`
- Create: `tests/golden/markdown/.gitkeep`

**Interfaces:**
- Produces: 可安装的 Python 包骨架，`pip install -e .` 可用

- [ ] **Step 1: 创建 pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.backends._legacy:_backend"
[project]
name = "markstrip"
version = "0.1.0"
description = "标记式选择性注释过滤库"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [{name = "markstrip contributors"}]
classifiers = [
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Libraries",
    "Topic :: Utilities",
]

[project.scripts]
markstrip = "markstrip.cli:main"

[project.entry-points."markstrip.plugins"]

[tool.setuptools.packages.find]
include = ["markstrip*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]

[tool.ruff]
line-length = 100
target-version = "py310"
```

- [ ] **Step 2: 创建包目录和 __init__.py 文件**

创建以下空 `__init__.py` 文件（每个只包含一行注释）：

`markstrip/__init__.py`:
```python
"""markstrip - 标记式选择性注释过滤库。"""
```

`markstrip/core/__init__.py`:
```python
"""核心模块。"""
```

`markstrip/languages/__init__.py`:
```python
"""语言插件模块。"""
```

`tests/__init__.py`、`tests/unit/__init__.py`、`tests/integration/__init__.py`:
```python
```

（空文件即可）

`markstrip/py.typed`:
```
```
（空文件，标记 PEP 564 类型支持）

- [ ] **Step 3: 安装包并验证**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; pip install -e .`
Expected: 成功安装，无错误

Run: `python -c "import markstrip; print(markstrip.__doc__)"`
Expected: 输出 `标记式选择性注释过滤库。`

- [ ] **Step 4: 验证 pytest 可运行**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest --co`
Expected: `no tests ran` 或 `collected 0 items`（无错误）

- [ ] **Step 5: 提交**

```bash
cd d:\WorkPlace\Pycharm\markstrip
git init
git add pyproject.toml markstrip/ tests/
git commit -m "feat: 初始化项目脚手架"
```

---

### Task 2: 核心数据结构 (StripConfig, StripResult, errors)

**Files:**
- Create: `markstrip/core/config.py`
- Create: `markstrip/core/result.py`
- Create: `markstrip/core/errors.py`
- Test: `tests/unit/test_config.py`, `tests/unit/test_result.py`

**Interfaces:**
- Produces: `StripConfig`（配置数据类）、`StripResult`（结果数据类）、`MarkstripError`（异常基类）

- [ ] **Step 1: 编写 StripConfig 测试**

```python
# tests/unit/test_config.py
"""StripConfig 单元测试。"""
from markstrip.core.config import StripConfig


def test_default_config():
    config = StripConfig()
    assert config.line_marker == "@internal"
    assert config.docstring_marker == "@internal-docstring"
    assert config.preserve_docstrings is True
    assert config.preserve_todo is True
    assert config.custom_markers == []


def test_custom_config():
    config = StripConfig(
        line_marker="@private",
        docstring_marker="@private-doc",
        preserve_docstrings=False,
        preserve_todo=False,
        custom_markers=["@secret"],
    )
    assert config.line_marker == "@private"
    assert config.docstring_marker == "@private-doc"
    assert config.preserve_docstrings is False
    assert config.preserve_todo is False
    assert config.custom_markers == ["@secret"]


def test_custom_markers_independent():
    """每个 StripConfig 实例的 custom_markers 应独立。"""
    c1 = StripConfig()
    c2 = StripConfig()
    c1.custom_markers.append("@test")
    assert c2.custom_markers == []
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest tests/unit/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'markstrip.core.config'`

- [ ] **Step 3: 实现 StripConfig**

```python
# markstrip/core/config.py
"""清理配置。"""
from dataclasses import dataclass, field


@dataclass
class StripConfig:
    """标记式注释清理配置。

    Attributes:
        line_marker: 行级标记符号，匹配此标记的注释行将被删除。
        docstring_marker: 整体 docstring 标记，放在 docstring 首行时整体删除。
        preserve_docstrings: full 模式下是否保留 docstring。
        preserve_todo: full 模式下是否保留 TODO/FIXME 注释。
        custom_markers: 自定义额外标记列表，与 line_marker 一起匹配。
    """
    line_marker: str = "@internal"
    docstring_marker: str = "@internal-docstring"
    preserve_docstrings: bool = True
    preserve_todo: bool = True
    custom_markers: list[str] = field(default_factory=list)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest tests/unit/test_config.py -v`
Expected: 3 passed

- [ ] **Step 5: 编写 StripResult 测试**

```python
# tests/unit/test_result.py
"""StripResult 单元测试。"""
from markstrip.core.result import StripResult


def test_basic_result():
    result = StripResult(
        cleaned_content="hello",
        removed_count=3,
    )
    assert result.cleaned_content == "hello"
    assert result.removed_count == 3
    assert result.detected_language == ""
    assert result.warnings == []


def test_result_with_warnings():
    result = StripResult(
        cleaned_content="hello",
        removed_count=0,
        detected_language="python",
        warnings=["无法识别语言"],
    )
    assert result.detected_language == "python"
    assert result.warnings == ["无法识别语言"]


def test_warnings_independent():
    r1 = StripResult(cleaned_content="", removed_count=0)
    r2 = StripResult(cleaned_content="", removed_count=0)
    r1.warnings.append("test")
    assert r2.warnings == []
```

- [ ] **Step 6: 实现 StripResult**

```python
# markstrip/core/result.py
"""清理结果。"""
from dataclasses import dataclass, field


@dataclass
class StripResult:
    """注释清理结果。

    Attributes:
        cleaned_content: 清理后的内容。
        removed_count: 删除的行数。
        detected_language: 检测到的语言标识符。
        warnings: 警告信息列表。
    """
    cleaned_content: str
    removed_count: int
    detected_language: str = ""
    warnings: list[str] = field(default_factory=list)
```

- [ ] **Step 7: 实现 errors.py**

```python
# markstrip/core/errors.py
"""异常定义。"""


class MarkstripError(Exception):
    """markstrip 基础异常。"""


class PluginNotFoundError(MarkstripError):
    """未找到匹配的语言插件。"""


class TokenizeError(MarkstripError):
    """tokenize 词法分析失败。"""
```

- [ ] **Step 8: 运行所有测试**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest tests/unit/ -v`
Expected: 6 passed

- [ ] **Step 9: 提交**

```bash
cd d:\WorkPlace\Pycharm\markstrip
git add markstrip/core/config.py markstrip/core/result.py markstrip/core/errors.py tests/unit/test_config.py tests/unit/test_result.py
git commit -m "feat: 添加 StripConfig、StripResult 和异常定义"
```

---

### Task 3: LanguagePlugin 抽象基类 + LanguageRegistry

**Files:**
- Create: `markstrip/languages/base.py`
- Create: `markstrip/languages/registry.py`
- Test: `tests/unit/test_registry.py`

**Interfaces:**
- Produces: `LanguagePlugin`（抽象基类）、`LanguageRegistry`（注册表）
- `LanguagePlugin` 属性: `name` (str), `file_extensions` (list[str])
- `LanguagePlugin` 方法: `strip_selective(content, config) -> str`, `strip_full(content, config) -> str`, `detect(content) -> bool`
- `LanguageRegistry` 方法: `register(plugin)`, `get_plugin(name) -> plugin|None`, `get_plugin_by_extension(ext) -> plugin|None`, `list_languages() -> list[str]`

- [ ] **Step 1: 编写 Registry 测试**

```python
# tests/unit/test_registry.py
"""LanguageRegistry 单元测试。"""
import pytest
from markstrip.languages.base import LanguagePlugin
from markstrip.languages.registry import LanguageRegistry
from markstrip.core.config import StripConfig


class FakePlugin(LanguagePlugin):
    """测试用假插件。"""
    def __init__(self, name, extensions):
        self._name = name
        self._exts = extensions

    @property
    def name(self) -> str:
        return self._name

    @property
    def file_extensions(self) -> list[str]:
        return self._exts

    def strip_selective(self, content: str, config: StripConfig) -> str:
        return content

    def strip_full(self, content: str, config: StripConfig) -> str:
        return content


def test_register_and_get_by_name():
    registry = LanguageRegistry()
    plugin = FakePlugin("python", [".py"])
    registry.register(plugin)
    assert registry.get_plugin("python") is plugin


def test_get_by_name_case_insensitive():
    registry = LanguageRegistry()
    registry.register(FakePlugin("python", [".py"]))
    assert registry.get_plugin("Python") is not None
    assert registry.get_plugin("PYTHON") is not None


def test_get_by_extension():
    registry = LanguageRegistry()
    plugin = FakePlugin("python", [".py", ".pyw"])
    registry.register(plugin)
    assert registry.get_plugin_by_extension(".py") is plugin
    assert registry.get_plugin_by_extension(".pyw") is plugin


def test_get_unknown_plugin():
    registry = LanguageRegistry()
    assert registry.get_plugin("rust") is None
    assert registry.get_plugin_by_extension(".rs") is None


def test_list_languages():
    registry = LanguageRegistry()
    registry.register(FakePlugin("python", [".py"]))
    registry.register(FakePlugin("markdown", [".md"]))
    languages = registry.list_languages()
    assert "python" in languages
    assert "markdown" in languages


def test_register_overwrites():
    registry = LanguageRegistry()
    old = FakePlugin("python", [".py"])
    new = FakePlugin("python", [".py"])
    registry.register(old)
    registry.register(new)
    assert registry.get_plugin("python") is new
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest tests/unit/test_registry.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现 LanguagePlugin 抽象基类**

```python
# markstrip/languages/base.py
"""语言插件抽象基类。"""
from abc import ABC, abstractmethod

from markstrip.core.config import StripConfig


class LanguagePlugin(ABC):
    """语言插件抽象基类。

    每种语言实现此接口，提供 selective 和 full 两种清理模式。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """语言标识符，如 'python', 'markdown'。"""

    @property
    @abstractmethod
    def file_extensions(self) -> list[str]:
        """支持的文件扩展名列表，如 ['.py', '.pyw']。"""

    @abstractmethod
    def strip_selective(self, content: str, config: StripConfig) -> str:
        """标记式选择性过滤：仅删除含标记的注释。

        Args:
            content: 源代码内容。
            config: 清理配置。

        Returns:
            清理后的内容。
        """

    @abstractmethod
    def strip_full(self, content: str, config: StripConfig) -> str:
        """全量注释删除：删除所有注释，保留 shebang/TODO 等。

        Args:
            content: 源代码内容。
            config: 清理配置。

        Returns:
            清理后的内容。
        """

    def detect(self, content: str) -> bool:
        """检测内容是否属于该语言。

        默认返回 False，子类可覆盖以实现内容探测。

        Args:
            content: 待检测的内容。

        Returns:
            是否属于该语言。
        """
        return False
```

- [ ] **Step 4: 实现 LanguageRegistry**

```python
# markstrip/languages/registry.py
"""语言插件注册表。"""
from markstrip.languages.base import LanguagePlugin


class LanguageRegistry:
    """语言插件注册与查找。

    管理所有已注册的语言插件，支持按名称和扩展名查找。
    """

    def __init__(self) -> None:
        self._plugins: dict[str, LanguagePlugin] = {}
        self._extension_map: dict[str, str] = {}

    def register(self, plugin: LanguagePlugin) -> None:
        """注册语言插件。

        Args:
            plugin: 要注册的语言插件实例。
        """
        self._plugins[plugin.name] = plugin
        for ext in plugin.file_extensions:
            self._extension_map[ext] = plugin.name

    def get_plugin(self, name: str) -> LanguagePlugin | None:
        """按语言名查找插件（大小写不敏感）。

        Args:
            name: 语言标识符。

        Returns:
            匹配的插件，未找到返回 None。
        """
        return self._plugins.get(name.lower())

    def get_plugin_by_extension(self, ext: str) -> LanguagePlugin | None:
        """按文件扩展名查找插件。

        Args:
            ext: 文件扩展名，如 '.py'。

        Returns:
            匹配的插件，未找到返回 None。
        """
        name = self._extension_map.get(ext)
        if name:
            return self._plugins.get(name)
        return None

    def list_languages(self) -> list[str]:
        """列出所有已注册语言。

        Returns:
            语言标识符列表。
        """
        return list(self._plugins.keys())
```

- [ ] **Step 5: 运行测试验证通过**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest tests/unit/test_registry.py -v`
Expected: 6 passed

- [ ] **Step 6: 提交**

```bash
cd d:\WorkPlace\Pycharm\markstrip
git add markstrip/languages/base.py markstrip/languages/registry.py tests/unit/test_registry.py
git commit -m "feat: 添加 LanguagePlugin 抽象基类和 LanguageRegistry"
```

---

### Task 4: PythonPlugin - selective 模式（行注释）

**Files:**
- Create: `markstrip/languages/python_plugin.py`
- Test: `tests/unit/test_python_plugin.py`
- Golden: `tests/golden/python/internal_comment.py`, `tests/golden/python/internal_comment.expected.py`, `tests/golden/python/string_with_hash.py`, `tests/golden/python/string_with_hash.expected.py`

**Interfaces:**
- Consumes: `LanguagePlugin`（Task 3）、`StripConfig`（Task 2）
- Produces: `PythonPlugin` 类，`name="python"`，`file_extensions=[".py", ".pyw", ".pyi"]`
- 方法: `strip_selective(content, config) -> str`（仅处理 `# @internal` 行注释，docstring 留到 Task 5）

- [ ] **Step 1: 创建黄金测试文件 — 行注释**

`tests/golden/python/internal_comment.py`:
```python
# 普通注释，应保留
# @internal 这行应被删除
x = 1  # @internal 行尾标记也应删除
# 另一条普通注释
y = 2
```

`tests/golden/python/internal_comment.expected.py`:
```python
# 普通注释，应保留

x = 1
# 另一条普通注释
y = 2
```

- [ ] **Step 2: 创建黄金测试文件 — 字符串中的 #**

`tests/golden/python/string_with_hash.py`:
```python
url = "https://example.com/path#fragment"
path = 'C:\\Users\\test#dir'
comment = "# not a real comment"
x = 1  # @internal 删除这行注释
```

`tests/golden/python/string_with_hash.expected.py`:
```python
url = "https://example.com/path#fragment"
path = 'C:\\Users\\test#dir'
comment = "# not a real comment"
x = 1
```

- [ ] **Step 3: 编写 conftest.py 黄金文件工具**

```python
# tests/conftest.py
"""pytest 公共配置和黄金文件测试工具。"""
from pathlib import Path

GOLDEN_DIR = Path(__file__).parent / "golden"


def collect_golden_cases(lang: str, suffix: str = ".py"):
    """收集黄金测试用例。

    自动匹配 xxx.py 和 xxx.expected.py 文件对。
    """
    cases = []
    lang_dir = GOLDEN_DIR / lang
    if not lang_dir.exists():
        return cases
    for input_file in lang_dir.glob(f"*{suffix}"):
        if input_file.name.endswith(f".expected{suffix}"):
            continue
        expected_file = input_file.with_name(
            input_file.stem + f".expected{suffix}"
        )
        if expected_file.exists():
            cases.append((str(input_file), str(expected_file)))
    return cases
```

- [ ] **Step 4: 编写 PythonPlugin selective 测试**

```python
# tests/unit/test_python_plugin.py
"""PythonPlugin 单元测试。"""
import pytest
from pathlib import Path

from markstrip.languages.python_plugin import PythonPlugin
from markstrip.core.config import StripConfig

from tests.conftest import collect_golden_cases


@pytest.fixture
def plugin():
    return PythonPlugin()


@pytest.fixture
def config():
    return StripConfig()


def test_plugin_name(plugin):
    assert plugin.name == "python"


def test_plugin_extensions(plugin):
    assert ".py" in plugin.file_extensions
    assert ".pyw" in plugin.file_extensions
    assert ".pyi" in plugin.file_extensions


@pytest.mark.parametrize(
    "input_file,expected_file",
    collect_golden_cases("python"),
    ids=[Path(f).stem for f, _ in collect_golden_cases("python")],
)
def test_python_selective_golden(input_file, expected_file):
    plugin = PythonPlugin()
    config = StripConfig()
    content = Path(input_file).read_text(encoding="utf-8")
    expected = Path(expected_file).read_text(encoding="utf-8")
    result = plugin.strip_selective(content, config)
    assert result == expected
```

- [ ] **Step 5: 运行测试验证失败**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest tests/unit/test_python_plugin.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 6: 实现 PythonPlugin — selective 模式（行注释部分）**

```python
# markstrip/languages/python_plugin.py
"""Python 语言插件。"""
import re
import tokenize

from markstrip.core.config import StripConfig
from markstrip.languages.base import LanguagePlugin


class PythonPlugin(LanguagePlugin):
    """Python 语言插件。

    使用 tokenize 词法分析精确定位注释和文档字符串，
    避免误删字符串中的 # 符号。
    """

    @property
    def name(self) -> str:
        return "python"

    @property
    def file_extensions(self) -> list[str]:
        return [".py", ".pyw", ".pyi"]

    def strip_selective(self, content: str, config: StripConfig) -> str:
        """标记式选择性过滤：仅删除含 @internal 标记的注释。

        Args:
            content: Python 源代码内容。
            config: 清理配置。

        Returns:
            清理后的内容。
        """
        lines = content.splitlines(keepends=True)
        remove_ranges: list[tuple[int, int]] = []

        # Phase 1+2: tokenize 识别注释
        try:
            tokens = list(tokenize.tokenize(
                iter(content.encode("utf-8").splitlines(True)).__next__
            ))
        except tokenize.TokenizeError:
            return self._fallback_regex_selective(content, config)

        for tok in tokens:
            if tok.type == tokenize.COMMENT:
                if self._has_marker(tok.string, config):
                    remove_ranges.append((tok.start[0], tok.end[0]))

        # Phase 4: 行级重组
        return self._rebuild(lines, remove_ranges)

    def strip_full(self, content: str, config: StripConfig) -> str:
        """全量注释删除。"""
        # Task 6 实现
        return content

    def _has_marker(self, comment_text: str, config: StripConfig) -> bool:
        """检查注释是否包含标记。

        Args:
            comment_text: 注释文本（含 # 前缀）。
            config: 清理配置。

        Returns:
            是否包含标记。
        """
        markers = [config.line_marker] + config.custom_markers
        # 去掉 # 前缀后检查
        stripped = comment_text.lstrip("#").strip()
        for marker in markers:
            if stripped.startswith(marker):
                return True
        return False

    def _rebuild(
        self,
        lines: list[str],
        remove_ranges: list[tuple[int, int]],
    ) -> str:
        """按行号范围重组代码。

        Args:
            lines: 原始行列表（splitlines(keepends=True)）。
            remove_ranges: 需要删除的行范围列表 (start, end)，1-based。

        Returns:
            重组后的内容。
        """
        if not remove_ranges:
            return "".join(lines)

        # 构建需要删除的行号集合
        remove_lines: set[int] = set()
        for start, end in remove_ranges:
            for line_num in range(start, end + 1):
                remove_lines.add(line_num)

        # 保留未标记删除的行
        result = []
        for i, line in enumerate(lines, start=1):
            if i not in remove_lines:
                result.append(line)

        return "".join(result)

    def _fallback_regex_selective(
        self, content: str, config: StripConfig
    ) -> str:
        """tokenize 失败时的正则回退。

        Args:
            content: 源代码内容。
            config: 清理配置。

        Returns:
            清理后的内容。
        """
        marker = re.escape(config.line_marker)
        pattern = rf"^\s*#\s*{marker}.*$\n?"
        return re.sub(pattern, "", content, flags=re.MULTILINE)
```

- [ ] **Step 7: 运行测试验证通过**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest tests/unit/test_python_plugin.py -v`
Expected: all passed（包括黄金文件测试）

- [ ] **Step 8: 提交**

```bash
cd d:\WorkPlace\Pycharm\markstrip
git add markstrip/languages/python_plugin.py tests/unit/test_python_plugin.py tests/conftest.py tests/golden/python/
git commit -m "feat: 添加 PythonPlugin selective 模式（行注释过滤）"
```

---

### Task 5: PythonPlugin - docstring 处理

**Files:**
- Modify: `markstrip/languages/python_plugin.py`
- Golden: `tests/golden/python/docstring_selective.py`, `tests/golden/python/docstring_selective.expected.py`, `tests/golden/python/docstring_whole.py`, `tests/golden/python/docstring_whole.expected.py`

**Interfaces:**
- Consumes: `PythonPlugin`（Task 4）
- Produces: 在 `strip_selective` 中增加 docstring 处理逻辑
- 新增方法: `_is_docstring(tok, tokens) -> bool`, `_process_docstring(tok, config) -> list[tuple[int, int]]`

- [ ] **Step 1: 创建黄金测试文件 — docstring 逐行标记**

`tests/golden/python/docstring_selective.py`:
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

`tests/golden/python/docstring_selective.expected.py`:
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

- [ ] **Step 2: 创建黄金测试文件 — docstring 整体标记**

`tests/golden/python/docstring_whole.py`:
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

`tests/golden/python/docstring_whole.expected.py`:
```python
def online_predict():

    timeout = 1
    return timeout
```

- [ ] **Step 3: 运行测试验证新增黄金文件失败**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest tests/unit/test_python_plugin.py -v -k "docstring"`
Expected: FAIL — docstring 内的 @internal 行未被删除

- [ ] **Step 4: 实现 docstring 处理逻辑**

修改 `markstrip/languages/python_plugin.py`，在 `strip_selective` 方法中添加 docstring 处理。

在 `import` 区域添加 `ast`：
```python
import ast
import re
import tokenize
```

修改 `strip_selective` 方法，在 COMMENT 处理后添加 STRING 处理：

```python
    def strip_selective(self, content: str, config: StripConfig) -> str:
        """标记式选择性过滤：仅删除含 @internal 标记的注释。"""
        lines = content.splitlines(keepends=True)
        remove_ranges: list[tuple[int, int]] = []

        try:
            tokens = list(tokenize.tokenize(
                iter(content.encode("utf-8").splitlines(True)).__next__
            ))
        except tokenize.TokenizeError:
            return self._fallback_regex_selective(content, config)

        for tok in tokens:
            if tok.type == tokenize.COMMENT:
                if self._has_marker(tok.string, config):
                    remove_ranges.append((tok.start[0], tok.end[0]))

            if tok.type == tokenize.STRING:
                if self._is_docstring(tok, tokens):
                    doc_ranges = self._process_docstring(tok, config)
                    remove_ranges.extend(doc_ranges)

        return self._rebuild(lines, remove_ranges)
```

在类中添加以下方法：

```python
    def _is_docstring(
        self,
        tok: tokenize.TokenInfo,
        tokens: list[tokenize.TokenInfo],
    ) -> bool:
        """判断 STRING token 是否为 docstring。

        docstring 是模块、类或函数体的首条语句。

        Args:
            tok: 待判断的 token。
            tokens: 完整 token 列表。

        Returns:
            是否为 docstring。
        """
        # 简化判断：三引号字符串且前一个非空 token 是 NEWLINE/INDENT/DEDENT
        # 或位于文件开头
        idx = tokens.index(tok)
        # 向前查找第一个非 NL/NEWLINE token
        prev_idx = idx - 1
        while prev_idx >= 0 and tokens[prev_idx].type in (
            tokenize.NL,
            tokenize.NEWLINE,
        ):
            prev_idx -= 1

        if prev_idx < 0:
            # 文件开头，是模块 docstring
            return True

        prev = tokens[prev_idx]
        # 前一个是 INDENT 或 COLON 后的 NEWLINE → 可能是函数/类体首语句
        if prev.type in (tokenize.INDENT, tokenize.DEDENT):
            return True
        # 前一个是冒号 → 函数/类定义后的首语句
        if prev.type == tokenize.OP and prev.string == ":":
            return True
        # 简化：多行字符串（含换行）也可能是 docstring
        if "\n" in tok.string:
            return True
        return False

    def _process_docstring(
        self,
        tok: tokenize.TokenInfo,
        config: StripConfig,
    ) -> list[tuple[int, int]]:
        """处理单个 docstring，返回需删除的行范围。

        Args:
            tok: docstring 的 STRING token。
            config: 清理配置。

        Returns:
            需要删除的 (start_line, end_line) 列表。
        """
        try:
            content = ast.literal_eval(tok.string)
        except (ValueError, SyntaxError):
            return []

        lines = content.split("\n")

        # 检查 @internal-docstring 标记（整体删除）
        first_line = lines[0].strip() if lines else ""
        if first_line.startswith(config.docstring_marker):
            return [(tok.start[0], tok.end[0])]

        # 逐行检查 @internal 标记
        markers = [config.line_marker] + config.custom_markers
        marked_lines: list[tuple[int, int]] = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            for marker in markers:
                if stripped.startswith(marker):
                    # 映射到源文件行号
                    source_line = tok.start[0] + i
                    marked_lines.append((source_line, source_line))
                    break

        return marked_lines
```

- [ ] **Step 5: 运行测试验证通过**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest tests/unit/test_python_plugin.py -v`
Expected: all passed

- [ ] **Step 6: 提交**

```bash
cd d:\WorkPlace\Pycharm\markstrip
git add markstrip/languages/python_plugin.py tests/golden/python/docstring_selective.py tests/golden/python/docstring_selective.expected.py tests/golden/python/docstring_whole.py tests/golden/python/docstring_whole.expected.py
git commit -m "feat: 添加 PythonPlugin docstring 选择性过滤和整体删除"
```

---

### Task 6: PythonPlugin - strip_full + 保留规则 + 语法错误回退

**Files:**
- Modify: `markstrip/languages/python_plugin.py`
- Golden: `tests/golden/python/full_mode.py`, `tests/golden/python/full_mode.expected.py`, `tests/golden/python/syntax_error.py`, `tests/golden/python/syntax_error.expected.py`

**Interfaces:**
- Consumes: `PythonPlugin`（Task 5）
- Produces: `strip_full` 完整实现、`_is_preserved_comment` 方法

- [ ] **Step 1: 创建黄金测试文件 — full 模式**

`tests/golden/python/full_mode.py`:
```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# TODO: 需要修复此问题
# FIXME: 另一个待修复项
# 普通注释，应删除
# type: ignore
import os


def func():
    """这是 docstring。"""
    # 函数内注释，应删除
    x = 1  # 行尾注释，应删除
    return x
```

`tests/golden/python/full_mode.expected.py`:
```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# TODO: 需要修复此问题
# FIXME: 另一个待修复项
# type: ignore
import os


def func():
    """这是 docstring。"""

    x = 1
    return x
```

> 注意：默认 `preserve_docstrings=True`，所以 docstring 保留。

- [ ] **Step 2: 创建黄金测试文件 — 语法错误回退**

`tests/golden/python/syntax_error.py`:
```python
# @internal 这行应被正则删除
def broken(
    # 语法错误，缺少右括号
    x = 1
# @internal 正则回退也应删除这行
```

`tests/golden/python/syntax_error.expected.py`:
```python
def broken(
    x = 1
```

- [ ] **Step 3: 编写 strip_full 测试**

在 `tests/unit/test_python_plugin.py` 中追加：

```python
def test_strip_full_removes_comments(plugin, config):
    content = "# 普通注释\nx = 1\n"
    result = plugin.strip_full(content, config)
    assert "#" not in result
    assert "x = 1" in result


def test_strip_full_preserves_shebang(plugin, config):
    content = "#!/usr/bin/env python\nx = 1\n"
    result = plugin.strip_full(content, config)
    assert "#!/usr/bin/env python" in result


def test_strip_full_preserves_todo(plugin, config):
    content = "# TODO: fix later\nx = 1\n"
    result = plugin.strip_full(content, config)
    assert "TODO" in result


def test_strip_full_preserves_encoding(plugin, config):
    content = "# -*- coding: utf-8 -*-\nx = 1\n"
    result = plugin.strip_full(content, config)
    assert "coding" in result


def test_strip_full_preserves_type_comment(plugin, config):
    content = "# type: ignore\nx = 1\n"
    result = plugin.strip_full(content, config)
    assert "type: ignore" in result


def test_strip_full_removes_docstrings_when_configured(plugin):
    content = 'def f():\n    """docstring"""\n    return 1\n'
    config = StripConfig(preserve_docstrings=False)
    result = plugin.strip_full(content, config)
    assert '"""docstring"""' not in result


def test_strip_full_preserves_docstrings_by_default(plugin, config):
    content = 'def f():\n    """docstring"""\n    return 1\n'
    result = plugin.strip_full(content, config)
    assert '"""docstring"""' in result
```

并在黄金文件参数化测试中添加 full 模式测试：

```python
@pytest.mark.parametrize(
    "input_file,expected_file",
    collect_golden_cases("python"),
    ids=[Path(f).stem for f, _ in collect_golden_cases("python")],
)
def test_python_full_golden(input_file, expected_file):
    plugin = PythonPlugin()
    config = StripConfig()
    content = Path(input_file).read_text(encoding="utf-8")
    expected = Path(expected_file).read_text(encoding="utf-8")
    result = plugin.strip_full(content, config)
    assert result == expected
```

> 注意：`internal_comment` 和 `string_with_hash` 的 expected 文件需要也通过 full 模式测试。但 full 模式会删除所有注释，所以这两个文件的 full 模式 expected 内容与 selective 不同。我们需要为 full 模式创建单独的 expected 文件，或在测试中只对 `full_mode` 和 `syntax_error` 运行 full 模式测试。

修正：将 `test_python_full_golden` 改为只测试文件名含 `full` 或 `syntax_error` 的用例：

```python
@pytest.mark.parametrize(
    "input_file,expected_file",
    [(i, e) for i, e in collect_golden_cases("python")
     if "full" in Path(i).stem or "syntax" in Path(i).stem],
    ids=[Path(f).stem for f, e in [(i, e) for i, e in collect_golden_cases("python")
     if "full" in Path(i).stem or "syntax" in Path(i).stem]],
)
def test_python_full_golden(input_file, expected_file):
    plugin = PythonPlugin()
    config = StripConfig()
    content = Path(input_file).read_text(encoding="utf-8")
    expected = Path(expected_file).read_text(encoding="utf-8")
    result = plugin.strip_full(content, config)
    assert result == expected
```

- [ ] **Step 4: 运行测试验证失败**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest tests/unit/test_python_plugin.py -v`
Expected: FAIL — `strip_full` 当前返回原内容

- [ ] **Step 5: 实现 strip_full 和 _is_preserved_comment**

修改 `markstrip/languages/python_plugin.py`，替换 `strip_full` 方法：

```python
    def strip_full(self, content: str, config: StripConfig) -> str:
        """全量注释删除：删除所有注释，保留 shebang/TODO 等。

        Args:
            content: Python 源代码内容。
            config: 清理配置。

        Returns:
            清理后的内容。
        """
        lines = content.splitlines(keepends=True)
        remove_ranges: list[tuple[int, int]] = []

        try:
            tokens = list(tokenize.tokenize(
                iter(content.encode("utf-8").splitlines(True)).__next__
            ))
        except tokenize.TokenizeError:
            # 语法错误时无法处理，直接返回原内容
            return content

        for tok in tokens:
            if tok.type == tokenize.COMMENT:
                if self._is_preserved_comment(tok, config):
                    continue
                remove_ranges.append((tok.start[0], tok.end[0]))

            if tok.type == tokenize.STRING:
                if self._is_docstring(tok, tokens):
                    if not config.preserve_docstrings:
                        remove_ranges.append((tok.start[0], tok.end[0]))

        return self._rebuild(lines, remove_ranges)

    def _is_preserved_comment(
        self,
        tok: tokenize.TokenInfo,
        config: StripConfig,
    ) -> bool:
        """判断注释是否应被保留（full 模式）。

        Args:
            tok: COMMENT token。
            config: 清理配置。

        Returns:
            True 表示保留，False 表示删除。
        """
        text = tok.string.strip()
        # 保留 shebang
        if text.startswith("#!"):
            return True
        # 保留编码声明
        if "coding:" in text or "coding=" in text:
            return True
        # 保留 TODO/FIXME
        if config.preserve_todo and (
            "TODO" in text or "FIXME" in text
        ):
            return True
        # 保留类型注释
        if text.startswith("# type:"):
            return True
        return False
```

- [ ] **Step 6: 运行测试验证通过**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest tests/unit/test_python_plugin.py -v`
Expected: all passed

- [ ] **Step 7: 提交**

```bash
cd d:\WorkPlace\Pycharm\markstrip
git add markstrip/languages/python_plugin.py tests/unit/test_python_plugin.py tests/golden/python/full_mode.py tests/golden/python/full_mode.expected.py tests/golden/python/syntax_error.py tests/golden/python/syntax_error.expected.py
git commit -m "feat: 添加 PythonPlugin strip_full 模式和保留规则"
```

---

### Task 7: MarkdownPlugin - 代码块解析 + 委托 + 嵌套块

**Files:**
- Create: `markstrip/languages/markdown_plugin.py`
- Test: `tests/unit/test_markdown_plugin.py`
- Golden: `tests/golden/markdown/code_block_delegation.md`, `tests/golden/markdown/code_block_delegation.expected.md`, `tests/golden/markdown/nested_codeblock.md`, `tests/golden/markdown/nested_codeblock.expected.md`

**Interfaces:**
- Consumes: `LanguagePlugin`（Task 3）、`LanguageRegistry`（Task 3）、`StripConfig`（Task 2）、`PythonPlugin`（Task 6）
- Produces: `MarkdownPlugin` 类，`name="markdown"`，`file_extensions=[".md", ".markdown"]`
- 构造函数: `__init__(self, registry: LanguageRegistry)`
- 方法: `strip_selective`, `strip_full`, `_process_code_blocks`, `_remove_nested_blocks`

- [ ] **Step 1: 创建黄金测试文件 — 代码块委托**

`tests/golden/markdown/code_block_delegation.md`:
```markdown
# 文档标题

```python
# @internal 这行应删除
# 普通注释保留
x = 1  # @internal 行尾标记删除
```

一些文字

```python
def func():
    """docstring"""
    # @internal 函数内注释删除
    return 1
```
```

`tests/golden/markdown/code_block_delegation.expected.md`:
```markdown
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
```

- [ ] **Step 2: 创建黄金测试文件 — 嵌套代码块**

`tests/golden/markdown/nested_codeblock.md`:
```markdown
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
```

`tests/golden/markdown/nested_codeblock.expected.md`:
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

- [ ] **Step 3: 编写 MarkdownPlugin 测试**

```python
# tests/unit/test_markdown_plugin.py
"""MarkdownPlugin 单元测试。"""
import pytest
from pathlib import Path

from markstrip.languages.markdown_plugin import MarkdownPlugin
from markstrip.languages.registry import LanguageRegistry
from markstrip.languages.python_plugin import PythonPlugin
from markstrip.core.config import StripConfig

from tests.conftest import collect_golden_cases


@pytest.fixture
def plugin():
    registry = LanguageRegistry()
    registry.register(PythonPlugin())
    return MarkdownPlugin(registry)


@pytest.fixture
def config():
    return StripConfig()


def test_plugin_name(plugin):
    assert plugin.name == "markdown"


def test_plugin_extensions(plugin):
    assert ".md" in plugin.file_extensions
    assert ".markdown" in plugin.file_extensions


@pytest.mark.parametrize(
    "input_file,expected_file",
    collect_golden_cases("markdown", ".md"),
    ids=[Path(f).stem for f, _ in collect_golden_cases("markdown", ".md")],
)
def test_markdown_selective_golden(input_file, expected_file, plugin, config):
    content = Path(input_file).read_text(encoding="utf-8")
    expected = Path(expected_file).read_text(encoding="utf-8")
    result = plugin.strip_selective(content, config)
    assert result == expected
```

- [ ] **Step 4: 运行测试验证失败**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest tests/unit/test_markdown_plugin.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 5: 实现 MarkdownPlugin**

```python
# markstrip/languages/markdown_plugin.py
"""Markdown 语言插件。"""
import re

from markstrip.core.config import StripConfig
from markstrip.languages.base import LanguagePlugin
from markstrip.languages.registry import LanguageRegistry

# 代码块正则：匹配 ```language\n...\n```
CODE_BLOCK_RE = re.compile(
    r"(?P<fence>`{3,})(?P<lang>\w*)\n(?P<code>.*?)(?P=fence)",
    re.DOTALL,
)

# 嵌套代码块：代码块内的 ``` 标记对
NESTED_BLOCK_RE = re.compile(r"```\n.*?```\n?", re.DOTALL)


class MarkdownPlugin(LanguagePlugin):
    """Markdown 语言插件。

    解析 Markdown 代码块后委托给对应语言插件处理。
    支持嵌套代码块删除和 HTML 注释过滤。
    """

    def __init__(self, registry: LanguageRegistry) -> None:
        self._registry = registry

    @property
    def name(self) -> str:
        return "markdown"

    @property
    def file_extensions(self) -> list[str]:
        return [".md", ".markdown"]

    def strip_selective(
        self, content: str, config: StripConfig
    ) -> str:
        """标记式选择性过滤。"""
        content = self._process_code_blocks(
            content, config, mode="selective"
        )
        return content

    def strip_full(self, content: str, config: StripConfig) -> str:
        """全量注释删除。"""
        content = self._process_code_blocks(
            content, config, mode="full"
        )
        return content

    def _process_code_blocks(
        self,
        content: str,
        config: StripConfig,
        mode: str,
    ) -> str:
        """处理所有围栏代码块。

        Args:
            content: Markdown 内容。
            config: 清理配置。
            mode: "selective" 或 "full"。

        Returns:
            处理后的内容。
        """

        def process_block(match: re.Match) -> str:
            fence = match.group("fence")
            lang = match.group("lang").lower()
            code = match.group("code")

            # 删除嵌套代码块
            code = self._remove_nested_blocks(code)

            # 委托给语言插件
            plugin = self._registry.get_plugin(lang)
            if plugin is not None:
                if mode == "selective":
                    cleaned = plugin.strip_selective(code, config)
                else:
                    cleaned = plugin.strip_full(code, config)
                return f"{fence}{lang}\n{cleaned}{fence}"

            # 未知语言：正则兜底
            cleaned = self._fallback_strip(code, lang, config)
            return f"{fence}{lang}\n{cleaned}{fence}"

        return CODE_BLOCK_RE.sub(process_block, content)

    def _remove_nested_blocks(self, code: str) -> str:
        """删除代码块内的嵌套 ``` 标记对及其内容。

        Args:
            code: 代码块内容。

        Returns:
            清理后的代码内容。
        """
        return NESTED_BLOCK_RE.sub("", code)

    def _fallback_strip(
        self,
        code: str,
        lang: str,
        config: StripConfig,
    ) -> str:
        """无对应插件时的正则兜底。

        Args:
            code: 代码内容。
            lang: 语言标识符。
            config: 清理配置。

        Returns:
            清理后的内容。
        """
        templates = {
            "yaml": r"^\s*#\s*{marker}.*$\n?",
            "bash": r"^\s*#\s*{marker}.*$\n?",
            "shell": r"^\s*#\s*{marker}.*$\n?",
            "javascript": r"^\s*//\s*{marker}.*$\n?",
            "java": r"^\s*//\s*{marker}.*$\n?",
            "c": r"^\s*//\s*{marker}.*$\n?",
            "cpp": r"^\s*//\s*{marker}.*$\n?",
        }
        template = templates.get(lang)
        if template is None:
            return code
        marker = re.escape(config.line_marker)
        pattern = template.format(marker=marker)
        return re.sub(pattern, "", code, flags=re.MULTILINE)
```

- [ ] **Step 6: 运行测试验证通过**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest tests/unit/test_markdown_plugin.py -v`
Expected: all passed

- [ ] **Step 7: 提交**

```bash
cd d:\WorkPlace\Pycharm\markstrip
git add markstrip/languages/markdown_plugin.py tests/unit/test_markdown_plugin.py tests/golden/markdown/
git commit -m "feat: 添加 MarkdownPlugin 代码块解析、委托和嵌套块删除"
```

---

### Task 8: MarkdownPlugin - HTML 注释 + 兜底测试

**Files:**
- Modify: `markstrip/languages/markdown_plugin.py`
- Golden: `tests/golden/markdown/html_comment.md`, `tests/golden/markdown/html_comment.expected.md`, `tests/golden/markdown/unknown_lang.md`, `tests/golden/markdown/unknown_lang.expected.md`

**Interfaces:**
- Consumes: `MarkdownPlugin`（Task 7）
- Produces: `_process_html_comments` 方法、HTML 注释过滤逻辑

- [ ] **Step 1: 创建黄金测试文件 — HTML 注释**

`tests/golden/markdown/html_comment.md`:
```markdown
# 文档

<!-- @internal 这条 HTML 注释应删除 -->
<!-- 这条 HTML 注释应保留 -->

```python
# @internal 代码块内的标记也应删除
x = 1
```

<!-- @internal 另一条应删除的 -->
```

`tests/golden/markdown/html_comment.expected.md`:
```markdown
# 文档

<!-- 这条 HTML 注释应保留 -->

```python
x = 1
```

```

- [ ] **Step 2: 创建黄金测试文件 — 未知语言兜底**

`tests/golden/markdown/unknown_lang.md`:
```markdown
# 文档

```yaml
key: value
# @internal 内部配置应删除
another: value
```

```rust
// @internal 这行不会被处理（无兜底模式）
fn main() {}
```
```

`tests/golden/markdown/unknown_lang.expected.md`:
```markdown
# 文档

```yaml
key: value
another: value
```

```rust
// @internal 这行不会被处理（无兜底模式）
fn main() {}
```
```

- [ ] **Step 3: 运行测试验证失败**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest tests/unit/test_markdown_plugin.py -v -k "html_comment or unknown_lang"`
Expected: FAIL — HTML 注释未被处理，yaml 兜底未生效

- [ ] **Step 4: 实现 HTML 注释处理**

修改 `markstrip/languages/markdown_plugin.py`，在模块顶部添加正则：

```python
# HTML 注释正则
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
```

修改 `strip_selective` 方法：

```python
    def strip_selective(
        self, content: str, config: StripConfig
    ) -> str:
        """标记式选择性过滤。"""
        content = self._process_code_blocks(
            content, config, mode="selective"
        )
        content = self._process_html_comments(content, config, mode="selective")
        return content
```

修改 `strip_full` 方法：

```python
    def strip_full(self, content: str, config: StripConfig) -> str:
        """全量注释删除。"""
        content = self._process_code_blocks(
            content, config, mode="full"
        )
        content = self._process_html_comments(content, config, mode="full")
        return content
```

在类中添加 `_process_html_comments` 方法：

```python
    def _process_html_comments(
        self,
        content: str,
        config: StripConfig,
        mode: str,
    ) -> str:
        """处理 HTML 注释。

        Args:
            content: Markdown 内容。
            config: 清理配置。
            mode: "selective" 仅删除含标记的，"full" 删除所有。

        Returns:
            处理后的内容。
        """
        if mode == "full":
            return HTML_COMMENT_RE.sub("", content)

        def filter_comment(match: re.Match) -> str:
            comment = match.group(0)
            if config.line_marker in comment:
                return ""
            return comment

        return HTML_COMMENT_RE.sub(filter_comment, content)
```

- [ ] **Step 5: 运行测试验证通过**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest tests/unit/test_markdown_plugin.py -v`
Expected: all passed

- [ ] **Step 6: 提交**

```bash
cd d:\WorkPlace\Pycharm\markstrip
git add markstrip/languages/markdown_plugin.py tests/golden/markdown/html_comment.md tests/golden/markdown/html_comment.expected.md tests/golden/markdown/unknown_lang.md tests/golden/markdown/unknown_lang.expected.md
git commit -m "feat: 添加 MarkdownPlugin HTML 注释处理和未知语言兜底"
```

---

### Task 9: StripEngine + _builtin.py + 公共 API

**Files:**
- Create: `markstrip/core/engine.py`
- Create: `markstrip/languages/_builtin.py`
- Modify: `markstrip/__init__.py`
- Test: `tests/unit/test_engine.py`

**Interfaces:**
- Consumes: `LanguageRegistry`（Task 3）、`PythonPlugin`（Task 6）、`MarkdownPlugin`（Task 8）、`StripConfig`/`StripResult`（Task 2）
- Produces: `StripEngine` 类、`_create_default_registry()` 函数、公共 API 函数
- 公共 API: `strip()`, `strip_file()`, `strip_directory()`, `register_plugin()`

- [ ] **Step 1: 编写 StripEngine 测试**

```python
# tests/unit/test_engine.py
"""StripEngine 单元测试。"""
from pathlib import Path
from tempfile import NamedTemporaryFile

from markstrip import strip, strip_file, register_plugin
from markstrip.core.config import StripConfig
from markstrip.core.result import StripResult


def test_strip_by_language():
    content = "# @internal 删除\nx = 1\n"
    result = strip(content, language="python", mode="selective")
    assert "# @internal" not in result.cleaned_content
    assert result.detected_language == "python"
    assert result.removed_count >= 1


def test_strip_by_filename():
    content = "# @internal 删除\nx = 1\n"
    result = strip(content, filename="test.py")
    assert result.detected_language == "python"


def test_strip_markdown_by_filename():
    content = "```python\n# @internal 删除\nx = 1\n```\n"
    result = strip(content, filename="test.md")
    assert result.detected_language == "markdown"
    assert "# @internal" not in result.cleaned_content


def test_strip_unknown_language():
    content = "some content"
    result = strip(content, language="rust")
    assert result.cleaned_content == content
    assert result.removed_count == 0
    assert len(result.warnings) > 0


def test_strip_full_mode():
    content = "# 注释\nx = 1\n"
    result = strip(content, language="python", mode="full")
    assert "#" not in result.cleaned_content


def test_strip_file():
    with NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write("# @internal 删除\nx = 1\n")
        f.flush()
        result = strip_file(f.name)
    assert "# @internal" not in result.cleaned_content


def test_strip_file_inplace():
    with NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write("# @internal 删除\nx = 1\n")
        f.flush()
        path = f.name

    strip_file(path, inplace=True)
    content = Path(path).read_text(encoding="utf-8")
    assert "# @internal" not in content


def test_custom_config():
    content = "# @private 删除\nx = 1\n"
    config = StripConfig(line_marker="@private")
    result = strip(content, language="python", config=config)
    assert "# @private" not in result.cleaned_content
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest tests/unit/test_engine.py -v`
Expected: FAIL — `ModuleNotFoundError` 或 `ImportError`

- [ ] **Step 3: 实现 _builtin.py**

```python
# markstrip/languages/_builtin.py
"""内置插件注册和 entry_points 自动发现。"""
import importlib.metadata
import sys
import warnings

from markstrip.languages.base import LanguagePlugin
from markstrip.languages.registry import LanguageRegistry
from markstrip.languages.python_plugin import PythonPlugin
from markstrip.languages.markdown_plugin import MarkdownPlugin


def _create_default_registry() -> LanguageRegistry:
    """创建默认注册表，注册所有内置插件和 entry_points 插件。

    Returns:
        包含所有已注册插件的 LanguageRegistry 实例。
    """
    registry = LanguageRegistry()

    # 注册 Python 插件
    python_plugin = PythonPlugin()
    registry.register(python_plugin)

    # 注册 Markdown 插件（需要 registry 引用以委托其他插件）
    markdown_plugin = MarkdownPlugin(registry)
    registry.register(markdown_plugin)

    # 发现并注册 entry_points 插件
    for plugin in _discover_entry_point_plugins():
        registry.register(plugin)

    return registry


def _discover_entry_point_plugins() -> list[LanguagePlugin]:
    """通过 entry_points 自动发现第三方插件。

    Returns:
        发现的插件实例列表。
    """
    plugins: list[LanguagePlugin] = []

    try:
        if sys.version_info >= (3, 10):
            eps = importlib.metadata.entry_points(
                group="markstrip.plugins"
            )
        else:
            eps = importlib.metadata.entry_points().get(
                "markstrip.plugins", []
            )
    except Exception:
        return plugins

    for ep in eps:
        try:
            plugin_class = ep.load()
            plugins.append(plugin_class())
        except Exception as e:
            warnings.warn(f"加载插件 {ep.name} 失败: {e}")

    return plugins
```

- [ ] **Step 4: 实现 StripEngine**

```python
# markstrip/core/engine.py
"""主引擎：调度插件执行清理。"""
from pathlib import Path

from markstrip.core.config import StripConfig
from markstrip.core.result import StripResult
from markstrip.languages.base import LanguagePlugin
from markstrip.languages.registry import LanguageRegistry
from markstrip.languages._builtin import _create_default_registry


class StripEngine:
    """主引擎：调度语言插件执行注释清理。

    按优先级解析语言：显式指定 > 文件扩展名 > 内容探测。
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
    ) -> StripResult:
        """清理内容中的注释。

        Args:
            content: 待清理的内容。
            language: 显式指定语言标识符。
            filename: 文件名（用于扩展名检测）。
            mode: "selective" 或 "full"。
            config: 清理配置，为 None 时使用默认配置。

        Returns:
            StripResult 清理结果。
        """
        config = config or StripConfig()

        plugin = self._resolve_plugin(language, filename, content)
        if plugin is None:
            return StripResult(
                cleaned_content=content,
                removed_count=0,
                warnings=["无法识别语言，跳过处理"],
            )

        original_len = len(content.splitlines())
        if mode == "full":
            cleaned = plugin.strip_full(content, config)
        else:
            cleaned = plugin.strip_selective(content, config)
        cleaned_len = len(cleaned.splitlines())

        return StripResult(
            cleaned_content=cleaned,
            removed_count=original_len - cleaned_len,
            detected_language=plugin.name,
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

- [ ] **Step 5: 实现公共 API**

修改 `markstrip/__init__.py`：

```python
"""markstrip - 标记式选择性注释过滤库。"""
from pathlib import Path
from typing import Union

from markstrip.core.config import StripConfig
from markstrip.core.engine import StripEngine
from markstrip.core.result import StripResult
from markstrip.languages.base import LanguagePlugin
from markstrip.languages.registry import LanguageRegistry

# 默认引擎实例（内置插件已注册）
_default_engine = StripEngine()


def strip(
    content: str,
    *,
    language: str | None = None,
    filename: str | None = None,
    mode: str = "selective",
    config: StripConfig | None = None,
) -> StripResult:
    """清理内容中的标记注释。

    Args:
        content: 待清理的内容。
        language: 显式指定语言标识符。
        filename: 文件名（用于扩展名检测）。
        mode: "selective"（标记过滤）或 "full"（全量删除）。
        config: 清理配置，为 None 时使用默认配置。

    Returns:
        StripResult 清理结果。
    """
    return _default_engine.strip(
        content,
        language=language,
        filename=filename,
        mode=mode,
        config=config,
    )


def strip_file(
    path: Union[str, Path],
    *,
    mode: str = "selective",
    config: StripConfig | None = None,
    inplace: bool = False,
) -> StripResult:
    """清理文件中的标记注释。

    Args:
        path: 文件路径。
        mode: "selective" 或 "full"。
        config: 清理配置。
        inplace: 是否原地修改文件。

    Returns:
        StripResult 清理结果。
    """
    path = Path(path)
    content = path.read_text(encoding="utf-8")
    result = _default_engine.strip(
        content, filename=str(path), mode=mode, config=config
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
) -> list[StripResult]:
    """批量清理目录下所有支持的文件。

    Args:
        path: 目录路径。
        mode: "selective" 或 "full"。
        config: 清理配置。
        extensions: 限制处理的文件扩展名列表。
        inplace: 是否原地修改文件。

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
                file_path, mode=mode, config=config, inplace=inplace
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
    "StripEngine",
    "LanguagePlugin",
    "LanguageRegistry",
]
```

- [ ] **Step 6: 运行测试验证通过**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest tests/unit/test_engine.py -v`
Expected: all passed

- [ ] **Step 7: 运行全部测试**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest tests/ -v`
Expected: all passed

- [ ] **Step 8: 提交**

```bash
cd d:\WorkPlace\Pycharm\markstrip
git add markstrip/core/engine.py markstrip/languages/_builtin.py markstrip/__init__.py tests/unit/test_engine.py
git commit -m "feat: 添加 StripEngine、公共 API 和 entry_points 发现"
```

---

### Task 10: CLI 实现

**Files:**
- Create: `markstrip/cli.py`
- Test: `tests/integration/test_cli.py`

**Interfaces:**
- Consumes: `strip()`、`strip_file()`、`strip_directory()`（Task 9）
- Produces: `main()` CLI 入口函数

- [ ] **Step 1: 编写 CLI 测试**

```python
# tests/integration/test_cli.py
"""CLI 集成测试。"""
import subprocess
import sys
from pathlib import Path


def run_cli(*args) -> tuple[int, str, str]:
    """运行 markstrip CLI 并返回 (returncode, stdout, stderr)。"""
    result = subprocess.run(
        [sys.executable, "-m", "markstrip.cli", *args],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def test_cli_help():
    code, out, err = run_cli("--help")
    assert code == 0
    assert "markstrip" in out
    assert "--mode" in out


def test_cli_strip_file(tmp_path):
    # 创建测试文件
    test_file = tmp_path / "test.py"
    test_file.write_text("# @internal 删除\nx = 1\n", encoding="utf-8")

    # 运行 CLI
    code, out, err = run_cli(str(test_file), "--dry-run")
    assert code == 0
    assert "# @internal" not in out
    assert "x = 1" in out


def test_cli_output_to_file(tmp_path):
    test_file = tmp_path / "input.py"
    test_file.write_text("# @internal 删除\nx = 1\n", encoding="utf-8")
    output_file = tmp_path / "output.py"

    code, out, err = run_cli(
        str(test_file), "--output", str(output_file)
    )
    assert code == 0
    result = output_file.read_text(encoding="utf-8")
    assert "# @internal" not in result
    assert "x = 1" in result


def test_cli_recursive_directory(tmp_path):
    # 创建目录结构
    subdir = tmp_path / "sub"
    subdir.mkdir()
    file1 = tmp_path / "a.py"
    file1.write_text("# @internal 删除\nx = 1\n", encoding="utf-8")
    file2 = subdir / "b.py"
    file2.write_text("# @internal 删除\ny = 2\n", encoding="utf-8")

    code, out, err = run_cli(str(tmp_path), "--recursive", "--dry-run")
    assert code == 0
    assert "x = 1" in out
    assert "y = 2" in out


def test_cli_custom_marker(tmp_path):
    test_file = tmp_path / "test.py"
    test_file.write_text("# @private 删除\nx = 1\n", encoding="utf-8")

    code, out, err = run_cli(
        str(test_file), "--dry-run", "--marker", "@private"
    )
    assert code == 0
    assert "# @private" not in out
    assert "x = 1" in out


def test_cli_full_mode(tmp_path):
    test_file = tmp_path / "test.py"
    test_file.write_text("# 普通注释\nx = 1\n", encoding="utf-8")

    code, out, err = run_cli(
        str(test_file), "--dry-run", "--mode", "full"
    )
    assert code == 0
    assert "#" not in out
    assert "x = 1" in out
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest tests/integration/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'markstrip.cli'`

- [ ] **Step 3: 实现 CLI**

```python
# markstrip/cli.py
"""markstrip 命令行工具。"""
import argparse
import sys
from pathlib import Path

from markstrip.core.config import StripConfig
from markstrip.core.result import StripResult


def main(argv: list[str] | None = None) -> int:
    """CLI 主入口。

    Args:
        argv: 命令行参数，为 None 时使用 sys.argv。

    Returns:
        退出码，0 表示成功。
    """
    parser = argparse.ArgumentParser(
        prog="markstrip",
        description="标记式选择性注释过滤工具",
    )
    parser.add_argument("path", help="文件或目录路径")
    parser.add_argument(
        "--mode",
        choices=["selective", "full"],
        default="selective",
        help="清理模式：selective（标记过滤）或 full（全量删除）",
    )
    parser.add_argument(
        "--marker",
        default="@internal",
        help="行级标记符号（默认: @internal）",
    )
    parser.add_argument(
        "--docstring-marker",
        default="@internal-docstring",
        help="整体 docstring 标记符号",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式，不修改文件，输出清理结果到 stdout",
    )
    parser.add_argument(
        "--output", "-o",
        help="输出文件路径（仅单文件模式）",
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
    args = parser.parse_args(argv)

    config = StripConfig(
        line_marker=args.marker,
        docstring_marker=args.docstring_marker,
        preserve_docstrings=args.preserve_docstrings,
    )

    target = Path(args.path)

    if target.is_dir():
        if not args.recursive:
            print(f"错误: {target} 是目录，请使用 --recursive", file=sys.stderr)
            return 1
        _process_directory(target, args, config)
    elif target.is_file():
        _process_single_file(target, args, config)
    else:
        print(f"错误: {target} 不存在", file=sys.stderr)
        return 1

    return 0


def _process_single_file(
    path: Path, args: argparse.Namespace, config: StripConfig
) -> None:
    """处理单个文件。"""
    from markstrip import strip

    content = path.read_text(encoding="utf-8")
    result = strip(content, filename=str(path), mode=args.mode, config=config)

    if args.verbose:
        print(
            f"Processing {path}... removed {result.removed_count} lines",
            file=sys.stderr,
        )

    if args.dry_run:
        print(result.cleaned_content, end="")
    elif args.output:
        Path(args.output).write_text(
            result.cleaned_content, encoding="utf-8"
        )
    else:
        path.write_text(result.cleaned_content, encoding="utf-8")


def _process_directory(
    path: Path, args: argparse.Namespace, config: StripConfig
) -> None:
    """递归处理目录。"""
    from markstrip import strip_file

    total_removed = 0
    total_files = 0

    for file_path in path.rglob("*"):
        if not file_path.is_file():
            continue
        # 跳过不支持的文件
        ext = file_path.suffix.lower()
        if ext not in (".py", ".pyw", ".pyi", ".md", ".markdown"):
            continue

        content = file_path.read_text(encoding="utf-8")
        from markstrip import strip
        result = strip(
            content, filename=str(file_path), mode=args.mode, config=config
        )

        if args.verbose:
            print(
                f"Processing {file_path}... "
                f"removed {result.removed_count} lines",
                file=sys.stderr,
            )

        total_removed += result.removed_count
        total_files += 1

        if not args.dry_run:
            file_path.write_text(
                result.cleaned_content, encoding="utf-8"
            )

    if args.verbose:
        print(
            f"Total: {total_removed} lines removed from {total_files} files",
            file=sys.stderr,
        )


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest tests/integration/test_cli.py -v`
Expected: all passed

- [ ] **Step 5: 运行全部测试**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest tests/ -v`
Expected: all passed

- [ ] **Step 6: 提交**

```bash
cd d:\WorkPlace\Pycharm\markstrip
git add markstrip/cli.py tests/integration/test_cli.py
git commit -m "feat: 添加 CLI 命令行工具"
```

---

### Task 11: 最终验证和 .gitignore

**Files:**
- Create: `.gitignore`
- Verify: 全部测试通过、CLI 可用

- [ ] **Step 1: 创建 .gitignore**

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
dist/
build/
.eggs/

# Virtual environments
.venv/
venv/
env/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/

# OS
.DS_Store
Thumbs.db
```

- [ ] **Step 2: 运行全部测试**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest tests/ -v`
Expected: all passed

- [ ] **Step 3: 验证 CLI 可用**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; python -m markstrip.cli --help`
Expected: 输出帮助信息，包含 `--mode`、`--marker`、`--dry-run` 等选项

- [ ] **Step 4: 提交**

```bash
cd d:\WorkPlace\Pycharm\markstrip
git add .gitignore
git commit -m "chore: 添加 .gitignore 并完成最终验证"
```