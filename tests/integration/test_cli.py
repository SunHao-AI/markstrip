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


class TestCliCheck:
    """CLI --check 模式集成测试。"""

    def test_check_clean_file_exit_0(self, tmp_path):
        """无标记文件 --check 应 exit 0,stderr 含 'No markers found'。"""
        test_file = tmp_path / "clean.py"
        test_file.write_text("# normal comment\nx = 1\n", encoding="utf-8")
        code, out, err = run_cli(str(test_file), "--check")
        assert code == 0
        assert "No markers found" in err

    def test_check_marked_file_exit_1(self, tmp_path):
        """有标记文件 --check 应 exit 1,stderr 含 ':line:' 与标记类型。"""
        test_file = tmp_path / "marked.py"
        test_file.write_text(
            "# @internal secret\nx = 1\n", encoding="utf-8"
        )
        code, out, err = run_cli(str(test_file), "--check")
        assert code == 1
        assert "@internal" in err
        assert "(line)" in err

    def test_check_recursive_directory(self, tmp_path):
        """递归目录 --check 汇总输出。"""
        sub = tmp_path / "sub"
        sub.mkdir()
        (tmp_path / "a.py").write_text(
            "# @internal a\nx = 1\n", encoding="utf-8"
        )
        (sub / "b.py").write_text(
            "# @internal b\ny = 2\n", encoding="utf-8"
        )
        code, out, err = run_cli(str(tmp_path), "--recursive", "--check")
        assert code == 1
        assert "Found 2 markers in 2 files" in err

    def test_check_mode_full_conflict_exit_2(self, tmp_path):
        """--check --mode full 互斥 exit 2。"""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n", encoding="utf-8")
        code, out, err = run_cli(str(test_file), "--check", "--mode", "full")
        assert code == 2
        assert "冲突" in err or "互斥" in err

    def test_check_output_conflict_exit_2(self, tmp_path):
        """--check --output 互斥 exit 2。"""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n", encoding="utf-8")
        out_file = tmp_path / "out.py"
        code, out, err = run_cli(
            str(test_file), "--check", "--output", str(out_file)
        )
        assert code == 2
        assert "冲突" in err or "互斥" in err

    def test_check_custom_marker(self, tmp_path):
        """--check --marker @private 同步检测。"""
        test_file = tmp_path / "test.py"
        test_file.write_text("# @private x\ny = 1\n", encoding="utf-8")
        code, out, err = run_cli(
            str(test_file), "--check", "--marker", "@private"
        )
        assert code == 1
        assert "@private" in err


class TestCliStdin:
    """CLI stdin 管道集成测试。"""

    def test_stdin_basic_pipe(self, tmp_path):
        """markstrip - < file.py:stdout 输出清理后内容。"""
        input_file = tmp_path / "input.py"
        input_file.write_text(
            "# @internal x\ny = 1\n", encoding="utf-8"
        )
        result = subprocess.run(
            [sys.executable, "-m", "markstrip.cli", "-"],
            stdin=open(input_file, "r", encoding="utf-8"),
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "# @internal" not in result.stdout
        assert "y = 1" in result.stdout

    def test_stdin_with_language(self, tmp_path):
        """echo '...' | markstrip - --language python:显式语言。"""
        result = subprocess.run(
            [sys.executable, "-m", "markstrip.cli", "-",
             "--language", "python"],
            input="# @internal x\ny = 1\n",
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "# @internal" not in result.stdout
        assert "y = 1" in result.stdout

    def test_stdin_check_mode(self, tmp_path):
        """cat file | markstrip --check -:stderr 含标记,stdout 空。"""
        result = subprocess.run(
            [sys.executable, "-m", "markstrip.cli", "--check", "-"],
            input="# @internal x\ny = 1\n",
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "@internal" in result.stderr
        assert result.stdout == ""

    def test_stdin_recursive_conflict_exit_2(self):
        """markstrip - --recursive 互斥 exit 2。"""
        result = subprocess.run(
            [sys.executable, "-m", "markstrip.cli", "-", "--recursive"],
            input="x = 1\n",
            capture_output=True, text=True,
        )
        assert result.returncode == 2
        assert "递归" in result.stderr or "recursive" in result.stderr.lower()

    def test_stdin_output_to_file(self, tmp_path):
        """markstrip - -o out.py < file.py:写入文件,stdout 空。"""
        input_file = tmp_path / "in.py"
        input_file.write_text("# @internal x\ny = 1\n", encoding="utf-8")
        out_file = tmp_path / "out.py"
        result = subprocess.run(
            [sys.executable, "-m", "markstrip.cli", "-",
             "-o", str(out_file)],
            stdin=open(input_file, "r", encoding="utf-8"),
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert result.stdout == ""
        content = out_file.read_text(encoding="utf-8")
        assert "@internal" not in content
        assert "y = 1" in content
