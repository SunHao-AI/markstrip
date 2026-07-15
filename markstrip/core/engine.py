# markstrip/core/engine.py
"""主引擎：调度插件执行清理。"""
from pathlib import Path

from markstrip.core.config import StripConfig
from markstrip.core.result import StripResult
from markstrip.languages._builtin import _create_default_registry
from markstrip.languages.base import LanguagePlugin
from markstrip.languages.registry import LanguageRegistry


class StripEngine:
    """主引擎：调度语言插件执行注释清理。

    按优先级解析语言：显式指定 > 文件扩展名 > 内容探测。
    """

    def __init__(self, registry: LanguageRegistry | None = None) -> None:
        self._registry = registry or _create_default_registry()

    def strip(
        self,
        content: str,
        *,
        language: str | None = None,
        filename: str | None = None,
        mode: str = "selective",
        config: StripConfig | None = None,
    ) -> StripResult:
        """清理内容中的注释。

        Args:
            content: 待清理的内容。
            language: 显式指定语言标识符。
            filename: 文件名（用于扩展名检测）。
            mode: "selective" 或 "full"。
            config: 清理配置，为 None 时使用默认配置。

        Returns:
            StripResult 清理结果。
        """
        config = config or StripConfig()

        plugin = self._resolve_plugin(language, filename, content)
        if plugin is None:
            return StripResult(
                cleaned_content=content,
                removed_count=0,
                warnings=["无法识别语言，跳过处理"],
            )

        if mode == "full":
            cleaned = plugin.strip_full(content, config)
        else:
            cleaned = plugin.strip_selective(content, config)

        # 统计变更/删除行数
        original_lines = content.splitlines()
        cleaned_lines = cleaned.splitlines()
        removed_count = sum(
            1 for o, c in zip(original_lines, cleaned_lines) if o != c
        ) + max(0, len(original_lines) - len(cleaned_lines))

        return StripResult(
            cleaned_content=cleaned,
            removed_count=removed_count,
            detected_language=plugin.name,
        )

    def _resolve_plugin(
        self,
        language: str | None,
        filename: str | None,
        content: str,
    ) -> LanguagePlugin | None:
        """按优先级解析语言插件。"""
        # 优先级 1: 显式指定
        if language:
            return self._registry.get_plugin(language)
        # 优先级 2: 文件扩展名
        if filename:
            ext = Path(filename).suffix.lower()
            plugin = self._registry.get_plugin_by_extension(ext)
            if plugin:
                return plugin
        # 优先级 3: 内容探测
        for plugin in self._registry._plugins.values():
            if plugin.detect(content):
                return plugin
        return None
