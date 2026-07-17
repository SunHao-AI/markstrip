"""Pragma 指令扫描器。

与 block_scanner.py 平级的纯函数模块,识别 # markstrip: <directive> 指令。
pragma 命名空间独立于 @internal 标记体系,语义为 full(全量删注释,保留代码)。
"""
import re

from markstrip.core.block_scanner import BlockRange, BlockScanResult


def _build_pragma_regex(comment_prefix: str, directive: str) -> re.Pattern:
    r"""构造 pragma 正则:^\s*{prefix}\s*markstrip\s*:\s*{directive}(?:\s|$)。

    冒号两侧 \s* 容错,指令后须空白或行尾。
    """
    return re.compile(
        rf"^\s*{re.escape(comment_prefix)}\s*markstrip\s*:\s*"
        rf"{re.escape(directive)}(?:\s|$)"
    )


def scan_file_pragma(lines: list[str], comment_prefix: str) -> bool:
    """检测是否存在 # markstrip: full(文件级 pragma)。

    扫描全部行,任意位置出现即返回 True。

    Args:
        lines: 源代码行列表(splitlines(keepends=True))。
        comment_prefix: 注释前缀,如 "#" 或 "//"。

    Returns:
        是否存在文件级 pragma。
    """
    regex = _build_pragma_regex(comment_prefix, "full")
    return any(regex.match(line) for line in lines)


def scan_full_ranges(
    lines: list[str], comment_prefix: str
) -> BlockScanResult:
    """扫描 # markstrip: full-start / full-end 区间。

    返回 BlockScanResult,ranges 中 BlockRange.mode = 'comments'。
    块语义与 scan_blocks 一致(首 start 到首 end 闭区间、不支持嵌套、错配警告)。

    Args:
        lines: 源代码行列表(splitlines(keepends=True))。
        comment_prefix: 注释前缀,如 "#" 或 "//"。

    Returns:
        扫描结果,ranges 的 mode 均为 "comments"。
    """
    start_re = _build_pragma_regex(comment_prefix, "full-start")
    end_re = _build_pragma_regex(comment_prefix, "full-end")

    ranges: list[BlockRange] = []
    warnings: list[str] = []
    open_start: int | None = None

    for i, line in enumerate(lines, 1):
        if start_re.match(line):
            if open_start is not None:
                warnings.append(f"行 {i}: 嵌套 markstrip: full-start, 已忽略")
                continue
            open_start = i
        elif end_re.match(line):
            if open_start is None:
                warnings.append(f"行 {i}: 孤立 markstrip: full-end, 已忽略")
                continue
            ranges.append(
                BlockRange(
                    start_line=open_start,
                    end_line=i,
                    mode="comments",
                )
            )
            open_start = None

    if open_start is not None:
        warnings.append(
            f"行 {open_start}: 未闭合 markstrip: full-start, 已忽略"
        )

    return BlockScanResult(ranges=ranges, warnings=warnings)
