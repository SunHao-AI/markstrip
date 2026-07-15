"""语言插件抽象基类。"""
from abc import ABC, abstractmethod

from markstrip.core.config import StripConfig


class LanguagePlugin(ABC):
    """语言插件抽象基类。

    每种语言实现此接口，提供 selective 和 full 两种清理模式。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """语言标识符，如 'python', 'markdown'。"""

    @property
    @abstractmethod
    def file_extensions(self) -> list[str]:
        """支持的文件扩展名列表，如 ['.py', '.pyw']。"""

    @abstractmethod
    def strip_selective(self, content: str, config: StripConfig) -> str:
        """标记式选择性过滤：仅删除含标记的注释。

        Args:
            content: 源代码内容。
            config: 清理配置。

        Returns:
            清理后的内容。
        """

    @abstractmethod
    def strip_full(self, content: str, config: StripConfig) -> str:
        """全量注释删除：删除所有注释，保留 shebang/TODO 等。

        Args:
            content: 源代码内容。
            config: 清理配置。

        Returns:
            清理后的内容。
        """

    def detect(self, content: str) -> bool:
        """检测内容是否属于该语言。

        默认返回 False，子类可覆盖以实现内容探测。

        Args:
            content: 待检测的内容。

        Returns:
            是否属于该语言。
        """
        return False
