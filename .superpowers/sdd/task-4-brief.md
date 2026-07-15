### Task 4: PythonPlugin - selective 模式（行注释）

**Files:**
- Create: `markstrip/languages/python_plugin.py`
- Test: `tests/unit/test_python_plugin.py`
- Golden: `tests/golden/python/internal_comment.py`, `tests/golden/python/internal_comment.expected.py`, `tests/golden/python/string_with_hash.py`, `tests/golden/python/string_with_hash.expected.py`
- Create: `tests/conftest.py`

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
