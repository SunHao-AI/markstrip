"""Python 语言插件。"""
import ast
import re
import tokenize

from markstrip.core.block_scanner import scan_blocks
from markstrip.core.config import StripConfig
from markstrip.core.pragma_scanner import scan_file_pragma
from markstrip.core.result import MarkerLocation
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

    def detect(self, content: str) -> bool:
        """启发式判断内容是否为 Python 源代码。

        识别信号:行首 def/import/from/class/return 等关键字、
        `#` 注释占比、`:` 行尾(代码块)。

        Args:
            content: 待检测的内容。

        Returns:
            是否为 Python 代码。
        """
        lines = content.splitlines()
        if not lines:
            return False
        python_signals = 0
        for line in lines:
            stripped = line.lstrip()
            if any(
                stripped.startswith(kw)
                for kw in ("def ", "import ", "from ", "class ", "return ")
            ):
                python_signals += 1
            elif stripped.startswith("#"):
                python_signals += 1
            elif stripped.endswith(":") and not stripped.startswith("#"):
                python_signals += 1
        # 至少 1 个信号或占比 > 30% 才判定为 Python
        # (小文件如 `# @internal x\ny = 1\n` 仅 1 个 # 信号,
        # 阈值 2 会误判为 Markdown;Python 注册在 Markdown 之前,优先命中)
        threshold = max(1, len(lines) * 0.3)
        return python_signals >= threshold

    def strip_selective(self, content: str, config: StripConfig) -> str:
        """标记式选择性过滤:仅删除含标记的注释。

        支持逐行 @internal、块定界 @internal-start/-end、docstring 整体标记。
        纯注释标记行整行移除,内联标记注释仅删注释片段保留代码。

        check_mode=True 时,跳过 file-level pragma 委托,
        确保所有 @internal 标记被扫描回填至 config.markers_found。

        Args:
            content: Python 源代码内容。
            config: 清理配置。

        Returns:
            清理后的内容。
        """
        lines = content.splitlines(keepends=True)
        check_mode = config.check_mode
        # 文件级 pragma 检测(check_mode 时跳过委托,继续走 selective 扫描)
        if not check_mode and scan_file_pragma(lines, "#"):
            return self.strip_full(content, config)
        comment_removals: list[tuple[int, int, int]] = []

        # tokenize 识别注释
        try:
            tokens = list(tokenize.tokenize(
                iter(content.encode("utf-8").splitlines(True)).__next__
            ))
        except tokenize.TokenError:
            return self._fallback_regex_selective(content, config)

        # 块扫描
        scan = scan_blocks(
            lines,
            "#",
            config.effective_block_start(),
            config.effective_block_end(),
        )
        config.warnings.extend(scan.warnings)
        block_ranges = scan.ranges

        # check_mode:回填 block-start/block-end markers
        if check_mode:
            for r in block_ranges:
                start_line_text = lines[r.start_line - 1]
                end_line_text = lines[r.end_line - 1]
                # 计算 marker 起始列(定界行中 marker 第一个字符)
                start_col = start_line_text.find(
                    config.effective_block_start()
                )
                end_col = end_line_text.find(config.effective_block_end())
                config.markers_found.append(MarkerLocation(
                    line=r.start_line,
                    col=max(0, start_col),
                    marker_type="block-start",
                    marker_text=config.effective_block_start(),
                    content_preview=start_line_text.strip()[:80],
                ))
                config.markers_found.append(MarkerLocation(
                    line=r.end_line,
                    col=max(0, end_col),
                    marker_type="block-end",
                    marker_text=config.effective_block_end(),
                    content_preview=end_line_text.strip()[:80],
                ))

        def _in_block(line_num: int) -> bool:
            return any(
                r.start_line <= line_num <= r.end_line for r in block_ranges
            )

        for tok in tokens:
            if tok.type == tokenize.COMMENT:
                in_block = _in_block(tok.start[0])
                if in_block:
                    # 块内:纯注释整行移除,内联仅删片段
                    if self._is_whole_line_comment(tok, lines):
                        comment_removals.append((tok.start[0], 0, -1))
                    else:
                        comment_removals.append(
                            (tok.start[0], tok.start[1], tok.end[1])
                        )
                elif self._has_marker(tok.string, config):
                    # 块外逐行 @internal:纯注释整行移除,内联仅删片段
                    if self._is_whole_line_comment(tok, lines):
                        comment_removals.append((tok.start[0], 0, -1))
                    else:
                        comment_removals.append(
                            (tok.start[0], tok.start[1], tok.end[1])
                        )
                    # check_mode:回填 line marker
                    if check_mode:
                        line_text = lines[tok.start[0] - 1]
                        matched = self._matched_marker_text(
                            tok.string, config
                        )
                        config.markers_found.append(MarkerLocation(
                            line=tok.start[0],
                            col=tok.start[1],
                            marker_type="line",
                            marker_text=matched,
                            content_preview=line_text.strip()[:80],
                        ))

            if tok.type == tokenize.STRING:
                if self._is_docstring(tok, tokens):
                    doc_removals = self._process_docstring(
                        tok, config, lines, tokens
                    )
                    comment_removals.extend(doc_removals)

        # 行级重组
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

    def _is_whole_line_comment(
        self, tok: tokenize.TokenInfo, lines: list[str]
    ) -> bool:
        """判断注释是否独占整行（行首到注释起点全为空白）。

        覆盖顶格注释与缩进注释。

        Args:
            tok: COMMENT token。
            lines: 原始行列表。

        Returns:
            True 表示该行从行首到注释起点之间全为空白。
        """
        line_text = lines[tok.start[0] - 1]
        before = line_text[: tok.start[1]]
        return before.strip() == ""

    def _has_marker(self, comment_text: str, config: StripConfig) -> bool:
        """检查注释是否包含行级标记（排除块定界标记）。

        Args:
            comment_text: 注释文本（含 # 前缀）。
            config: 清理配置。

        Returns:
            是否包含行级标记。
        """
        markers = [config.line_marker] + config.custom_markers
        stripped = comment_text.lstrip("#").strip()
        # 排除块定界标记，避免 @internal-start/-end 被当作逐行 @internal
        block_delims = {
            config.effective_block_start(),
            config.effective_block_end(),
        }
        if any(stripped.startswith(d) for d in block_delims):
            return False
        for marker in markers:
            if stripped.startswith(marker):
                return True
        return False

    def _matched_marker_text(
        self, comment_text: str, config: StripConfig
    ) -> str:
        """返回命中的实际 marker 字符串(用于 --check 输出)。

        Args:
            comment_text: 注释文本(含 # 前缀)。
            config: 清理配置。

        Returns:
            命中的 marker 字符串(line_marker 或 custom_markers 之一)。
            未命中时返回 config.line_marker(兜底,不应发生)。
        """
        markers = [config.line_marker] + config.custom_markers
        stripped = comment_text.lstrip("#").strip()
        for marker in markers:
            if stripped.startswith(marker):
                return marker
        return config.line_marker

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
        tokens: list[tokenize.TokenInfo],
    ) -> list[tuple[int, int, int]]:
        """处理单个 docstring,返回需删除的位置。

        check_mode=True 时,同时回填 docstring-whole / docstring-line marker
        至 config.markers_found。

        Args:
            tok: docstring 的 STRING token。
            config: 清理配置。
            lines: 原始行列表。
            tokens: 完整 token 列表(判断 docstring 是否为块内唯一语句)。

        Returns:
            需要删除的 (line_num, start_col, end_col) 列表。
            end_col=-1 表示删除整行(含换行符)。
        """
        try:
            content = ast.literal_eval(tok.string)
        except (ValueError, SyntaxError):
            return []

        doc_lines = content.split("\n")

        # 检查整体 docstring 标记(整段删除)
        docstring_marker = config.effective_docstring_marker()
        has_whole_marker = any(
            line.strip().startswith(docstring_marker)
            for line in doc_lines
        )
        if has_whole_marker:
            removals = []
            for line_num in range(tok.start[0], tok.end[0] + 1):
                removals.append((line_num, 0, -1))
            # check_mode 回填 docstring-whole
            if config.check_mode:
                first_line_text = lines[tok.start[0] - 1]
                config.markers_found.append(MarkerLocation(
                    line=tok.start[0],
                    col=0,
                    marker_type="docstring-whole",
                    marker_text=docstring_marker,
                    content_preview=first_line_text.strip()[:80],
                ))
            return removals

        # 逐行检查行级标记(整行移除,不留空行)
        markers = [config.line_marker] + config.custom_markers
        block_delims = {
            config.effective_block_start(),
            config.effective_block_end(),
        }

        # docstring 内文本块定界:行首(无 # 前缀)的 @internal-start/-end。
        # scan_blocks 面向注释行(要求 # 前缀),docstring 内的定界行是纯文本,
        # 须在此按相同配对语义单独处理。解码行数与源码行数一致才可行
        # (转义 \n 会破坏行映射,此时保守跳过块处理)。
        start_marker = config.effective_block_start()
        end_marker = config.effective_block_end()
        text_blocks: list[tuple[int, int]] = []
        if len(doc_lines) == tok.end[0] - tok.start[0] + 1:
            open_i: int | None = None
            for i, line in enumerate(doc_lines):
                stripped = line.strip()
                if self._is_text_delimiter(stripped, start_marker):
                    if open_i is not None:
                        config.warnings.append(
                            f"行 {tok.start[0] + i}: docstring 内嵌套"
                            f" {start_marker},已忽略"
                        )
                        continue
                    open_i = i
                elif self._is_text_delimiter(stripped, end_marker):
                    if open_i is None:
                        config.warnings.append(
                            f"行 {tok.start[0] + i}: docstring 内无匹配"
                            f" {start_marker} 的 {end_marker},已忽略"
                        )
                        continue
                    text_blocks.append((open_i, i))
                    open_i = None
            if open_i is not None:
                config.warnings.append(
                    f"行 {tok.start[0] + open_i}: docstring 内 {start_marker}"
                    f" 缺少匹配 {end_marker},已忽略"
                )

        block_lines: set[int] = set()
        for s, e in text_blocks:
            block_lines.update(range(s, e + 1))

        # check_mode:回填 docstring-block-start/-end
        if config.check_mode:
            for s, e in text_blocks:
                s_line = tok.start[0] + s
                e_line = tok.start[0] + e
                s_text = lines[s_line - 1]
                e_text = lines[e_line - 1]
                config.markers_found.append(MarkerLocation(
                    line=s_line,
                    col=max(0, s_text.find(start_marker)),
                    marker_type="docstring-block-start",
                    marker_text=start_marker,
                    content_preview=s_text.strip()[:80],
                ))
                config.markers_found.append(MarkerLocation(
                    line=e_line,
                    col=max(0, e_text.find(end_marker)),
                    marker_type="docstring-block-end",
                    marker_text=end_marker,
                    content_preview=e_text.strip()[:80],
                ))

        removals: list[tuple[int, int, int]] = []
        line_mapped = (
            len(doc_lines) == tok.end[0] - tok.start[0] + 1
            and "\\" not in tok.string
        )
        _raw = tok.string
        while _raw and _raw[0] in "brufBRUF":
            _raw = _raw[1:]
        if _raw.startswith('"""'):
            quote_seq = '"""'
        elif _raw.startswith("'''"):
            quote_seq = "'''"
        else:
            quote_seq = _raw[0]
        for i, line in enumerate(doc_lines):
            stripped = line.strip()
            # 配对文本块内(含定界行):整行移除
            if i in block_lines:
                removals.append((tok.start[0] + i, 0, -1))
                continue
            # 排除块定界标记(未配对定界行保留)
            if any(stripped.startswith(d) for d in block_delims):
                continue
            matched = False
            for marker in markers:
                if stripped.startswith(marker):
                    source_line = tok.start[0] + i
                    # 整行移除(含换行符)
                    removals.append((source_line, 0, -1))
                    # check_mode 回填 docstring-line
                    if config.check_mode:
                        line_text = lines[source_line - 1]
                        config.markers_found.append(MarkerLocation(
                            line=source_line,
                            col=0,
                            marker_type="docstring-line",
                            marker_text=marker,
                            content_preview=line_text.strip()[:80],
                        ))
                    matched = True
                    break
            if matched or not line_mapped:
                continue
            # 内联标记:删除 docstring 行内自标记起至该行 docstring 文本尾
            # (保留标记前摘要与引号结构)。行映射成立(行数一致且无转义)
            # 才能安全换算源码列,否则保守跳过。
            for marker in markers:
                idx = self._inline_marker_index(line, marker)
                if idx < 0:
                    continue
                # 标记前本行含 #:视为文档示例注释行,保守不删
                if "#" in line[:idx]:
                    continue
                source_line = tok.start[0] + i
                source_text = lines[source_line - 1]
                if i == 0:
                    base_col = source_text.find(quote_seq) + len(quote_seq)
                else:
                    base_col = 0
                start_col = base_col + idx
                if i == len(doc_lines) - 1:
                    end_col = source_text.rfind(quote_seq)
                else:
                    end_col = len(source_text.rstrip("\r\n"))
                if start_col >= end_col:
                    continue
                removals.append((source_line, start_col, end_col))
                if config.check_mode:
                    config.markers_found.append(MarkerLocation(
                        line=source_line,
                        col=start_col,
                        marker_type="docstring-line",
                        marker_text=marker,
                        content_preview=source_text.strip()[:80],
                    ))
                break

        # 标记行全部移除后 docstring 内容为空时,会留下 `"""` / `"""` 空文档
        # 字符串:pyarmor --mix-str 的 freeze 步骤会因此误判其后的
        # from __future__ 位置(报 must occur at the beginning of the file),
        # 故此处整体移除该 docstring 语句。
        # 例外:docstring 是所在块唯一语句时保留,整体移除会造成空块语法错误。
        # 内联列级删除保留行(摘要前缀仍在),不参与"内容清空"判定,
        # 只有整行移除才算清空来源。
        removed_lines = {
            line_num for line_num, _, end in removals if end == -1
        }
        remaining = [
            line
            for i, line in enumerate(doc_lines)
            if tok.start[0] + i not in removed_lines
        ]
        if (
            not any(line.strip() for line in remaining)
            and self._starts_line(tok, lines)
            and not self._is_only_statement(tok, tokens)
        ):
            return [
                (line_num, 0, -1)
                for line_num in range(tok.start[0], tok.end[0] + 1)
            ]

        return removals

    @staticmethod
    def _inline_marker_index(line: str, marker: str) -> int:
        """返回 docstring 行内内联标记的起始列,无则 -1。

        匹配规则:标记后须空白或行尾(排除 `@internalized` 伪前缀);
        标记前不得是单词字符/#/@(排除 `foo@internal` 粘连、
        `# @internal` 文档示例注释、`@@internal`),标点与空白前缀
        (如 `摘要.@internal`)允许。

        Args:
            line: docstring 解码后的单行文本。
            marker: 行级标记,如 "@internal"。

        Returns:
            标记在该行内的起始下标,未命中返回 -1。
        """
        pattern = re.compile(
            r"(?<![\w#@])" + re.escape(marker) + r"(?=\s|$)"
        )
        m = pattern.search(line)
        return m.start() if m else -1

    @staticmethod
    def _is_text_delimiter(stripped: str, marker: str) -> bool:
        """判断 docstring 内文本行是否为块定界行(无 # 前缀)。

        与 block_scanner 注释定界语义对齐:标记后须空白或行尾,
        排除 @internal-started 伪前缀;带 # 前缀的行是文档示例注释,
        不算作文本定界。

        Args:
            stripped: 已 strip 的行文本。
            marker: 定界标记,如 "@internal-start"。

        Returns:
            是否为文本块定界行。
        """
        if stripped.startswith("#"):
            return False
        if not stripped.startswith(marker):
            return False
        rest = stripped[len(marker):]
        return rest == "" or rest[0].isspace()

    def _starts_line(
        self, tok: tokenize.TokenInfo, lines: list[str]
    ) -> bool:
        """判断 token 是否独占行首(其前只有空白)。

        用于区分真正的 docstring 与 `x = \"\"\"...\"\"\"` 这类内联多行字符串,
        避免整体移除时连带删掉同一行上的代码。

        Args:
            tok: STRING token。
            lines: 原始行列表。

        Returns:
            True 表示 token 之前仅有空白。
        """
        return lines[tok.start[0] - 1][: tok.start[1]].strip() == ""

    def _is_only_statement(
        self,
        tok: tokenize.TokenInfo,
        tokens: list[tokenize.TokenInfo],
    ) -> bool:
        """判断 token 是否为其所在代码块中唯一的语句。

        模块顶层返回 False(整体移除后得到空文件,仍合法);
        类/函数体内无后续语句(紧随 DEDENT)时返回 True。

        Args:
            tok: STRING token。
            tokens: 完整 token 列表。

        Returns:
            True 表示该 token 是块内唯一语句。
        """
        idx = tokens.index(tok)
        for nxt in tokens[idx + 1:]:
            if nxt.type in (
                tokenize.NL,
                tokenize.NEWLINE,
                tokenize.COMMENT,
                tokenize.ENCODING,
            ):
                continue
            if nxt.type == tokenize.ENDMARKER:
                return False
            return nxt.type == tokenize.DEDENT
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

        注意:正则无法区分字符串中的 # 和注释 #,此为已知限制。
        仅在 tokenize 失败(语法错误)时触发。

        逐行 @internal 与块内删除语义一致:纯注释行整行移除(不留空行),
        内联注释仅删片段保留代码。marker 正则要求标记后为空白/行尾,
        自动排除块定界行与 @internalized 等伪前缀。

        check_mode=True 时,跳过 file-level pragma 委托,
        回填 markers_found 与 strip_selective 一致。

        Args:
            content: 源代码内容。
            config: 清理配置。

        Returns:
            清理后的内容。
        """
        lines = content.splitlines(keepends=True)
        check_mode = config.check_mode
        # 文件级 pragma → 委托 strip_full(check_mode 时跳过)
        if not check_mode and scan_file_pragma(lines, "#"):
            return self.strip_full(content, config)
        scan = scan_blocks(
            lines,
            "#",
            config.effective_block_start(),
            config.effective_block_end(),
        )
        config.warnings.extend(scan.warnings)

        # check_mode:回填 block-start/block-end
        if check_mode:
            for r in scan.ranges:
                start_line_text = lines[r.start_line - 1]
                end_line_text = lines[r.end_line - 1]
                start_col = start_line_text.find(
                    config.effective_block_start()
                )
                end_col = end_line_text.find(config.effective_block_end())
                config.markers_found.append(MarkerLocation(
                    line=r.start_line,
                    col=max(0, start_col),
                    marker_type="block-start",
                    marker_text=config.effective_block_start(),
                    content_preview=start_line_text.strip()[:80],
                ))
                config.markers_found.append(MarkerLocation(
                    line=r.end_line,
                    col=max(0, end_col),
                    marker_type="block-end",
                    marker_text=config.effective_block_end(),
                    content_preview=end_line_text.strip()[:80],
                ))

        markers = [config.line_marker] + config.custom_markers
        marker_alt = "|".join(re.escape(m) for m in markers)
        # marker 后须空白或行尾:排除定界行与伪前缀
        full_re = re.compile(rf"^\s*#\s*(?:{marker_alt})(?:\s|$).*")
        inline_re = re.compile(rf"\s*#\s*(?:{marker_alt})(?:\s|$).*$")
        any_comment_re = re.compile(r"^\s*#")
        inline_any_re = re.compile(r"\s*#.*$")

        def _newline(line: str) -> str:
            for nl in ("\r\n", "\n", "\r"):
                if line.endswith(nl):
                    return nl
            return ""

        out: list[str] = []
        block_iter = iter(scan.ranges)
        cur = next(block_iter, None)

        def _in_block_range(line_num: int) -> bool:
            nonlocal cur
            while cur is not None and line_num > cur.end_line:
                cur = next(block_iter, None)
            return cur is not None and cur.start_line <= line_num <= cur.end_line

        for i, line in enumerate(lines, 1):
            nl = _newline(line)
            body = line[:-len(nl)] if nl else line
            if _in_block_range(i):
                # 块内:纯注释行整行丢弃;否则删内联注释片段保留代码
                if any_comment_re.match(body):
                    continue
                cleaned = inline_any_re.sub("", body).rstrip()
                if cleaned:
                    out.append(cleaned + nl)
            else:
                # 块外:逐行 @internal
                if full_re.match(body):
                    # check_mode 回填 line marker
                    if check_mode:
                        matched = self._matched_marker_text(
                            "#" + body.lstrip("#").lstrip(), config
                        )
                        # 重新解析 marker 起始列
                        col = body.find("#") + 1  # 跳过 #
                        # 找到 marker 在 body 中的位置
                        for m in markers:
                            idx = body.find(m)
                            if idx >= 0:
                                col = idx
                                break
                        config.markers_found.append(MarkerLocation(
                            line=i,
                            col=col,
                            marker_type="line",
                            marker_text=matched,
                            content_preview=body.strip()[:80],
                        ))
                    continue
                cleaned = inline_re.sub("", body)
                if cleaned.strip() == "":
                    continue
                out.append(cleaned.rstrip() + nl)

        return "".join(out)
