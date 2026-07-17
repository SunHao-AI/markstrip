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
    test_file = tmp_path / "test.py"
    test_file.write_text("# @internal 删除\nx = 1\n", encoding="utf-8")

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


def test_cli_block_markers(tmp_path):
    """默认块标记 @internal-start/-end 应被识别。"""
    test_file = tmp_path / "test.py"
    test_file.write_text(
        "# @internal-start\n"
        "# inside\n"
        "# @internal-end\n"
        "x = 1\n",
        encoding="utf-8",
    )
    code, out, err = run_cli(str(test_file), "--dry-run")
    assert code == 0
    assert "@internal" not in out
    assert "x = 1" in out


def test_cli_custom_block_markers(tmp_path):
    """显式覆盖块标记。"""
    test_file = tmp_path / "test.py"
    test_file.write_text(
        "# @secret-begin\n"
        "# inside\n"
        "# @secret-end\n"
        "x = 1\n",
        encoding="utf-8",
    )
    code, out, err = run_cli(
        str(test_file), "--dry-run",
        "--block-start-marker", "@secret-begin",
        "--block-end-marker", "@secret-end",
    )
    assert code == 0
    assert "@secret" not in out
    assert "x = 1" in out


def test_cli_verbose_warnings(tmp_path):
    """错配块定界应通过 --verbose 打印 warning。"""
    test_file = tmp_path / "test.py"
    test_file.write_text(
        "# @internal-start\n"
        "x = 1\n",
        encoding="utf-8",
    )
    code, out, err = run_cli(str(test_file), "--dry-run", "--verbose")
    assert code == 0
    assert "Warning:" in err
    assert "@internal-end" in err


class TestCliPragma:
    """CLI pragma 指令集成测试。"""

    def test_cli_pragma_full_overrides_selective(self, tmp_path):
        """文件有 # markstrip: full,CLI selective → 输出 full 效果。"""
        src = tmp_path / "src.py"
        src.write_text(
            "# markstrip: full\n"
            "# 注释\n"
            "x = 1  # 行尾注释\n"
            "y = 2\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            [sys.executable, "-m", "markstrip.cli", str(src), "--dry-run"],
            capture_output=True, text=True,
        )
        assert "# 注释" not in result.stdout
        assert "x = 1" in result.stdout
        assert "y = 2" in result.stdout

    def test_cli_pragma_full_with_cli_full_consistent(self, tmp_path):
        """文件有 pragma + CLI full → 一致(冗余无副作用)。"""
        src = tmp_path / "src.py"
        src.write_text(
            "# markstrip: full\n"
            "# 注释\n"
            "x = 1\n",
            encoding="utf-8",
        )
        r_pragma = subprocess.run(
            [sys.executable, "-m", "markstrip.cli", str(src),
             "--dry-run", "--mode", "selective"],
            capture_output=True, text=True,
        )
        r_full = subprocess.run(
            [sys.executable, "-m", "markstrip.cli", str(src),
             "--dry-run", "--mode", "full"],
            capture_output=True, text=True,
        )
        assert r_pragma.stdout == r_full.stdout

    def test_cli_verbose_pragma_warnings(self, tmp_path):
        """--verbose 输出 pragma 错配警告。"""
        src = tmp_path / "src.py"
        src.write_text(
            "# markstrip: full-end\n"
            "x = 1\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            [sys.executable, "-m", "markstrip.cli", str(src),
             "--dry-run", "--verbose"],
            capture_output=True, text=True,
        )
        assert "Warning:" in result.stderr
        assert "孤立" in result.stderr
