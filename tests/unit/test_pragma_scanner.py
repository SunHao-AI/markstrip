"""pragma_scanner 单元测试。"""
from markstrip.core.pragma_scanner import scan_file_pragma, scan_full_ranges


class TestScanFilePragma:
    """文件级 pragma 检测。"""

    def test_pragma_present(self):
        lines = ["# markstrip: full\n", "x = 1\n"]
        assert scan_file_pragma(lines, "#") is True

    def test_pragma_absent(self):
        lines = ["# 普通注释\n", "x = 1\n"]
        assert scan_file_pragma(lines, "#") is False

    def test_no_space_around_colon(self):
        lines = ["#markstrip:full\n"]
        assert scan_file_pragma(lines, "#") is True

    def test_extra_spaces(self):
        lines = ["#  markstrip :  full  \n"]
        assert scan_file_pragma(lines, "#") is True

    def test_trailing_text(self):
        lines = ["# markstrip: full  本文件全量清理\n"]
        assert scan_file_pragma(lines, "#") is True

    def test_case_sensitive(self):
        lines = ["# Markstrip: full\n"]
        assert scan_file_pragma(lines, "#") is False

    def test_only_full_directive(self):
        """full-start/full-end 不被 scan_file_pragma 识别。"""
        lines = ["# markstrip: full-start\n"]
        assert scan_file_pragma(lines, "#") is False

    def test_custom_prefix(self):
        lines = ["// markstrip: full\n"]
        assert scan_file_pragma(lines, "//") is True

    def test_pragma_anywhere(self):
        lines = ["x = 1\n", "y = 2\n", "# markstrip: full\n", "z = 3\n"]
        assert scan_file_pragma(lines, "#") is True

    def test_typo_not_recognized(self):
        lines = ["# markstrip: ful\n"]
        assert scan_file_pragma(lines, "#") is False


class TestScanFullRanges:
    """区间级 pragma 扫描。"""

    def test_single_range(self):
        lines = [
            "# markstrip: full-start\n",
            "# 注释 A\n",
            "x = 1\n",
            "# markstrip: full-end\n",
        ]
        result = scan_full_ranges(lines, "#")
        assert len(result.ranges) == 1
        assert result.ranges[0].start_line == 1
        assert result.ranges[0].end_line == 4
        assert result.ranges[0].mode == "comments"
        assert result.warnings == []

    def test_multiple_ranges(self):
        lines = [
            "# markstrip: full-start\n",
            "# a\n",
            "# markstrip: full-end\n",
            "y = 2\n",
            "# markstrip: full-start\n",
            "# b\n",
            "# markstrip: full-end\n",
        ]
        result = scan_full_ranges(lines, "#")
        assert len(result.ranges) == 2
        assert result.warnings == []

    def test_orphan_end(self):
        lines = ["# markstrip: full-end\n"]
        result = scan_full_ranges(lines, "#")
        assert result.ranges == []
        assert len(result.warnings) == 1
        assert "孤立" in result.warnings[0]

    def test_unclosed_start(self):
        lines = ["# markstrip: full-start\n", "# a\n"]
        result = scan_full_ranges(lines, "#")
        assert result.ranges == []
        assert len(result.warnings) == 1
        assert "未闭合" in result.warnings[0]

    def test_nested_start_ignored(self):
        lines = [
            "# markstrip: full-start\n",
            "# markstrip: full-start\n",
            "# a\n",
            "# markstrip: full-end\n",
        ]
        result = scan_full_ranges(lines, "#")
        assert len(result.ranges) == 1
        assert result.ranges[0].start_line == 1
        assert result.ranges[0].end_line == 4
        assert len(result.warnings) == 1
        assert "嵌套" in result.warnings[0]

    def test_whitespace_variations(self):
        lines = ["#markstrip:full-start\n", "#a\n", "#markstrip:full-end\n"]
        result = scan_full_ranges(lines, "#")
        assert len(result.ranges) == 1
        assert result.ranges[0].mode == "comments"

    def test_custom_prefix(self):
        lines = ["// markstrip: full-start\n", "// a\n", "// markstrip: full-end\n"]
        result = scan_full_ranges(lines, "//")
        assert len(result.ranges) == 1

    def test_no_pragma(self):
        lines = ["# 普通注释\n", "x = 1\n"]
        result = scan_full_ranges(lines, "#")
        assert result.ranges == []
        assert result.warnings == []
