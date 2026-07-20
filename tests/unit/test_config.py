"""StripConfig 单元测试。"""
from markstrip.core.config import StripConfig
from markstrip.core.result import MarkerLocation


def test_default_config():
    config = StripConfig()
    assert config.line_marker == "@internal"
    assert config.docstring_marker == ""
    assert config.block_start_marker == ""
    assert config.block_end_marker == ""
    assert config.preserve_docstrings is True
    assert config.preserve_todo is True
    assert config.custom_markers == []
    assert config.warnings == []


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


def test_default_derived_markers():
    """默认 line_marker=@internal 时派生标记与现状一致。"""
    config = StripConfig()
    assert config.docstring_marker == ""
    assert config.block_start_marker == ""
    assert config.block_end_marker == ""
    assert config.effective_docstring_marker() == "@internal-docstring"
    assert config.effective_block_start() == "@internal-start"
    assert config.effective_block_end() == "@internal-end"


def test_custom_line_marker_derives_all():
    """改 line_marker → 三类派生标记联动。"""
    config = StripConfig(line_marker="@private")
    assert config.effective_docstring_marker() == "@private-docstring"
    assert config.effective_block_start() == "@private-start"
    assert config.effective_block_end() == "@private-end"


def test_explicit_overrides_derivation():
    """显式设置非空值时不走派生。"""
    config = StripConfig(
        line_marker="@internal",
        docstring_marker="@secret-doc",
        block_start_marker="@secret-begin",
        block_end_marker="@secret-end",
    )
    assert config.effective_docstring_marker() == "@secret-doc"
    assert config.effective_block_start() == "@secret-begin"
    assert config.effective_block_end() == "@secret-end"


def test_warnings_default_empty():
    config = StripConfig()
    assert config.warnings == []


def test_warnings_independent():
    """每个 StripConfig 实例的 warnings 应独立。"""
    c1 = StripConfig()
    c2 = StripConfig()
    c1.warnings.append("x")
    assert c2.warnings == []


def test_config_markers_found_default_empty():
    config = StripConfig()
    assert config.markers_found == []
    assert config.check_mode is False


def test_config_markers_found_transient():
    """markers_found 是普通 list,可直接 append/clear。"""
    config = StripConfig()
    m = MarkerLocation(
        line=1, col=0, marker_type="line",
        marker_text="@internal", content_preview="x",
    )
    config.markers_found.append(m)
    assert len(config.markers_found) == 1
    config.markers_found.clear()
    assert config.markers_found == []
