"""Markdown 语言插件。"""
import re

from markstrip.core.config import StripConfig
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

        Args:
            content: Markdown 内容。
            config: 清理配置。
            mode: "selective" 或 "full"。

        Returns:
            处理后的内容。
        """

        def process_block(match: re.Match) -> str:
            fence = match.group("fence")
            lang = match.group("lang").lower()
            code = match.group("code")

            # 删除嵌套代码块
            code = self._remove_nested_blocks(code)

            # 委托给语言插件
            plugin = self._registry.get_plugin(lang)
            if plugin is not None:
                if mode == "selective":
                    cleaned = plugin.strip_selective(code, config)
                else:
                    cleaned = plugin.strip_full(code, config)
                return f"{fence}{lang}\n{cleaned}{fence}"

            # 未知语言：正则兜底
            cleaned = self._fallback_strip(code, lang, config)
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

        Args:
            content: Markdown 内容。
            config: 清理配置。
            mode: "selective" 仅删除含标记的，"full" 删除所有。

        Returns:
            处理后的内容。
        """
        if mode == "full":
            return HTML_COMMENT_RE.sub("", content)

        def filter_comment(match: re.Match) -> str:
            comment = match.group(0)
            if config.line_marker in comment:
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

        Args:
            code: 代码内容。
            lang: 语言标识符。
            config: 清理配置。

        Returns:
            清理后的内容。
        """
        templates = {
            "yaml": r"^\s*#\s*{marker}.*$\n?",
            "bash": r"^\s*#\s*{marker}.*$\n?",
            "shell": r"^\s*#\s*{marker}.*$\n?",
            "javascript": r"^\s*//\s*{marker}.*$\n?",
            "java": r"^\s*//\s*{marker}.*$\n?",
            "c": r"^\s*//\s*{marker}.*$\n?",
            "cpp": r"^\s*//\s*{marker}.*$\n?",
        }
        template = templates.get(lang)
        if template is None:
            return code
        marker = re.escape(config.line_marker)
        pattern = template.format(marker=marker)
        return re.sub(pattern, "", code, flags=re.MULTILINE)
