### Task 6: PythonPlugin - strip_full + 保留规则 + 语法错误回退

**Files:**
- Modify: `markstrip/languages/python_plugin.py`
- Modify: `tests/unit/test_python_plugin.py` (追加测试)
- Golden: `tests/golden/python/full_mode.py`, `tests/golden/python/full_mode.expected.py`, `tests/golden/python/syntax_error.py`, `tests/golden/python/syntax_error.expected.py`

**Interfaces:**
- Consumes: `PythonPlugin`（Task 5）
- Produces: `strip_full` 完整实现、`_is_preserved_comment` 方法

**IMPORTANT ADAPTATION:** The current `_rebuild` method uses `list[tuple[int, int, int]]` format: (line_num, start_col, end_col), 1-based line, 0-based columns. end_col=-1 means remove entire line. The strip_full implementation MUST use this format, NOT the `list[tuple[int, int]]` format from the plan.

- [ ] **Step 1: 创建黄金测试文件 — full 模式**

`tests/golden/python/full_mode.py`:
```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# TODO: 需要修复此问题
# FIXME: 另一个待修复项
# 普通注释，应删除
# type: ignore
import os


def func():
    """这是 docstring。"""
    # 函数内注释，应删除
    x = 1  # 行尾注释，应删除
    return x
```

`tests/golden/python/full_mode.expected.py`:
```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# TODO: 需要修复此问题
# FIXME: 另一个待修复项
# type: ignore
import os


def func():
    """这是 docstring。"""

    x = 1
    return x
```

> 注意：默认 `preserve_docstrings=True`，所以 docstring 保留。

- [ ] **Step 2: 创建黄金测试文件 — 语法错误回退**

`tests/golden/python/syntax_error.py`:
```python
# @internal 这行应被正则删除
def broken(
    # 语法错误，缺少右括号
    x = 1
# @internal 正则回退也应删除这行
```

`tests/golden/python/syntax_error.expected.py`:
```python
def broken(
    x = 1
```

> 注意：syntax_error 的 expected 文件用于 selective 模式（strip_selective），不是 full 模式。selective 模式下 tokenize 失败会走 _fallback_regex_selective 正则回退。

- [ ] **Step 3: 编写 strip_full 测试**

在 `tests/unit/test_python_plugin.py` 中追加：

```python
def test_strip_full_removes_comments(plugin, config):
    content = "# 普通注释\nx = 1\n"
    result = plugin.strip_full(content, config)
    assert "#" not in result
    assert "x = 1" in result


def test_strip_full_preserves_shebang(plugin, config):
    content = "#!/usr/bin/env python\nx = 1\n"
    result = plugin.strip_full(content, config)
    assert "#!/usr/bin/env python" in result


def test_strip_full_preserves_todo(plugin, config):
    content = "# TODO: fix later\nx = 1\n"
    result = plugin.strip_full(content, config)
    assert "TODO" in result


def test_strip_full_preserves_encoding(plugin, config):
    content = "# -*- coding: utf-8 -*-\nx = 1\n"
    result = plugin.strip_full(content, config)
    assert "coding" in result


def test_strip_full_preserves_type_comment(plugin, config):
    content = "# type: ignore\nx = 1\n"
    result = plugin.strip_full(content, config)
    assert "type: ignore" in result


def test_strip_full_removes_docstrings_when_configured(plugin):
    content = 'def f():\n    """docstring"""\n    return 1\n'
    config = StripConfig(preserve_docstrings=False)
    result = plugin.strip_full(content, config)
    assert '"""docstring"""' not in result


def test_strip_full_preserves_docstrings_by_default(plugin, config):
    content = 'def f():\n    """docstring"""\n    return 1\n'
    result = plugin.strip_full(content, config)
    assert '"""docstring"""' in result
```

并在黄金文件参数化测试中添加 full 模式测试（只测试文件名含 `full` 的用例）：

```python
@pytest.mark.parametrize(
    "input_file,expected_file",
    [(i, e) for i, e in collect_golden_cases("python")
     if "full" in Path(i).stem],
    ids=[Path(f).stem for f, e in [(i, e) for i, e in collect_golden_cases("python")
     if "full" in Path(i).stem]],
)
def test_python_full_golden(input_file, expected_file):
    plugin = PythonPlugin()
    config = StripConfig()
    content = Path(input_file).read_text(encoding="utf-8")
    expected = Path(expected_file).read_text(encoding="utf-8")
    result = plugin.strip_full(content, config)
    assert result == expected
```

- [ ] **Step 4: 运行测试验证失败**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest tests/unit/test_python_plugin.py -v`
Expected: FAIL — `strip_full` 当前返回原内容

- [ ] **Step 5: 实现 strip_full 和 _is_preserved_comment**

修改 `markstrip/languages/python_plugin.py`，替换 `strip_full` 方法（当前是占位符 `return content`）。

IMPORTANT: 使用 `list[tuple[int, int, int]]` 格式（与现有 `_rebuild` 兼容）：

```python
    def strip_full(self, content: str, config: StripConfig) -> str:
        """全量注释删除：删除所有注释，保留 shebang/TODO 等。

        Args:
            content: Python 源代码内容。
            config: 清理配置。

        Returns:
            清理后的内容。
        """
        lines = content.splitlines(keepends=True)
        comment_removals: list[tuple[int, int, int]] = []

        try:
            tokens = list(tokenize.tokenize(
                iter(content.encode("utf-8").splitlines(True)).__next__
            ))
        except tokenize.TokenizeError:
            # 语法错误时无法处理，直接返回原内容
            return content

        for tok in tokens:
            if tok.type == tokenize.COMMENT:
                if self._is_preserved_comment(tok, config):
                    continue
                # 使用列级删除格式：(行号, 起始列, 结束列)
                comment_removals.append(
                    (tok.start[0], tok.start[1], tok.end[1])
                )

            if tok.type == tokenize.STRING:
                if self._is_docstring(tok, tokens):
                    if not config.preserve_docstrings:
                        # 删除整个 docstring 的所有行
                        for line_num in range(tok.start[0], tok.end[0] + 1):
                            comment_removals.append((line_num, 0, -1))

        return self._rebuild(lines, comment_removals)

    def _is_preserved_comment(
        self,
        tok: tokenize.TokenInfo,
        config: StripConfig,
    ) -> bool:
        """判断注释是否应被保留（full 模式）。

        Args:
            tok: COMMENT token。
            config: 清理配置。

        Returns:
            True 表示保留，False 表示删除。
        """
        text = tok.string.strip()
        # 保留 shebang
        if text.startswith("#!"):
            return True
        # 保留编码声明
        if "coding:" in text or "coding=" in text:
            return True
        # 保留 TODO/FIXME
        if config.preserve_todo and (
            "TODO" in text or "FIXME" in text
        ):
            return True
        # 保留类型注释
        if text.startswith("# type:"):
            return True
        return False
```

- [ ] **Step 6: 运行测试验证通过**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest tests/unit/test_python_plugin.py -v`
Expected: all passed

- [ ] **Step 7: 提交**

```bash
cd d:\WorkPlace\Pycharm\markstrip
git add markstrip/languages/python_plugin.py tests/unit/test_python_plugin.py tests/golden/python/full_mode.py tests/golden/python/full_mode.expected.py tests/golden/python/syntax_error.py tests/golden/python/syntax_error.expected.py
git commit -m "feat: 添加 PythonPlugin strip_full 模式和保留规则"
```
