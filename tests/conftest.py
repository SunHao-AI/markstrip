# tests/conftest.py
"""pytest 公共配置和黄金文件测试工具。"""
from pathlib import Path

GOLDEN_DIR = Path(__file__).parent / "golden"


def collect_golden_cases(lang: str, suffix: str = ".py"):
    """收集黄金测试用例。

    自动匹配 xxx.py 和 xxx.expected.py 文件对。
    """
    cases = []
    lang_dir = GOLDEN_DIR / lang
    if not lang_dir.exists():
        return cases
    for input_file in lang_dir.glob(f"*{suffix}"):
        if input_file.name.endswith(f".expected{suffix}"):
            continue
        expected_file = input_file.with_name(
            input_file.stem + f".expected{suffix}"
        )
        if expected_file.exists():
            cases.append((str(input_file), str(expected_file)))
    return cases
