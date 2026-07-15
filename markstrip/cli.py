"""markstrip 命令行工具。"""
import argparse
import sys
from pathlib import Path

from markstrip.core.config import StripConfig


def main(argv: list[str] | None = None) -> int:
    """CLI 主入口。

    Args:
        argv: 命令行参数，为 None 时使用 sys.argv。

    Returns:
        退出码，0 表示成功。
    """
    parser = argparse.ArgumentParser(
        prog="markstrip",
        description="标记式选择性注释过滤工具",
    )
    parser.add_argument("path", help="文件或目录路径")
    parser.add_argument(
        "--mode",
        choices=["selective", "full"],
        default="selective",
        help="清理模式：selective（标记过滤）或 full（全量删除）",
    )
    parser.add_argument(
        "--marker",
        default="@internal",
        help="行级标记符号（默认: @internal）",
    )
    parser.add_argument(
        "--docstring-marker",
        default="@internal-docstring",
        help="整体 docstring 标记符号",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式，不修改文件，输出清理结果到 stdout",
    )
    parser.add_argument(
        "--output", "-o",
        help="输出文件路径（仅单文件模式）",
    )
    parser.add_argument(
        "--recursive", "-r",
        action="store_true",
        help="递归处理目录下所有文件",
    )
    parser.add_argument(
        "--preserve-docstrings",
        action="store_true",
        help="full 模式下保留 docstring",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细处理信息",
    )
    args = parser.parse_args(argv)

    config = StripConfig(
        line_marker=args.marker,
        docstring_marker=args.docstring_marker,
        preserve_docstrings=args.preserve_docstrings,
    )

    target = Path(args.path)

    if target.is_dir():
        if not args.recursive:
            print(f"错误: {target} 是目录，请使用 --recursive", file=sys.stderr)
            return 1
        _process_directory(target, args, config)
    elif target.is_file():
        _process_single_file(target, args, config)
    else:
        print(f"错误: {target} 不存在", file=sys.stderr)
        return 1

    return 0


def _process_single_file(
    path: Path, args: argparse.Namespace, config: StripConfig
) -> None:
    """处理单个文件。"""
    from markstrip import strip

    content = path.read_text(encoding="utf-8")
    result = strip(content, filename=str(path), mode=args.mode, config=config)

    if args.verbose:
        print(
            f"Processing {path}... removed {result.removed_count} lines",
            file=sys.stderr,
        )

    if args.dry_run:
        print(result.cleaned_content, end="")
    elif args.output:
        Path(args.output).write_text(
            result.cleaned_content, encoding="utf-8"
        )
    else:
        path.write_text(result.cleaned_content, encoding="utf-8")


def _process_directory(
    path: Path, args: argparse.Namespace, config: StripConfig
) -> None:
    """递归处理目录。"""
    from markstrip import strip

    total_removed = 0
    total_files = 0

    for file_path in path.rglob("*"):
        if not file_path.is_file():
            continue
        # 跳过不支持的文件
        ext = file_path.suffix.lower()
        if ext not in (".py", ".pyw", ".pyi", ".md", ".markdown"):
            continue

        content = file_path.read_text(encoding="utf-8")
        result = strip(
            content, filename=str(file_path), mode=args.mode, config=config
        )

        if args.verbose:
            print(
                f"Processing {file_path}... "
                f"removed {result.removed_count} lines",
                file=sys.stderr,
            )

        total_removed += result.removed_count
        total_files += 1

        if args.dry_run:
            print(f"--- {file_path} ---")
            print(result.cleaned_content, end="")
        else:
            file_path.write_text(
                result.cleaned_content, encoding="utf-8"
            )

    if args.verbose:
        print(
            f"Total: {total_removed} lines removed from {total_files} files",
            file=sys.stderr,
        )


if __name__ == "__main__":
    sys.exit(main())
