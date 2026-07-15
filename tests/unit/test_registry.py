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
