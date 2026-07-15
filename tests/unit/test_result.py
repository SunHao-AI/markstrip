"""StripResult 单元测试。"""
from markstrip.core.result import StripResult


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
