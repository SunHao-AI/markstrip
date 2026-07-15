"""异常定义。"""


class MarkstripError(Exception):
    """markstrip 基础异常。"""


class PluginNotFoundError(MarkstripError):
    """未找到匹配的语言插件。"""


class TokenizeError(MarkstripError):
    """tokenize 词法分析失败。"""
