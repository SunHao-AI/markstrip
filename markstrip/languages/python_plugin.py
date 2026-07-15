"""Python 语言插件。"""
import re
import tokenize

from markstrip.core.config import StripConfig
from markstrip.languages.base import LanguagePlugin


class PythonPlugin(LanguagePlugin):
    """Python 语言插件。

    使用 tokenize 词法分析精确定位注释和文档字符串，
    避免误删字符串中的 # 符号。
    """

    @property
    def name(self) -> str:
        return "python"

    @property
    def file_extensions(self) -> list[str]:
        return [".py", ".pyw", ".pyi"]

    def strip_selective(self, content: str, config: StripConfig) -> str:
        """标记式选择性过滤：仅删除含 @internal 标记的注释。

        Args:
            content: Python 源代码内容。
            config: 清理配置。

        Returns:
            清理后的内容。
        """
        lines = content.splitlines(keepends=True)
        # 收集标记注释的精确位置：(行号, 起始列, 结束列)
        comment_removals: list[tuple[int, int, int]] = []

        # tokenize 识别注释
        try:
            tokens = list(tokenize.tokenize(
                iter(content.encode("utf-8").splitlines(True)).__next__
            ))
        except tokenize.TokenizeError:
            return self._fallback_regex_selective(content, config)

        for tok in tokens:
            if tok.type == tokenize.COMMENT:
                if self._has_marker(tok.string, config):
                    comment_removals.append(
                        (tok.start[0], tok.start[1], tok.end[1])
                    )

        # 行级重组：删除标记注释文本，保留非注释代码
        return self._rebuild(lines, comment_removals)

    def strip_full(self, content: str, config: StripConfig) -> str:
        """全量注释删除。"""
        # Task 6 实现
        return content

    def _has_marker(self, comment_text: str, config: StripConfig) -> bool:
        """检查注释是否包含标记。

        Args:
            comment_text: 注释文本（含 # 前缀）。
            config: 清理配置。

        Returns:
            是否包含标记。
        """
        markers = [config.line_marker] + config.custom_markers
        # 去掉 # 前缀后检查
        stripped = comment_text.lstrip("#").strip()
        for marker in markers:
            if stripped.startswith(marker):
                return True
        return False

    def _rebuild(
        self,
        lines: list[str],
        comment_removals: list[tuple[int, int, int]],
    ) -> str:
        """按注释位置重组代码，保留非注释部分。

        Args:
            lines: 原始行列表（splitlines(keepends=True)）。
            comment_removals: 需要删除的注释信息列表
                (行号, 起始列, 结束列)，1-based 行号，0-based 列。

        Returns:
            重组后的内容。
        """
        if not comment_removals:
            return "".join(lines)

        # 按行号分组
        removals_by_line: dict[int, list[tuple[int, int]]] = {}
        for line_num, start_col, end_col in comment_removals:
            removals_by_line.setdefault(line_num, []).append(
                (start_col, end_col)
            )

        result = []
        for i, line in enumerate(lines, start=1):
            if i not in removals_by_line:
                result.append(line)
                continue

            # 处理含标记注释的行
            # 分离换行符和内容
            newline = ""
            content_part = line
            if line.endswith("\r\n"):
                newline = "\r\n"
                content_part = line[:-2]
            elif line.endswith("\n"):
                newline = "\n"
                content_part = line[:-1]
            elif line.endswith("\r"):
                newline = "\r"
                content_part = line[:-1]

            # 按列位置从后往前删除注释文本
            removals = sorted(removals_by_line[i], reverse=True)
            for start_col, end_col in removals:
                before = content_part[:start_col]
                after = content_part[end_col:]
                content_part = before + after

            # 删除注释后只剩空白 → 整行变空（保留换行符）
            if content_part.strip() == "":
                content_part = ""
            else:
                # 去除行尾多余空白
                content_part = content_part.rstrip()

            result.append(content_part + newline)

        return "".join(result)

    def _fallback_regex_selective(
        self, content: str, config: StripConfig
    ) -> str:
        """tokenize 失败时的正则回退。

        Args:
            content: 源代码内容。
            config: 清理配置。

        Returns:
            清理后的内容。
        """
        marker = re.escape(config.line_marker)
        pattern = rf"^\s*#\s*{marker}.*$\n?"
        return re.sub(pattern, "", content, flags=re.MULTILINE)
