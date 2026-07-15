"""清理配置。"""
from dataclasses import dataclass, field


@dataclass
class StripConfig:
    """标记式注释清理配置。

    Attributes:
        line_marker: 行级标记符号，匹配此标记的注释行将被删除。
        docstring_marker: 整体 docstring 标记，放在 docstring 首行时整体删除。
        preserve_docstrings: full 模式下是否保留 docstring。
        preserve_todo: full 模式下是否保留 TODO/FIXME 注释。
        custom_markers: 自定义额外标记列表，与 line_marker 一起匹配。
    """
    line_marker: str = "@internal"
    docstring_marker: str = "@internal-docstring"
    preserve_docstrings: bool = True
    preserve_todo: bool = True
    custom_markers: list[str] = field(default_factory=list)
