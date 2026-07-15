"""PythonPlugin 单元测试。"""
from pathlib import Path

import pytest

from markstrip.core.config import StripConfig
from markstrip.languages.python_plugin import PythonPlugin
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
