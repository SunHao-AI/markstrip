"""语言插件注册表。"""
from markstrip.languages.base import LanguagePlugin


class LanguageRegistry:
    """语言插件注册与查找。

    管理所有已注册的语言插件，支持按名称和扩展名查找。
    """

    def __init__(self) -> None:
        self._plugins: dict[str, LanguagePlugin] = {}
        self._extension_map: dict[str, str] = {}

    def register(self, plugin: LanguagePlugin) -> None:
        """注册语言插件。

        Args:
            plugin: 要注册的语言插件实例。
        """
        self._plugins[plugin.name] = plugin
        for ext in plugin.file_extensions:
            self._extension_map[ext] = plugin.name

    def get_plugin(self, name: str) -> LanguagePlugin | None:
        """按语言名查找插件（大小写不敏感）。

        Args:
            name: 语言标识符。

        Returns:
            匹配的插件，未找到返回 None。
        """
        return self._plugins.get(name.lower())

    def get_plugin_by_extension(self, ext: str) -> LanguagePlugin | None:
        """按文件扩展名查找插件。

        Args:
            ext: 文件扩展名，如 '.py'。

        Returns:
            匹配的插件，未找到返回 None。
        """
        name = self._extension_map.get(ext)
        if name:
            return self._plugins.get(name)
        return None

    def list_languages(self) -> list[str]:
        """列出所有已注册语言。

        Returns:
            语言标识符列表。
        """
        return list(self._plugins.keys())
