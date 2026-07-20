"""PythonPlugin 单元测试。"""
from pathlib import Path

import pytest

from markstrip.core.config import StripConfig
from markstrip.core.result import MarkerLocation
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


def test_check_line_marker_reported(plugin):
    """行标记 @internal 在 check_mode 下被报告为 line 类型。"""
    config = StripConfig()
    config.check_mode = True
    plugin.strip_selective("# @internal 使用 TRT\nx = 1\n", config)
    assert len(config.markers_found) == 1
    m = config.markers_found[0]
    assert m.marker_type == "line"
    assert m.marker_text == "@internal"
    assert m.line == 1
    assert m.col == 0  # 顶格注释,col=0


def test_check_block_markers_reported(plugin):
    """块定界 @internal-start/-end 在 check_mode 下被报告为 block-start/block-end。"""
    config = StripConfig()
    config.check_mode = True
    plugin.strip_selective(
        "# @internal-start\n# inside\nx = 1\n# @internal-end\n",
        config,
    )
    types = [m.marker_type for m in config.markers_found]
    assert "block-start" in types
    assert "block-end" in types
    # 块内 collateral 代码行不报告
    assert len(config.markers_found) == 2


def test_check_docstring_whole_reported(plugin):
    """docstring 含 @internal-docstring 整体标记,在 check_mode 下报告 docstring-whole。"""
    content = 'def f():\n    """\n    @internal-docstring\n    """\n    return 1\n'
    config = StripConfig()
    config.check_mode = True
    plugin.strip_selective(content, config)
    types = [m.marker_type for m in config.markers_found]
    assert "docstring-whole" in types


def test_check_docstring_line_reported(plugin):
    """docstring 内行首 @internal,在 check_mode 下报告 docstring-line。"""
    content = 'def f():\n    """\n    @internal 逐行\n    other\n    """\n    return 1\n'
    config = StripConfig()
    config.check_mode = True
    plugin.strip_selective(content, config)
    types = [m.marker_type for m in config.markers_found]
    assert "docstring-line" in types


def test_check_custom_marker_reported(plugin):
    """自定义 marker 在 check_mode 下同步报告。"""
    config = StripConfig(line_marker="@private")
    config.check_mode = True
    plugin.strip_selective("# @private x\ny = 1\n", config)
    assert len(config.markers_found) == 1
    assert config.markers_found[0].marker_text == "@private"


def test_check_mode_skips_file_level_pragma(plugin):
    """check_mode=True 时,文件级 pragma 不委托 strip_full,@internal 仍被报告。"""
    content = (
        "# markstrip: full\n"
        "# @internal 这条仍要报告\n"
        "x = 1\n"
    )
    config = StripConfig()
    config.check_mode = True
    plugin.strip_selective(content, config)
    # 应报告 1 个 line marker(不被 file-level pragma 委托吞掉)
    line_markers = [
        m for m in config.markers_found if m.marker_type == "line"
    ]
    assert len(line_markers) == 1


def test_check_mode_pragma_not_reported(plugin):
    """pragma 指令本身不算违规,markers_found 不含 pragma 行。"""
    content = (
        "# markstrip: full\n"
        "x = 1\n"
    )
    config = StripConfig()
    config.check_mode = True
    plugin.strip_selective(content, config)
    assert config.markers_found == []


def test_check_mode_off_pragma_works(plugin):
    """check_mode=False(默认),pragma 正常生效,@internal 不报告(行为不变)。"""
    content = (
        "# markstrip: full\n"
        "# @internal 这条会被 pragma 委托的 strip_full 删掉,不报告\n"
        "x = 1\n"
    )
    config = StripConfig()
    config.check_mode = False
    plugin.strip_selective(content, config)
    assert config.markers_found == []


def test_content_preview_truncated(plugin):
    """content_preview 截断至 80 字符。"""
    long_line = "# @internal " + "x" * 200
    config = StripConfig()
    config.check_mode = True
    plugin.strip_selective(long_line + "\n", config)
    assert len(config.markers_found) == 1
    assert len(config.markers_found[0].content_preview) <= 80


def test_check_fallback_line_marker_reported():
    """tokenize 失败(语法错误)时,_fallback_regex_selective 仍回填 markers。"""
    # 语法错误代码:未闭合字符串字面量导致 tokenize 失败
    content = 'x = "abc\n# @internal x\ny = 1\n'
    config = StripConfig()
    config.check_mode = True
    plugin = PythonPlugin()
    plugin.strip_selective(content, config)
    line_markers = [
        m for m in config.markers_found if m.marker_type == "line"
    ]
    assert len(line_markers) == 1


def test_python_detect_typical_code(plugin):
    """典型 Python 代码应被识别。"""
    content = "import os\n\ndef f():\n    return 1\n"
    assert plugin.detect(content) is True


def test_python_detect_rejects_plain_text(plugin):
    """纯文本不应被识别为 Python。"""
    assert plugin.detect("just some text\n") is False
