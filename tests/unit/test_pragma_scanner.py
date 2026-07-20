"""pragma_scanner 单元测试。"""
from markstrip.core.pragma_scanner import scan_file_pragma


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



