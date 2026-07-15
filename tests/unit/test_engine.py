# tests/unit/test_engine.py
"""StripEngine 单元测试。"""
from pathlib import Path
from tempfile import NamedTemporaryFile

from markstrip import strip, strip_file, register_plugin
from markstrip.core.config import StripConfig
from markstrip.core.result import StripResult


def test_strip_by_language():
    content = "# @internal 删除\nx = 1\n"
    result = strip(content, language="python", mode="selective")
    assert "# @internal" not in result.cleaned_content
    assert result.detected_language == "python"
    assert result.removed_count >= 1


def test_strip_by_filename():
    content = "# @internal 删除\nx = 1\n"
    result = strip(content, filename="test.py")
    assert result.detected_language == "python"


def test_strip_markdown_by_filename():
    content = "```python\n# @internal 删除\nx = 1\n```\n"
    result = strip(content, filename="test.md")
    assert result.detected_language == "markdown"
    assert "# @internal" not in result.cleaned_content


def test_strip_unknown_language():
    content = "some content"
    result = strip(content, language="rust")
    assert result.cleaned_content == content
    assert result.removed_count == 0
    assert len(result.warnings) > 0


def test_strip_full_mode():
    content = "# 注释\nx = 1\n"
    result = strip(content, language="python", mode="full")
    assert "#" not in result.cleaned_content


def test_strip_file():
    with NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write("# @internal 删除\nx = 1\n")
        f.flush()
        result = strip_file(f.name)
    assert "# @internal" not in result.cleaned_content


def test_strip_file_inplace():
    with NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write("# @internal 删除\nx = 1\n")
        f.flush()
        path = f.name

    strip_file(path, inplace=True)
    content = Path(path).read_text(encoding="utf-8")
    assert "# @internal" not in content


def test_custom_config():
    content = "# @private 删除\nx = 1\n"
    config = StripConfig(line_marker="@private")
    result = strip(content, language="python", config=config)
    assert "# @private" not in result.cleaned_content
