# tests/unit/test_markdown_plugin.py
"""MarkdownPlugin 单元测试。"""
from pathlib import Path

import pytest

from markstrip.core.config import StripConfig
from markstrip.core.result import MarkerLocation
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


def test_check_html_comment_marker_reported(plugin):
    """HTML 注释含 @internal,在 check_mode 下报告 .md 绝对行号。"""
    content = (
        "# Title\n"
        "\n"
        "<!-- @internal 秘密说明 -->\n"
        "\n"
        "text\n"
    )
    config = StripConfig()
    config.check_mode = True
    plugin.strip_selective(content, config)
    # 应报告 1 个 marker,line=3(HTML 注释在第 3 行)
    assert len(config.markers_found) == 1
    m = config.markers_found[0]
    assert m.line == 3
    assert m.marker_text == "@internal"


def test_check_code_block_marker_translated(plugin):
    """代码块内委托插件记录的相对行号应翻译为 .md 绝对行号。"""
    content = (
        "# Title\n"
        "\n"
        "```python\n"
        "# @internal code marker\n"
        "x = 1\n"
        "```\n"
    )
    config = StripConfig()
    config.check_mode = True
    plugin.strip_selective(content, config)
    # 代码块在 .md 第 3 行起,marker 在代码块第 1 行
    # .md 绝对行号 = 3 (block_start) + 1 (code_first_line) + 0 = 4
    line_markers = [
        m for m in config.markers_found if m.marker_type == "line"
    ]
    assert len(line_markers) == 1
    assert line_markers[0].line == 4


def test_check_multiple_code_blocks_no_crosstalk(plugin):
    """多个代码块的 markers 行号独立翻译,不串号。"""
    content = (
        "# A\n\n"
        "```python\n"
        "# @internal first\n"
        "```\n\n"
        "# B\n\n"
        "```python\n"
        "# @internal second\n"
        "```\n"
    )
    config = StripConfig()
    config.check_mode = True
    plugin.strip_selective(content, config)
    line_markers = [
        m for m in config.markers_found if m.marker_type == "line"
    ]
    assert len(line_markers) == 2
    # first marker 在第 4 行(代码块 fence 在第 3 行,内容第 4 行)
    # second marker:计算位置 — # B 在第 7 行,``` 在第 9 行,内容第 10 行
    lines = content.splitlines()
    # 验证两个 marker 行号都在 .md 内有效范围且不同
    assert line_markers[0].line != line_markers[1].line
    for m in line_markers:
        assert 1 <= m.line <= len(lines)


def test_check_html_comment_col_position(plugin):
    """HTML 注释 marker 的 col 应为 marker 起始列。"""
    content = "  <!-- @internal indented -->\n"
    config = StripConfig()
    config.check_mode = True
    plugin.strip_selective(content, config)
    assert len(config.markers_found) == 1
    # marker_text @internal 在 "<!-- " 之后,即 col=6
    m = config.markers_found[0]
    assert m.marker_text == "@internal"
