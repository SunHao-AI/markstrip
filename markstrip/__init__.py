"""markstrip - 标记式选择性注释过滤库。"""
from pathlib import Path
from typing import Union

from markstrip.core.config import StripConfig
from markstrip.core.engine import StripEngine
from markstrip.core.result import StripResult
from markstrip.languages.base import LanguagePlugin
from markstrip.languages.registry import LanguageRegistry

# 默认引擎实例（内置插件已注册）
_default_engine = StripEngine()


def strip(
    content: str,
    *,
    language: str | None = None,
    filename: str | None = None,
    mode: str = "selective",
    config: StripConfig | None = None,
) -> StripResult:
    """清理内容中的标记注释。

    Args:
        content: 待清理的内容。
        language: 显式指定语言标识符。
        filename: 文件名（用于扩展名检测）。
        mode: "selective"（标记过滤）或 "full"（全量删除）。
        config: 清理配置，为 None 时使用默认配置。

    Returns:
        StripResult 清理结果。
    """
    return _default_engine.strip(
        content,
        language=language,
        filename=filename,
        mode=mode,
        config=config,
    )


def strip_file(
    path: Union[str, Path],
    *,
    mode: str = "selective",
    config: StripConfig | None = None,
    inplace: bool = False,
) -> StripResult:
    """清理文件中的标记注释。

    Args:
        path: 文件路径。
        mode: "selective" 或 "full"。
        config: 清理配置。
        inplace: 是否原地修改文件。

    Returns:
        StripResult 清理结果。
    """
    path = Path(path)
    content = path.read_text(encoding="utf-8")
    result = _default_engine.strip(
        content, filename=str(path), mode=mode, config=config
    )
    if inplace:
        path.write_text(result.cleaned_content, encoding="utf-8")
    return result


def strip_directory(
    path: Union[str, Path],
    *,
    mode: str = "selective",
    config: StripConfig | None = None,
    extensions: list[str] | None = None,
    inplace: bool = False,
) -> list[StripResult]:
    """批量清理目录下所有支持的文件。

    Args:
        path: 目录路径。
        mode: "selective" 或 "full"。
        config: 清理配置。
        extensions: 限制处理的文件扩展名列表。
        inplace: 是否原地修改文件。

    Returns:
        每个文件的 StripResult 列表。
    """
    path = Path(path)
    results = []
    for file_path in path.rglob("*"):
        if file_path.is_file():
            if extensions and file_path.suffix not in extensions:
                continue
            result = strip_file(
                file_path, mode=mode, config=config, inplace=inplace
            )
            results.append(result)
    return results


def register_plugin(plugin: LanguagePlugin) -> None:
    """注册自定义语言插件。

    Args:
        plugin: 要注册的语言插件实例。
    """
    _default_engine._registry.register(plugin)


__all__ = [
    "strip",
    "strip_file",
    "strip_directory",
    "register_plugin",
    "StripConfig",
    "StripResult",
    "StripEngine",
    "LanguagePlugin",
    "LanguageRegistry",
]
