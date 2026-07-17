"""块定界扫描器：纯函数，供 Python 插件与 Markdown 兜底共用。

块语义的唯一真理源。单趟扫描，严格容错，不支持嵌套：
内层 start 视为错配并忽略 + 警告；未闭合/无匹配的定界行均忽略 + 警告。
"""
import re
from dataclasses import dataclass, field


@dataclass
class BlockRange:
    """块范围（1-based，含两端的定界行）。"""
    start_line: int
    end_line: int
    mode: str = "all"  # "all"=删全部(@internal-start/end), "comments"=只删注释(markstrip pragma)


@dataclass
class BlockScanResult:
    """块扫描结果。"""
    ranges: list[BlockRange] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _build_delimiter_regex(comment_prefix: str, marker: str) -> re.Pattern:
    r"""构造定界行正则：^\s*{prefix}\s*{marker}(?:\s|$)。

    要求标记后紧跟空白或行尾，避免 @internal-started 等伪前缀误匹配。
    """
    escaped_prefix = re.escape(comment_prefix)
    escaped_marker = re.escape(marker)
    return re.compile(
        rf"^\s*{escaped_prefix}\s*{escaped_marker}(?:\s|$)"
    )


def scan_blocks(
    lines: list[str],
    comment_prefix: str,
    start_marker: str,
    end_marker: str,
) -> BlockScanResult:
    """扫描行列表，返回块范围与警告。

    Args:
        lines: 源行列表（含换行符，splitlines(keepends=True) 风格）。
        comment_prefix: 注释前缀，如 "#" 或 "//"（不含空白）。
        start_marker: 块起始标记文本，如 "@internal-start"。
        end_marker: 块结束标记文本，如 "@internal-end"。

    Returns:
        BlockScanResult，ranges 为配对成功的块范围（1-based，含定界行），
        warnings 为错配定界行的警告信息列表。
    """
    start_re = _build_delimiter_regex(comment_prefix, start_marker)
    end_re = _build_delimiter_regex(comment_prefix, end_marker)

    open_start: int | None = None
    ranges: list[BlockRange] = []
    warnings: list[str] = []

    for i, line in enumerate(lines, 1):
        is_start = start_re.match(line) is not None
        is_end = end_re.match(line) is not None
        if is_start:
            if open_start is not None:
                warnings.append(
                    f"行 {i}: 嵌套 {start_marker}，已忽略"
                )
                continue
            open_start = i
        elif is_end:
            if open_start is None:
                warnings.append(
                    f"行 {i}: 无匹配 {start_marker} 的 {end_marker}，已忽略"
                )
                continue
            ranges.append(BlockRange(open_start, i))
            open_start = None

    if open_start is not None:
        warnings.append(
            f"行 {open_start}: {start_marker} 缺少匹配 {end_marker}，已忽略"
        )

    return BlockScanResult(ranges=ranges, warnings=warnings)
