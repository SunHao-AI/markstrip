"""清理结果。"""
from dataclasses import dataclass, field


@dataclass
class MarkerLocation:
    """检测到的标记位置（用于 --check 输出）。

    Attributes:
        line: 1-based 行号（文件绝对行号）。
        col: 0-based 列号（标记起点）。
        marker_type: "line" | "block-start" | "block-end"
            | "docstring-whole" | "docstring-line"。
        marker_text: 命中的标记文本（如 "@internal" / "@internal-start"
            / "@internal-docstring" / 自定义 marker 串）。
        content_preview: 标记所在行内容预览（截断至 80 字符，便于定位）。
    """
    line: int
    col: int
    marker_type: str
    marker_text: str
    content_preview: str


@dataclass
class StripResult:
    """注释清理结果。

    Attributes:
        cleaned_content: 清理后的内容。
        removed_count: 删除的行数。
        detected_language: 检测到的语言标识符。
        warnings: 警告信息列表。
        markers_found: --check 模式检测到的标记位置列表（瞬态，由引擎复制并入）。
    """
    cleaned_content: str
    removed_count: int
    detected_language: str = ""
    warnings: list[str] = field(default_factory=list)
    markers_found: list[MarkerLocation] = field(default_factory=list)
