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


_selective_golden_cases = [
    (i, e) for i, e in collect_golden_cases("python")
    if "full" not in Path(i).stem
]


@pytest.mark.parametrize(
    "input_file,expected_file",
    _selective_golden_cases,
    ids=[Path(f).stem for f, _ in _selective_golden_cases],
)
def test_python_selective_golden(input_file, expected_file):
    plugin = PythonPlugin()
    config = StripConfig()
    content = Path(input_file).read_text(encoding="utf-8")
    expected = Path(expected_file).read_text(encoding="utf-8")
    result = plugin.strip_selective(content, config)
    assert result == expected


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


_full_golden_cases = [
    (i, e) for i, e in collect_golden_cases("python")
    if "full" in Path(i).stem
]


@pytest.mark.parametrize(
    "input_file,expected_file",
    _full_golden_cases,
    ids=[Path(f).stem for f, _ in _full_golden_cases],
)
def test_python_full_golden(input_file, expected_file):
    plugin = PythonPlugin()
    config = StripConfig()
    content = Path(input_file).read_text(encoding="utf-8")
    expected = Path(expected_file).read_text(encoding="utf-8")
    result = plugin.strip_full(content, config)
    assert result == expected
