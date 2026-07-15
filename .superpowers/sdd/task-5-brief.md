### Task 5: PythonPlugin - docstring 处理

**Files:**
- Modify: `markstrip/languages/python_plugin.py`
- Golden: `tests/golden/python/docstring_selective.py`, `tests/golden/python/docstring_selective.expected.py`, `tests/golden/python/docstring_whole.py`, `tests/golden/python/docstring_whole.expected.py`

**Interfaces:**
- Consumes: `PythonPlugin`（Task 4）
- Produces: 在 `strip_selective` 中增加 docstring 处理逻辑
- 新增方法: `_is_docstring(tok, tokens) -> bool`, `_process_docstring(tok, config) -> list[tuple[int, int, int]]`

**IMPORTANT ADAPTATION:** Task 4 changed `_rebuild` to use column-level deletion format: `list[tuple[int, int, int]]` = (line_num, start_col, end_col), 1-based line, 0-based columns. The docstring processing must produce ranges in this format.

- For @internal lines within docstrings: produce (line_num, 0, len_of_line_content) to blank the line (keep empty line)
- For @internal-docstring whole removal: produce (line_num, 0, -1) for each line of the docstring to remove entire lines including newlines. You MUST modify `_rebuild` to handle end_col=-1 (or a similar sentinel) as "remove entire line including newline".

- [ ] **Step 1: 创建黄金测试文件 — docstring 逐行标记**

`tests/golden/python/docstring_selective.py`:
```python
def online_predict():
    """
    Online 推理任务调度

    @internal 本模块调度任务到 native worker
    @internal native worker 使用 solo pool 模式

    Online 任务双重超时控制:
    Layer 1: requests.timeout
    """

    timeout = 1
    return timeout
```

`tests/golden/python/docstring_selective.expected.py`:
```python
def online_predict():
    """
    Online 推理任务调度


    Online 任务双重超时控制:
    Layer 1: requests.timeout
    """

    timeout = 1
    return timeout
```

- [ ] **Step 2: 创建黄金测试文件 — docstring 整体标记**

`tests/golden/python/docstring_whole.py`:
```python
def online_predict():
    """
    @internal-docstring
    Online 推理任务调度 - 自适应超时策略

    本模块调度任务到 native worker
    native worker 使用 solo pool 模式
    """

    timeout = 1
    return timeout
```

`tests/golden/python/docstring_whole.expected.py`:
```python
def online_predict():

    timeout = 1
    return timeout
```

- [ ] **Step 3: 运行测试验证新增黄金文件失败**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest tests/unit/test_python_plugin.py -v -k "docstring"`
Expected: FAIL — docstring 内的 @internal 行未被删除

- [ ] **Step 4: 实现 docstring 处理逻辑**

修改 `markstrip/languages/python_plugin.py`:

1. 在 import 区域添加 `ast`:
```python
import ast
import re
import tokenize
```

2. 修改 `strip_selective` 方法，在 COMMENT 处理后添加 STRING 处理:
```python
    def strip_selective(self, content: str, config: StripConfig) -> str:
        """标记式选择性过滤：仅删除含 @internal 标记的注释。"""
        lines = content.splitlines(keepends=True)
        comment_removals: list[tuple[int, int, int]] = []

        try:
            tokens = list(tokenize.tokenize(
                iter(content.encode("utf-8").splitlines(True)).__next__
            ))
        except tokenize.TokenizeError:
            return self._fallback_regex_selective(content, config)

        for tok in tokens:
            if tok.type == tokenize.COMMENT:
                if self._has_marker(tok.string, config):
                    comment_removals.append(
                        (tok.start[0], tok.start[1], tok.end[1])
                    )

            if tok.type == tokenize.STRING:
                if self._is_docstring(tok, tokens):
                    doc_removals = self._process_docstring(tok, config, lines)
                    comment_removals.extend(doc_removals)

        return self._rebuild(lines, comment_removals)
```

3. 添加 `_is_docstring` 方法:
```python
    def _is_docstring(
        self,
        tok: tokenize.TokenInfo,
        tokens: list[tokenize.TokenInfo],
    ) -> bool:
        """判断 STRING token 是否为 docstring。

        docstring 是模块、类或函数体的首条语句。

        Args:
            tok: 待判断的 token。
            tokens: 完整 token 列表。

        Returns:
            是否为 docstring。
        """
        # 简化判断：三引号字符串且前一个非空 token 是 NEWLINE/INDENT/DEDENT
        # 或位于文件开头
        idx = tokens.index(tok)
        # 向前查找第一个非 NL/NEWLINE token
        prev_idx = idx - 1
        while prev_idx >= 0 and tokens[prev_idx].type in (
            tokenize.NL,
            tokenize.NEWLINE,
        ):
            prev_idx -= 1

        if prev_idx < 0:
            # 文件开头，是模块 docstring
            return True

        prev = tokens[prev_idx]
        # 前一个是 INDENT 或 COLON 后的 NEWLINE → 可能是函数/类体首语句
        if prev.type in (tokenize.INDENT, tokenize.DEDENT):
            return True
        # 前一个是冒号 → 函数/类定义后的首语句
        if prev.type == tokenize.OP and prev.string == ":":
            return True
        # 简化：多行字符串（含换行）也可能是 docstring
        if "\n" in tok.string:
            return True
        return False
```

4. 添加 `_process_docstring` 方法:
```python
    def _process_docstring(
        self,
        tok: tokenize.TokenInfo,
        config: StripConfig,
        lines: list[str],
    ) -> list[tuple[int, int, int]]:
        """处理单个 docstring，返回需删除的位置。

        Args:
            tok: docstring 的 STRING token。
            config: 清理配置。
            lines: 原始行列表。

        Returns:
            需要删除的 (line_num, start_col, end_col) 列表。
            end_col=-1 表示删除整行（含换行符）。
        """
        try:
            content = ast.literal_eval(tok.string)
        except (ValueError, SyntaxError):
            return []

        doc_lines = content.split("\n")

        # 检查 @internal-docstring 标记（整体删除）
        first_line = doc_lines[0].strip() if doc_lines else ""
        if first_line.startswith(config.docstring_marker):
            # 删除整个 docstring 的所有行
            removals = []
            for line_num in range(tok.start[0], tok.end[0] + 1):
                removals.append((line_num, 0, -1))  # -1 = 删除整行
            return removals

        # 逐行检查 @internal 标记
        markers = [config.line_marker] + config.custom_markers
        removals: list[tuple[int, int, int]] = []
        for i, line in enumerate(doc_lines):
            stripped = line.strip()
            for marker in markers:
                if stripped.startswith(marker):
                    # 映射到源文件行号，清空该行内容（保留空行）
                    source_line = tok.start[0] + i
                    # 获取该行的长度（不含换行符）
                    if source_line - 1 < len(lines):
                        line_content = lines[source_line - 1].rstrip("\r\n")
                        removals.append(
                            (source_line, 0, len(line_content))
                        )
                    break

        return removals
```

5. 修改 `_rebuild` 方法以支持 end_col=-1（删除整行含换行符）:
在 `_rebuild` 方法中，处理 end_col == -1 的情况：
```python
    def _rebuild(
        self,
        lines: list[str],
        comment_removals: list[tuple[int, int, int]],
    ) -> str:
        """按注释位置重组代码，保留非注释部分。

        Args:
            lines: 原始行列表（splitlines(keepends=True)）。
            comment_removals: 需要删除的注释信息列表
                (行号, 起始列, 结束列)，1-based 行号，0-based 列。
                end_col=-1 表示删除整行（含换行符）。

        Returns:
            重组后的内容。
        """
        if not comment_removals:
            return "".join(lines)

        # 按行号分组
        removals_by_line: dict[int, list[tuple[int, int]]] = {}
        full_line_removals: set[int] = set()

        for line_num, start_col, end_col in comment_removals:
            if end_col == -1:
                full_line_removals.add(line_num)
            else:
                removals_by_line.setdefault(line_num, []).append(
                    (start_col, end_col)
                )

        result = []
        for i, line in enumerate(lines, start=1):
            if i in full_line_removals:
                # 删除整行（含换行符）
                continue

            if i not in removals_by_line:
                result.append(line)
                continue

            # 处理含标记注释的行
            # 分离换行符和内容
            newline = ""
            content_part = line
            if line.endswith("\r\n"):
                newline = "\r\n"
                content_part = line[:-2]
            elif line.endswith("\n"):
                newline = "\n"
                content_part = line[:-1]
            elif line.endswith("\r"):
                newline = "\r"
                content_part = line[:-1]

            # 按列位置从后往前删除注释文本
            removals = sorted(removals_by_line[i], reverse=True)
            for start_col, end_col in removals:
                before = content_part[:start_col]
                after = content_part[end_col:]
                content_part = before + after

            # 如果删除后内容为空且只有空白，也保留换行符
            result.append(content_part + newline)

        return "".join(result)
```

- [ ] **Step 5: 运行测试验证通过**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest tests/unit/test_python_plugin.py -v`
Expected: all passed（包括新的 docstring 黄金文件测试）

- [ ] **Step 6: 提交**

```bash
cd d:\WorkPlace\Pycharm\markstrip
git add markstrip/languages/python_plugin.py tests/golden/python/docstring_selective.py tests/golden/python/docstring_selective.expected.py tests/golden/python/docstring_whole.py tests/golden/python/docstring_whole.expected.py
git commit -m "feat: 添加 PythonPlugin docstring 选择性过滤和整体删除"
```
