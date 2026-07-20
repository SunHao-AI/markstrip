"""Pragma 指令扫描器。

与 block_scanner.py 平级的纯函数模块,识别 # markstrip: <directive> 指令。
pragma 命名空间独立于 @internal 标记体系,语义为 full(全量删注释,保留代码)。
"""
import re




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



