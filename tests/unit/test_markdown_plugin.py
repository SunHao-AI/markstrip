# tests/unit/test_markdown_plugin.py
"""MarkdownPlugin 单元测试。"""
from pathlib import Path

import pytest

from markstrip.core.config import StripConfig
from markstrip.languages.markdown_plugin import MarkdownPlugin
from markstrip.languages.python_plugin import PythonPlugin
from markstrip.languages.registry import LanguageRegistry
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
