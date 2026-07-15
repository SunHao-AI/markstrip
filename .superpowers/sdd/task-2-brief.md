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
