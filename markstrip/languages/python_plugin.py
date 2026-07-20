"""Python 语言插件。"""
import ast
import re
import tokenize

from markstrip.core.block_scanner import scan_blocks
from markstrip.core.config import StripConfig
from markstrip.core.pragma_scanner import scan_file_pragma, scan_full_ranges
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
        # 至少 2 个信号或占比 > 30% 才判定为 Python
        threshold = max(2, len(lines) * 0.3)
        return python_signals >= threshold

    def strip_selective(self, content: str, config: StripConfig) -> str:
        """标记式选择性过滤:仅删除含标记的注释。

        支持逐行 @internal、块定界 @internal-start/-end、docstring 整体标记。
        纯注释标记行整行移除,内联标记注释仅删注释片段保留代码。

        check_mode=True 时,跳过 file-level pragma 委托与 in_pragma 优先分支,
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
            # 检查区间标记冗余
            pragma_scan = scan_full_ranges(lines, "#")
            config.warnings.extend(pragma_scan.warnings)
            if pragma_scan.ranges:
                config.warnings.append("文件级 full 已生效, 区间标记冗余")
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

        # pragma 区间扫描
        pragma_scan = scan_full_ranges(lines, "#")
        config.warnings.extend(pragma_scan.warnings)
        pragma_ranges = pragma_scan.ranges

        def _in_pragma_range(line_num: int) -> bool:
            return any(
                r.start_line <= line_num <= r.end_line for r in pragma_ranges
            )

        for tok in tokens:
            if tok.type == tokenize.COMMENT:
                in_block = _in_block(tok.start[0])
                in_pragma = _in_pragma_range(tok.start[0])
                if in_block:
                    # 块内:纯注释整行移除,内联仅删片段
                    if self._is_whole_line_comment(tok, lines):
                        comment_removals.append((tok.start[0], 0, -1))
                    else:
                        comment_removals.append(
                            (tok.start[0], tok.start[1], tok.end[1])
                        )
                elif in_pragma and not check_mode:
                    # pragma 区间(check_mode=False):full 逻辑,删注释保留代码
                    if self._is_preserved_comment(tok, config):
                        continue
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
                elif in_pragma and check_mode:
                    # pragma 区间内非 @internal 注释:check_mode 不删除不报告
                    # (避免与"pragma 区间内全量删"的语义混淆;check_mode 跳过此分支)
                    pass

            if tok.type == tokenize.STRING:
                if self._is_docstring(tok, tokens):
                    in_pragma = _in_pragma_range(tok.start[0])
                    if in_pragma and not config.preserve_docstrings and not check_mode:
                        for line_num in range(tok.start[0], tok.end[0] + 1):
                            comment_removals.append((line_num, 0, -1))
                    else:
                        doc_removals = self._process_docstring(
                            tok, config, lines
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
    ) -> list[tuple[int, int, int]]:
        """处理单个 docstring,返回需删除的位置。

        check_mode=True 时,同时回填 docstring-whole / docstring-line marker
        至 config.markers_found。

        Args:
            tok: docstring 的 STRING token。
            config: 清理配置。
            lines: 原始行列表。

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
        removals: list[tuple[int, int, int]] = []
        for i, line in enumerate(doc_lines):
            stripped = line.strip()
            # 排除块定界标记
            if any(stripped.startswith(d) for d in block_delims):
                continue
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

        注意:正则无法区分字符串中的 # 和注释 #,此为已知限制。
        仅在 tokenize 失败(语法错误)时触发。

        逐行 @internal 与块内删除语义一致:纯注释行整行移除(不留空行),
        内联注释仅删片段保留代码。marker 正则要求标记后为空白/行尾,
        自动排除块定界行与 @internalized 等伪前缀。

        check_mode=True 时,跳过 file-level pragma 委托与 in_pragma 优先分支,
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

        # pragma 区间扫描
        pragma_scan = scan_full_ranges(lines, "#")
        config.warnings.extend(pragma_scan.warnings)
        pragma_ranges = pragma_scan.ranges

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

        def _in_pragma_range(line_num: int) -> bool:
            return any(
                r.start_line <= line_num <= r.end_line for r in pragma_ranges
            )

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
            elif _in_pragma_range(i) and not check_mode:
                # pragma 区间(check_mode=False):full 逻辑,删注释保留代码
                if any_comment_re.match(body):
                    continue
                cleaned = inline_any_re.sub("", body).rstrip()
                if cleaned:
                    out.append(cleaned + nl)
            else:
                # 块外 / check_mode 下 pragma 区间外:逐行 @internal
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
