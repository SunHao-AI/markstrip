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
