"""markstrip 命令行工具。"""
import argparse
import sys
from pathlib import Path

from markstrip import strip
from markstrip.core.config import StripConfig


def main(argv: list[str] | None = None) -> int:
    """CLI 主入口。

    Args:
        argv: 命令行参数,为 None 时使用 sys.argv。

    Returns:
        退出码:0 成功;1(--check 发现标记);2 参数错误/路径不存在。
    """
    parser = argparse.ArgumentParser(
        prog="markstrip",
        description="标记式选择性注释过滤工具",
    )
    parser.add_argument("path", help="文件或目录路径,或 '-' 触发 stdin 模式")
    parser.add_argument(
        "--mode",
        choices=["selective", "full"],
        default="selective",
        help="清理模式:selective(标记过滤)或 full(全量删除)",
    )
    parser.add_argument(
        "--marker",
        default="@internal",
        help="行级标记符号(默认: @internal)",
    )
    parser.add_argument(
        "--docstring-marker",
        default="",
        help="整体 docstring 标记(默认自动派生为 {marker}-docstring)",
    )
    parser.add_argument(
        "--block-start-marker",
        default="",
        help="块起始标记(默认自动派生为 {marker}-start)",
    )
    parser.add_argument(
        "--block-end-marker",
        default="",
        help="块结束标记(默认自动派生为 {marker}-end)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式,不修改文件,输出清理结果到 stdout",
    )
    parser.add_argument(
        "--output", "-o",
        help="输出文件路径(仅单文件模式)",
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
    parser.add_argument(
        "--check",
        action="store_true",
        help="检查模式:扫描 @internal 标记并输出位置到 stderr,"
             "不修改文件,exit 0(无标记)/1(有标记)",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="显式指定语言标识符(如 python/markdown),"
             "stdin 模式或内容探测失败时使用",
    )
    args = parser.parse_args(argv)

    # 参数冲突检测
    if args.check and args.mode == "full":
        print(
            "错误: --check 与 --mode full 互斥(--check 蕴含 selective)",
            file=sys.stderr,
        )
        return 2
    if args.check and args.output:
        print(
            "错误: --check 与 --output 互斥(--check 不写文件)",
            file=sys.stderr,
        )
        return 2
    if args.path == "-" and args.recursive:
        print(
            "错误: stdin 模式(-)不支持 --recursive(stdin 是单流)",
            file=sys.stderr,
        )
        return 2

    config = StripConfig(
        line_marker=args.marker,
        docstring_marker=args.docstring_marker,
        block_start_marker=args.block_start_marker,
        block_end_marker=args.block_end_marker,
        preserve_docstrings=args.preserve_docstrings,
    )

    # stdin 模式
    if args.path == "-":
        return _process_stdin(args, config)

    target = Path(args.path)

    if target.is_dir():
        if not args.recursive:
            print(
                f"错误: {target} 是目录,请使用 --recursive",
                file=sys.stderr,
            )
            return 1
        return _process_directory(target, args, config)
    elif target.is_file():
        return _process_single_file(target, args, config)
    else:
        print(f"错误: {target} 不存在", file=sys.stderr)
        return 1


def _process_stdin(args: argparse.Namespace, config: StripConfig) -> int:
    """处理 stdin 模式。

    Args:
        args: 命令行参数。
        config: 清理配置。

    Returns:
        退出码。
    """
    content = sys.stdin.read()
    result = strip(
        content,
        language=args.language,
        mode=args.mode,
        config=config,
        check_mode=args.check,
    )

    if not result.detected_language and not args.language:
        print(
            f"错误: 无法识别语言,请使用 --language 显式指定",
            file=sys.stderr,
        )
        return 2

    if args.verbose:
        print(
            f"Processing stdin... removed {result.removed_count} lines",
            file=sys.stderr,
        )
        for w in result.warnings:
            print(f"Warning: {w}", file=sys.stderr)

    if args.check:
        _output_markers_to_stderr([("<stdin>", result)])
        return 1 if result.markers_found else 0

    if args.output:
        Path(args.output).write_text(
            result.cleaned_content, encoding="utf-8"
        )
    else:
        sys.stdout.write(result.cleaned_content)

    for w in result.warnings:
        print(f"Warning: {w}", file=sys.stderr)
    return 0


def _process_single_file(
    path: Path, args: argparse.Namespace, config: StripConfig
) -> int:
    """处理单个文件。"""
    content = path.read_text(encoding="utf-8")
    result = strip(
        content,
        filename=str(path),
        mode=args.mode,
        config=config,
        check_mode=args.check,
    )

    if args.verbose:
        print(
            f"Processing {path}... removed {result.removed_count} lines",
            file=sys.stderr,
        )
        for w in result.warnings:
            print(f"Warning: {w}", file=sys.stderr)

    if args.check:
        _output_markers_to_stderr([(str(path), result)])
        return 1 if result.markers_found else 0

    if args.dry_run:
        print(result.cleaned_content, end="")
    elif args.output:
        Path(args.output).write_text(
            result.cleaned_content, encoding="utf-8"
        )
    else:
        path.write_text(result.cleaned_content, encoding="utf-8")
    return 0


def _process_directory(
    path: Path, args: argparse.Namespace, config: StripConfig
) -> int:
    """递归处理目录。"""
    total_removed = 0
    total_files = 0
    results: list[tuple[str, "StripResult"]] = []

    for file_path in path.rglob("*"):
        if not file_path.is_file():
            continue
        ext = file_path.suffix.lower()
        if ext not in (".py", ".pyw", ".pyi", ".md", ".markdown"):
            continue

        content = file_path.read_text(encoding="utf-8")
        result = strip(
            content,
            filename=str(file_path),
            mode=args.mode,
            config=config,
            check_mode=args.check,
        )

        if args.verbose:
            print(
                f"Processing {file_path}... "
                f"removed {result.removed_count} lines",
                file=sys.stderr,
            )
            for w in result.warnings:
                print(f"Warning: {w}", file=sys.stderr)

        total_removed += result.removed_count
        total_files += 1

        if args.check:
            results.append((str(file_path), result))
        elif args.dry_run:
            print(f"--- {file_path} ---")
            print(result.cleaned_content, end="")
        else:
            file_path.write_text(
                result.cleaned_content, encoding="utf-8"
            )

    if args.check:
        _output_markers_to_stderr(results)
        total_markers = sum(
            len(r.markers_found) for _, r in results
        )
        return 1 if total_markers > 0 else 0

    if args.verbose:
        print(
            f"Total: {total_removed} lines removed from {total_files} files",
            file=sys.stderr,
        )
    return 0


def _output_markers_to_stderr(
    results: list[tuple[str, "StripResult"]]
) -> None:
    """格式化输出 markers_found 到 stderr。

    Args:
        results: (path, result) 元组列表。
    """
    total_markers = 0
    files_with_markers = 0
    for path, result in results:
        if not result.markers_found:
            continue
        files_with_markers += 1
        for m in result.markers_found:
            total_markers += 1
            print(
                f"{path}:{m.line}:{m.col}  "
                f"{m.marker_text} ({m.marker_type})\t"
                f"{m.content_preview}",
                file=sys.stderr,
            )
    if total_markers == 0:
        print("No markers found", file=sys.stderr)
    else:
        print(
            f"Found {total_markers} markers in {files_with_markers} files",
            file=sys.stderr,
        )


if __name__ == "__main__":
    sys.exit(main())
