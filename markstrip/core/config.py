"""清理配置。"""
from dataclasses import dataclass, field

from markstrip.core.result import MarkerLocation


@dataclass
class StripConfig:
    """标记式注释清理配置。

    Attributes:
        line_marker: 行级标记符号，匹配此标记的注释行将被删除。
        docstring_marker: 整体 docstring 标记，空串时自动派生为
            f"{line_marker}-docstring"。
        block_start_marker: 块起始定界标记，空串时自动派生为
            f"{line_marker}-start"。
        block_end_marker: 块结束定界标记，空串时自动派生为
            f"{line_marker}-end"。
        preserve_docstrings: full 模式下是否保留 docstring。
        preserve_todo: full 模式下是否保留 TODO/FIXME 注释。
        custom_markers: 自定义额外标记列表，与 line_marker 一起匹配。
        warnings: 引擎瞬态回填通道，由引擎每次调用插件前 clear()，
            插件回填，引擎复制后并入 StripResult.warnings。非用户配置。
        markers_found: --check 模式瞬态回填通道，由引擎每次调用插件前
            clear()，插件在删除点回填 MarkerLocation，引擎复制后并入
            StripResult.markers_found。非用户配置。
        check_mode: --check 模式瞬态标志，由引擎设置。True 时插件跳过
            pragma 委托与 in_pragma 优先分支，确保所有 @internal 被扫描。
    """
    line_marker: str = "@internal"
    docstring_marker: str = ""
    block_start_marker: str = ""
    block_end_marker: str = ""
    preserve_docstrings: bool = True
    preserve_todo: bool = True
    custom_markers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    markers_found: list[MarkerLocation] = field(default_factory=list)
    check_mode: bool = False

    def effective_docstring_marker(self) -> str:
        """返回实际生效的 docstring 标记（空则从 line_marker 派生）。"""
        return self.docstring_marker or f"{self.line_marker}-docstring"

    def effective_block_start(self) -> str:
        """返回实际生效的块起始标记（空则从 line_marker 派生）。"""
        return self.block_start_marker or f"{self.line_marker}-start"

    def effective_block_end(self) -> str:
        """返回实际生效的块结束标记（空则从 line_marker 派生）。"""
        return self.block_end_marker or f"{self.line_marker}-end"
