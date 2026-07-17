"""BlockScanner 单元测试。"""
from markstrip.core.block_scanner import (
    BlockRange,
    BlockScanResult,
    scan_blocks,
)


def test_single_block():
    lines = [
        "# @internal-start\n",
        "# inside\n",
        "# @internal-end\n",
    ]
    result = scan_blocks(lines, "#", "@internal-start", "@internal-end")
    assert result.ranges == [BlockRange(1, 3)]
    assert result.warnings == []


def test_multiple_blocks():
    lines = [
        "# @internal-start\n",
        "# a\n",
        "# @internal-end\n",
        "# keep\n",
        "# @internal-start\n",
        "# b\n",
        "# @internal-end\n",
    ]
    result = scan_blocks(lines, "#", "@internal-start", "@internal-end")
    assert result.ranges == [BlockRange(1, 3), BlockRange(5, 7)]
    assert result.warnings == []


def test_start_without_end():
    lines = [
        "# @internal-start\n",
        "# inside\n",
    ]
    result = scan_blocks(lines, "#", "@internal-start", "@internal-end")
    assert result.ranges == []
    assert len(result.warnings) == 1
    assert "行 1" in result.warnings[0]
    assert "@internal-end" in result.warnings[0]


def test_end_without_start():
    lines = [
        "# inside\n",
        "# @internal-end\n",
    ]
    result = scan_blocks(lines, "#", "@internal-start", "@internal-end")
    assert result.ranges == []
    assert len(result.warnings) == 1
    assert "行 2" in result.warnings[0]
    assert "@internal-start" in result.warnings[0]


def test_nested_start_ignored_with_warning():
    lines = [
        "# @internal-start\n",
        "# @internal-start\n",
        "# inside\n",
        "# @internal-end\n",
    ]
    result = scan_blocks(lines, "#", "@internal-start", "@internal-end")
    assert result.ranges == [BlockRange(1, 4)]
    assert len(result.warnings) == 1
    assert "行 2" in result.warnings[0]
    assert "嵌套" in result.warnings[0]


def test_custom_prefix_slash_slash():
    lines = [
        "// @internal-start\n",
        "// inside\n",
        "// @internal-end\n",
    ]
    result = scan_blocks(lines, "//", "@internal-start", "@internal-end")
    assert result.ranges == [BlockRange(1, 3)]
    assert result.warnings == []


def test_marker_with_suffix_not_matched():
    """@internal-started 不应被识别为 start。"""
    lines = [
        "# @internal-started\n",
        "# @internal-end\n",
    ]
    result = scan_blocks(lines, "#", "@internal-start", "@internal-end")
    assert result.ranges == []
    assert len(result.warnings) == 1  # end 无匹配 start


def test_indented_delimiter():
    """缩进的定界行应被识别。"""
    lines = [
        "    # @internal-start\n",
        "    # inside\n",
        "    # @internal-end\n",
    ]
    result = scan_blocks(lines, "#", "@internal-start", "@internal-end")
    assert result.ranges == [BlockRange(1, 3)]
    assert result.warnings == []


def test_delimiter_with_trailing_text_allowed():
    """定界行标记后允许有说明文字。"""
    lines = [
        "# @internal-start ここから内部\n",
        "# inside\n",
        "# @internal-end ここまで\n",
    ]
    result = scan_blocks(lines, "#", "@internal-start", "@internal-end")
    assert result.ranges == [BlockRange(1, 3)]
    assert result.warnings == []


def test_custom_derived_markers():
    """scan_blocks 接收任意 marker，验证 @private 联动。"""
    lines = [
        "# @private-start\n",
        "# inside\n",
        "# @private-end\n",
    ]
    result = scan_blocks(lines, "#", "@private-start", "@private-end")
    assert result.ranges == [BlockRange(1, 3)]
    assert result.warnings == []


def test_blockscan_result_dataclass():
    r = BlockScanResult(ranges=[BlockRange(1, 2)], warnings=["w"])
    assert r.ranges[0].start_line == 1
    assert r.ranges[0].end_line == 2
    assert r.warnings == ["w"]
