"""Python 语言插件。"""
import ast
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
        except tokenize.TokenError:
            return self._fallback_regex_selective(content, config)

        for tok in tokens:
            if tok.type == tokenize.COMMENT:
                if self._has_marker(tok.string, config):
                    comment_removals.append(
                        (tok.start[0], tok.start[1], tok.end[1])
                    )

            if tok.type == tokenize.STRING:
                if self._is_docstring(tok, tokens):
                    doc_removals = self._process_docstring(tok, config, lines)
                    comment_removals.extend(doc_removals)

        # 行级重组：删除标记注释文本，保留非注释代码
        return self._rebuild(lines, comment_removals)

    def strip_full(self, content: str, config: StripConfig) -> str:
        """全量注释删除：删除所有注释，保留 shebang/TODO 等。

        Args:
            content: Python 源代码内容。
            config: 清理配置。

        Returns:
            清理后的内容。
        """
        lines = content.splitlines(keepends=True)
        comment_removals: list[tuple[int, int, int]] = []

        try:
            tokens = list(tokenize.tokenize(
                iter(content.encode("utf-8").splitlines(True)).__next__
            ))
        except tokenize.TokenError:
            # 语法错误时无法处理，直接返回原内容
            return content

        for tok in tokens:
            if tok.type == tokenize.COMMENT:
                if self._is_preserved_comment(tok, config):
                    continue
                # 列号为 0 的注释（整行只有注释）→ 删除整行
                if tok.start[1] == 0:
                    comment_removals.append((tok.start[0], 0, -1))
                else:
                    # 列级删除：(行号, 起始列, 结束列)
                    comment_removals.append(
                        (tok.start[0], tok.start[1], tok.end[1])
                    )

            if tok.type == tokenize.STRING:
                if self._is_docstring(tok, tokens):
                    if not config.preserve_docstrings:
                        # 删除整个 docstring 的所有行
                        for line_num in range(tok.start[0], tok.end[0] + 1):
                            comment_removals.append((line_num, 0, -1))

        return self._rebuild(lines, comment_removals)

    def _is_preserved_comment(
        self,
        tok: tokenize.TokenInfo,
        config: StripConfig,
    ) -> bool:
        """判断注释是否应被保留（full 模式）。

        Args:
            tok: COMMENT token。
            config: 清理配置。

        Returns:
            True 表示保留，False 表示删除。
        """
        text = tok.string.strip()
        # 保留 shebang
        if text.startswith("#!"):
            return True
        # 保留编码声明
        if "coding:" in text or "coding=" in text:
            return True
        # 保留 TODO/FIXME
        if config.preserve_todo and (
            "TODO" in text or "FIXME" in text
        ):
            return True
        # 保留类型注释
        if text.startswith("# type:"):
            return True
        return False

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

    def _is_docstring(
        self,
        tok: tokenize.TokenInfo,
        tokens: list[tokenize.TokenInfo],
    ) -> bool:
        """判断 STRING token 是否为 docstring。

        docstring 是模块、类或函数体的首条语句。

        Args:
            tok: 待判断的 token。
            tokens: 完整 token 列表。

        Returns:
            是否为 docstring。
        """
        # 简化判断：三引号字符串且前一个非空 token 是 NEWLINE/INDENT/DEDENT
        # 或位于文件开头
        idx = tokens.index(tok)
        # 向前查找第一个非 NL/NEWLINE token
        prev_idx = idx - 1
        while prev_idx >= 0 and tokens[prev_idx].type in (
            tokenize.NL,
            tokenize.NEWLINE,
        ):
            prev_idx -= 1

        if prev_idx < 0:
            # 文件开头，是模块 docstring
            return True

        prev = tokens[prev_idx]
        # 前一个是 INDENT 或 DEDENT → 可能是函数/类体首语句
        if prev.type in (tokenize.INDENT, tokenize.DEDENT):
            return True
        # 前一个是冒号 → 函数/类定义后的首语句
        if prev.type == tokenize.OP and prev.string == ":":
            return True
        # 简化：多行字符串（含换行）也可能是 docstring
        if "\n" in tok.string:
            return True
        return False

    def _process_docstring(
        self,
        tok: tokenize.TokenInfo,
        config: StripConfig,
        lines: list[str],
    ) -> list[tuple[int, int, int]]:
        """处理单个 docstring，返回需删除的位置。

        Args:
            tok: docstring 的 STRING token。
            config: 清理配置。
            lines: 原始行列表。

        Returns:
            需要删除的 (line_num, start_col, end_col) 列表。
            end_col=-1 表示删除整行（含换行符）。
        """
        try:
            content = ast.literal_eval(tok.string)
        except (ValueError, SyntaxError):
            return []

        doc_lines = content.split("\n")

        # 检查 @internal-docstring 标记（整体删除）
        # 扫描所有行以支持标记不在首行的情况
        has_whole_marker = any(
            line.strip().startswith(config.docstring_marker)
            for line in doc_lines
        )
        if has_whole_marker:
            # 删除整个 docstring 的所有行
            removals = []
            for line_num in range(tok.start[0], tok.end[0] + 1):
                removals.append((line_num, 0, -1))  # -1 = 删除整行
            return removals

        # 逐行检查 @internal 标记
        markers = [config.line_marker] + config.custom_markers
        removals: list[tuple[int, int, int]] = []
        for i, line in enumerate(doc_lines):
            stripped = line.strip()
            for marker in markers:
                if stripped.startswith(marker):
                    # 映射到源文件行号，清空该行内容（保留空行）
                    source_line = tok.start[0] + i
                    # 获取该行的长度（不含换行符）
                    if source_line - 1 < len(lines):
                        line_content = lines[source_line - 1].rstrip("\r\n")
                        removals.append(
                            (source_line, 0, len(line_content))
                        )
                    break

        return removals

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
                end_col=-1 表示删除整行（含换行符）。

        Returns:
            重组后的内容。
        """
        if not comment_removals:
            return "".join(lines)

        # 按行号分组
        removals_by_line: dict[int, list[tuple[int, int]]] = {}
        full_line_removals: set[int] = set()

        for line_num, start_col, end_col in comment_removals:
            if end_col == -1:
                full_line_removals.add(line_num)
            else:
                removals_by_line.setdefault(line_num, []).append(
                    (start_col, end_col)
                )

        result = []
        for i, line in enumerate(lines, start=1):
            if i in full_line_removals:
                # 删除整行（含换行符）
                continue

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

        注意：正则无法区分字符串中的 # 和注释 #，此为已知限制。
        仅在 tokenize 失败（语法错误）时触发。

        Args:
            content: 源代码内容。
            config: 清理配置。

        Returns:
            清理后的内容。
        """
        markers = [config.line_marker] + config.custom_markers
        marker_alt = "|".join(re.escape(m) for m in markers)

        # 第一遍：删除整行标记注释（含换行符）
        full_pattern = rf"^\s*#\s*(?:{marker_alt}).*$\n?"
        content = re.sub(full_pattern, "", content, flags=re.MULTILINE)

        # 第二遍：删除行内标记注释（仅注释部分，保留前面的代码）
        inline_pattern = rf"\s*#\s*(?:{marker_alt}).*$"
        content = re.sub(inline_pattern, "", content, flags=re.MULTILINE)

        return content
