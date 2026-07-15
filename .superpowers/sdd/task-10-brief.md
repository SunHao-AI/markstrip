# Task 10: CLI 实现

## 目标
创建 markstrip 命令行工具，支持文件/目录处理、dry-run 预览、自定义标记、full/selective 模式切换。

## 文件
- 创建: `markstrip/cli.py`
- 创建: `tests/integration/test_cli.py`

## 上下文
- 已完成的公共 API（Task 9）: `markstrip.strip()`, `markstrip.strip_file()`, `markstrip.strip_directory()`
- StripConfig 在 `markstrip.core.config`
- 当前 41 个测试全部通过

## TDD 步骤

### Step 1: 编写 CLI 测试

创建 `tests/integration/test_cli.py`（注意需要先创建 `tests/integration/` 目录，可能需要 `__init__.py`）:

```python
# tests/integration/test_cli.py
"""CLI 集成测试。"""
import subprocess
import sys
from pathlib import Path


def run_cli(*args) -> tuple[int, str, str]:
    """运行 markstrip CLI 并返回 (returncode, stdout, stderr)。"""
    result = subprocess.run(
        [sys.executable, "-m", "markstrip.cli", *args],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def test_cli_help():
    code, out, err = run_cli("--help")
    assert code == 0
    assert "markstrip" in out
    assert "--mode" in out


def test_cli_strip_file(tmp_path):
    # 创建测试文件
    test_file = tmp_path / "test.py"
    test_file.write_text("# @internal 删除\nx = 1\n", encoding="utf-8")

    # 运行 CLI
    code, out, err = run_cli(str(test_file), "--dry-run")
    assert code == 0
    assert "# @internal" not in out
    assert "x = 1" in out


def test_cli_output_to_file(tmp_path):
    test_file = tmp_path / "input.py"
    test_file.write_text("# @internal 删除\nx = 1\n", encoding="utf-8")
    output_file = tmp_path / "output.py"

    code, out, err = run_cli(
        str(test_file), "--output", str(output_file)
    )
    assert code == 0
    result = output_file.read_text(encoding="utf-8")
    assert "# @internal" not in result
    assert "x = 1" in result


def test_cli_recursive_directory(tmp_path):
    # 创建目录结构
    subdir = tmp_path / "sub"
    subdir.mkdir()
    file1 = tmp_path / "a.py"
    file1.write_text("# @internal 删除\nx = 1\n", encoding="utf-8")
    file2 = subdir / "b.py"
    file2.write_text("# @internal 删除\ny = 2\n", encoding="utf-8")

    code, out, err = run_cli(str(tmp_path), "--recursive", "--dry-run")
    assert code == 0
    assert "x = 1" in out
    assert "y = 2" in out


def test_cli_custom_marker(tmp_path):
    test_file = tmp_path / "test.py"
    test_file.write_text("# @private 删除\nx = 1\n", encoding="utf-8")

    code, out, err = run_cli(
        str(test_file), "--dry-run", "--marker", "@private"
    )
    assert code == 0
    assert "# @private" not in out
    assert "x = 1" in out


def test_cli_full_mode(tmp_path):
    test_file = tmp_path / "test.py"
    test_file.write_text("# 普通注释\nx = 1\n", encoding="utf-8")

    code, out, err = run_cli(
        str(test_file), "--dry-run", "--mode", "full"
    )
    assert code == 0
    assert "#" not in out
    assert "x = 1" in out
```

### Step 2: 运行测试验证失败
```bash
cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest tests/integration/test_cli.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'markstrip.cli'`

### Step 3: 实现 CLI

创建 `markstrip/cli.py`:

```python
# markstrip/cli.py
"""markstrip 命令行工具。"""
import argparse
import sys
from pathlib import Path

from markstrip.core.config import StripConfig
from markstrip.core.result import StripResult


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

        if not args.dry_run:
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
```

### Step 4: 运行测试验证通过
```bash
cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest tests/integration/test_cli.py -v
```
Expected: all passed

### Step 5: 运行全部测试
```bash
cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest tests/ -v
```
Expected: all passed (41 + 6 = 47)

### Step 6: 提交
```bash
cd d:\WorkPlace\Pycharm\markstrip
git add markstrip/cli.py tests/integration/test_cli.py tests/integration/__init__.py
git commit -m "feat: 添加 CLI 命令行工具"
```

## 重要注意事项
1. 需要创建 `tests/integration/` 目录，可能需要 `__init__.py`
2. 导入顺序遵循 PEP 8：标准库 → 第三方库 → 本地应用
3. `python -m markstrip.cli` 方式运行时需要 `cli.py` 有 `__main__` guard
4. `StripResult` 的导入仅用于类型提示，如未使用可以移除
5. PowerShell 不支持 `&&`，测试命令使用 `;` 分隔
