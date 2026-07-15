"""清理结果。"""
from dataclasses import dataclass, field


@dataclass
class StripResult:
    """注释清理结果。

    Attributes:
        cleaned_content: 清理后的内容。
        removed_count: 删除的行数。
        detected_language: 检测到的语言标识符。
        warnings: 警告信息列表。
    """
    cleaned_content: str
    removed_count: int
    detected_language: str = ""
    warnings: list[str] = field(default_factory=list)
