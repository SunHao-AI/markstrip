# markstrip/languages/_builtin.py
"""内置插件注册和 entry_points 自动发现。"""
import importlib.metadata
import sys
import warnings

from markstrip.languages.base import LanguagePlugin
from markstrip.languages.markdown_plugin import MarkdownPlugin
from markstrip.languages.python_plugin import PythonPlugin
from markstrip.languages.registry import LanguageRegistry


def _create_default_registry() -> LanguageRegistry:
    """创建默认注册表，注册所有内置插件和 entry_points 插件。

    Returns:
        包含所有已注册插件的 LanguageRegistry 实例。
    """
    registry = LanguageRegistry()

    # 注册 Python 插件
    python_plugin = PythonPlugin()
    registry.register(python_plugin)

    # 注册 Markdown 插件（需要 registry 引用以委托其他插件）
    markdown_plugin = MarkdownPlugin(registry)
    registry.register(markdown_plugin)

    # 发现并注册 entry_points 插件
    for plugin in _discover_entry_point_plugins():
        registry.register(plugin)

    return registry


def _discover_entry_point_plugins() -> list[LanguagePlugin]:
    """通过 entry_points 自动发现第三方插件。

    Returns:
        发现的插件实例列表。
    """
    plugins: list[LanguagePlugin] = []

    try:
        if sys.version_info >= (3, 10):
            eps = importlib.metadata.entry_points(
                group="markstrip.plugins"
            )
        else:
            eps = importlib.metadata.entry_points().get(
                "markstrip.plugins", []
            )
    except Exception:
        return plugins

    for ep in eps:
        try:
            plugin_class = ep.load()
            plugins.append(plugin_class())
        except Exception as e:
            warnings.warn(f"加载插件 {ep.name} 失败: {e}")

    return plugins
