"""Markdown 语言插件。"""
import re

from markstrip.core.block_scanner import scan_blocks
from markstrip.core.config import StripConfig
from markstrip.core.pragma_scanner import scan_file_pragma, scan_full_ranges
from markstrip.core.result import MarkerLocation
from markstrip.languages.base import LanguagePlugin
from markstrip.languages.registry import LanguageRegistry

# 代码块正则：匹配 ```language\n...\n```
# 使用 ^ 要求闭合围栏在行首，避免内嵌 ``` 提前终止
CODE_BLOCK_RE = re.compile(
    r"^(?P<fence>`{3,})(?P<lang>\w*)\n(?P<code>.*?)^(?P=fence)",
    re.DOTALL | re.MULTILINE,
)

# 嵌套代码块：代码块内带缩进的 ``` 标记对
# 匹配 \n + 前导空白 + ```\n ... 前导空白 + ``` + 可选换行
NESTED_BLOCK_RE = re.compile(
    r"\n[ \t]*```\n.*?[ \t]*```\n?",
    re.DOTALL,
)

# HTML 注释正则：匹配 <!-- ... -->，\n? 移除注释后清理行尾换行
HTML_COMMENT_RE = re.compile(r"<!--.*?-->\n?", re.DOTALL)

# 兜底语言的注释前缀映射（与 _fallback_strip 的 templates 语言集合对齐）
FALLBACK_COMMENT_PREFIX = {
    "yaml": "#",
    "bash": "#",
    "shell": "#",
    "javascript": "//",
    "java": "//",
    "c": "//",
    "cpp": "//",
}


class MarkdownPlugin(LanguagePlugin):
    """Markdown 语言插件。

    解析 Markdown 代码块后委托给对应语言插件处理。
    支持嵌套代码块删除和 HTML 注释过滤。
    """

    def __init__(self, registry: LanguageRegistry) -> None:
        self._registry = registry

    @property
    def name(self) -> str:
        return "markdown"

    @property
    def file_extensions(self) -> list[str]:
        return [".md", ".markdown"]

    def strip_selective(
        self, content: str, config: StripConfig
    ) -> str:
        """标记式选择性过滤。"""
        content = self._process_code_blocks(
            content, config, mode="selective"
        )
        content = self._process_html_comments(
            content, config, mode="selective"
        )
        return content

    def strip_full(self, content: str, config: StripConfig) -> str:
        """全量注释删除。"""
        content = self._process_code_blocks(
            content, config, mode="full"
        )
        content = self._process_html_comments(
            content, config, mode="full"
        )
        return content

    def _process_code_blocks(
        self,
        content: str,
        config: StripConfig,
        mode: str,
    ) -> str:
        """处理所有围栏代码块。

        check_mode=True 时,委托插件回填的 markers 行号会被翻译为 .md 绝对行号。

        Args:
            content: Markdown 内容。
            config: 清理配置。
            mode: "selective" 仅删除含标记的,"full" 删除所有。

        Returns:
            处理后的内容。
        """
        def process_block(match: re.Match) -> str:
            fence = match.group("fence")
            lang = match.group("lang").lower()
            code = match.group("code")

            # 删除嵌套代码块
            code = self._remove_nested_blocks(code)

            # 委托前记录 markers_found 长度,以便切片翻译行号
            pre_count = len(config.markers_found)

            # 委托给语言插件
            plugin = self._registry.get_plugin(lang)
            if plugin is not None:
                if mode == "selective":
                    cleaned = plugin.strip_selective(code, config)
                else:
                    cleaned = plugin.strip_full(code, config)
            else:
                # 未知语言:正则兜底
                cleaned = self._fallback_strip(code, lang, config)

            # check_mode:翻译委托插件记录的相对行号为 .md 绝对行号
            if config.check_mode:
                new_markers = config.markers_found[pre_count:]
                # 代码块 fence 行在 .md 中的行号(1-based)
                block_start_in_md = content[:match.start()].count("\n") + 1
                # 代码块内容首行 = fence 行 + 1
                code_first_line_in_md = block_start_in_md + 1
                for m in new_markers:
                    m.line = code_first_line_in_md + (m.line - 1)

            return f"{fence}{lang}\n{cleaned}{fence}"

        return CODE_BLOCK_RE.sub(process_block, content)

    def _remove_nested_blocks(self, code: str) -> str:
        """删除代码块内的嵌套 ``` 标记对及其内容。

        Args:
            code: 代码块内容。

        Returns:
            清理后的代码内容。
        """
        return NESTED_BLOCK_RE.sub("", code)

    def _process_html_comments(
        self,
        content: str,
        config: StripConfig,
        mode: str,
    ) -> str:
        """处理 HTML 注释。

        check_mode=True 且 selective 模式下,含 line_marker 的 HTML 注释
        回填 MarkerLocation(.md 绝对行号)。

        Args:
            content: Markdown 内容。
            config: 清理配置。
            mode: "selective" 仅删除含标记的,"full" 删除所有。

        Returns:
            处理后的内容。
        """
        if mode == "full":
            return HTML_COMMENT_RE.sub("", content)

        def filter_comment(match: re.Match) -> str:
            comment = match.group(0)
            if config.line_marker in comment:
                # check_mode: 回填 HTML 注释 marker(.md 绝对行号)
                if config.check_mode:
                    block_start_in_md = (
                        content[:match.start()].count("\n") + 1
                    )
                    marker_idx = comment.find(config.line_marker)
                    # marker 起始列 = match 在所在行的列偏移 + marker 在 comment 内偏移
                    line_start = content.rfind("\n", 0, match.start()) + 1
                    col = (match.start() - line_start) + marker_idx
                    # 截取 marker 所在行文本(整行)
                    line_end = content.find("\n", match.start())
                    if line_end == -1:
                        line_end = len(content)
                    line_text = content[line_start:line_end]
                    config.markers_found.append(MarkerLocation(
                        line=block_start_in_md,
                        col=col,
                        marker_type="line",
                        marker_text=config.line_marker,
                        content_preview=line_text.strip()[:80],
                    ))
                return ""
            return comment

        return HTML_COMMENT_RE.sub(filter_comment, content)

    def _fallback_strip(
        self,
        code: str,
        lang: str,
        config: StripConfig,
    ) -> str:
        """无对应插件时的正则兜底。

        支持逐行 @internal 与块定界。纯注释标记行整行移除，内联注释
        仅删片段保留代码。

        Args:
            code: 代码内容。
            lang: 语言标识符。
            config: 清理配置。

        Returns:
            清理后的内容。
        """
        prefix = FALLBACK_COMMENT_PREFIX.get(lang)
        if prefix is None:
            return code

        lines = code.splitlines(keepends=True)

        # 文件级 pragma → 全量删注释
        if scan_file_pragma(lines, prefix):
            return self._fallback_full(lines, prefix, config)

        # pragma 区间扫描
        pragma_scan = scan_full_ranges(lines, prefix)
        config.warnings.extend(pragma_scan.warnings)
        pragma_ranges = pragma_scan.ranges

        def _in_pragma_range(line_num: int) -> bool:
            return any(
                r.start_line <= line_num <= r.end_line for r in pragma_ranges
            )

        scan = scan_blocks(
            lines,
            prefix,
            config.effective_block_start(),
            config.effective_block_end(),
        )
        config.warnings.extend(scan.warnings)

        markers = [config.line_marker] + config.custom_markers
        marker_alt = "|".join(re.escape(m) for m in markers)
        full_re = re.compile(
            rf"^\s*{re.escape(prefix)}\s*(?:{marker_alt})(?:\s|$).*"
        )
        inline_re = re.compile(
            rf"\s*{re.escape(prefix)}\s*(?:{marker_alt})(?:\s|$).*$"
        )
        any_comment_re = re.compile(rf"^\s*{re.escape(prefix)}")
        inline_any_re = re.compile(rf"\s*{re.escape(prefix)}.*$")

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
                if any_comment_re.match(body):
                    continue
                cleaned = inline_any_re.sub("", body).rstrip()
                if cleaned:
                    out.append(cleaned + nl)
            elif _in_pragma_range(i):
                # pragma 区间：full 逻辑,删注释保留代码
                if any_comment_re.match(body):
                    continue
                cleaned = inline_any_re.sub("", body).rstrip()
                if cleaned:
                    out.append(cleaned + nl)
            else:
                if full_re.match(body):
                    continue
                cleaned = inline_re.sub("", body)
                if cleaned.strip() == "":
                    continue
                out.append(cleaned.rstrip() + nl)

        return "".join(out)

    def _fallback_full(
        self,
        lines: list[str],
        prefix: str,
        config: StripConfig,
    ) -> str:
        """正则兜底的全量注释删除(文件级 pragma 触发)。

        删除所有注释行与行尾注释,保留代码。不保留 TODO/shebang
        (兜底语言无统一 shebang 约定,简化处理)。

        Args:
            lines: 代码行列表(splitlines(keepends=True))。
            prefix: 注释前缀。
            config: 清理配置(此方法不使用 preserve_* 字段)。

        Returns:
            清理后的代码。
        """
        any_comment_re = re.compile(rf"^\s*{re.escape(prefix)}")
        inline_any_re = re.compile(rf"\s*{re.escape(prefix)}.*$")

        def _newline(line: str) -> str:
            for nl in ("\r\n", "\n", "\r"):
                if line.endswith(nl):
                    return nl
            return ""

        out: list[str] = []
        for line in lines:
            nl = _newline(line)
            body = line[:-len(nl)] if nl else line
            if any_comment_re.match(body):
                continue
            cleaned = inline_any_re.sub("", body).rstrip()
            if cleaned:
                out.append(cleaned + nl)
        return "".join(out)
