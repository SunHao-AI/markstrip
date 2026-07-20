"""StripResult 单元测试。"""
from markstrip.core.result import MarkerLocation, StripResult


def test_basic_result():
    result = StripResult(
        cleaned_content="hello",
        removed_count=3,
    )
    assert result.cleaned_content == "hello"
    assert result.removed_count == 3
    assert result.detected_language == ""
    assert result.warnings == []


def test_result_with_warnings():
    result = StripResult(
        cleaned_content="hello",
        removed_count=0,
        detected_language="python",
        warnings=["无法识别语言"],
    )
    assert result.detected_language == "python"
    assert result.warnings == ["无法识别语言"]


def test_warnings_independent():
    r1 = StripResult(cleaned_content="", removed_count=0)
    r2 = StripResult(cleaned_content="", removed_count=0)
    r1.warnings.append("test")
    assert r2.warnings == []


def test_marker_location_basic():
    m = MarkerLocation(
        line=12,
        col=5,
        marker_type="line",
        marker_text="@internal",
        content_preview="# @internal 使用 TensorRT",
    )
    assert m.line == 12
    assert m.col == 5
    assert m.marker_type == "line"
    assert m.marker_text == "@internal"
    assert m.content_preview == "# @internal 使用 TensorRT"


def test_marker_location_types():
    """覆盖所有合法 marker_type 值。"""
    for t in ("line", "block-start", "block-end",
              "docstring-whole", "docstring-line"):
        m = MarkerLocation(
            line=1, col=0, marker_type=t,
            marker_text="@internal", content_preview="x",
        )
        assert m.marker_type == t
