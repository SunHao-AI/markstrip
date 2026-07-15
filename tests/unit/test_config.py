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
