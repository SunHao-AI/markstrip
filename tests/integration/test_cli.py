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
