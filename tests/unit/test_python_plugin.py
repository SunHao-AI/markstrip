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


def test_block_with_custom_line_marker_derives_block_markers(plugin):
    """line_marker=@private 时块标记应自动派生为 @private-start/-end。"""
    config = StripConfig(line_marker="@private")
    content = (
        "# @private-start\n"
        "# inside\n"
        "# @private-end\n"
        "x = 1\n"
    )
    result = plugin.strip_selective(content, config)
    assert result == "x = 1\n"
    assert "@private" not in result


class TestPragmaDelegation:
    """文件级 pragma 经 strip_selective 委托至 strip_full 的路径覆盖。

    覆盖 python_plugin.strip_selective 中的 scan_file_pragma → strip_full
    委托路径,该路径被 golden 路由分流至 test_python_full_golden 而跳过。
    """

    def test_delegates_and_removes_comments(self, plugin, config):
        """文件级 pragma 触发委托:删注释、保留 shebang/coding/docstring/代码。"""
        content = (
            "#!/usr/bin/env python3\n"
            "# -*- coding: utf-8 -*-\n"
            "# markstrip: full\n"
            "# 普通注释\n"
            "x = 1  # 行尾注释\n"
            'def f():\n'
            '    """docstring"""\n'
            '    return 1\n'
        )
        result = plugin.strip_selective(content, config)
        # 普通注释被删除
        assert "普通注释" not in result
        # 行尾注释被删除
        assert "行尾注释" not in result
        # shebang 被保留
        assert "#!/usr/bin/env python3" in result
        # coding 声明被保留
        assert "coding: utf-8" in result
        # docstring 被保留(默认 preserve_docstrings=True)
        assert '"""docstring"""' in result
        # pragma 行本身被删除
        assert "markstrip: full" not in result
        # 代码保留
        assert "x = 1" in result
        assert "return 1" in result

    def test_redundant_range_pragma_warns(self, plugin, config):
        """文件级 full 与区间标记共存时产生冗余警告。"""
        content = (
            "# markstrip: full\n"
            "# markstrip: full-start\n"
            "# 注释\n"
            "# markstrip: full-end\n"
            "x = 1\n"
        )
        plugin.strip_selective(content, config)
        assert "文件级 full 已生效, 区间标记冗余" in config.warnings
