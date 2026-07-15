# Task 6 报告：PythonPlugin - strip_full + 保留规则 + 语法错误回退

## 实现内容

为 PythonPlugin 添加了全量注释删除模式（`strip_full`），实现了保留规则和语法错误回退。

### 新增/修改的方法

- **`strip_full(content, config) -> str`**：全量注释删除。使用 tokenize 词法分析定位所有 COMMENT 和 STRING token。删除所有非保留注释，保留 shebang/编码声明/TODO/FIXME/类型注释。docstring 根据 `preserve_docstrings` 配置决定保留或删除。语法错误时（`tokenize.TokenError`）直接返回原内容。
- **`_is_preserved_comment(tok, config) -> bool`**：判断注释是否应被保留。依次检查 shebang（`#!`）、编码声明（`coding:`/`coding=`）、TODO/FIXME（受 `preserve_todo` 控制）、类型注释（`# type:`）。

### 修复的 Bug

- **`tokenize.TokenizeError` → `tokenize.TokenError`**：`strip_selective` 中的异常捕获使用了不存在的 `tokenize.TokenizeError`，应为 `tokenize.TokenError`。此 bug 在 Task 5 中引入，但之前没有任何测试触发 tokenize 失败路径，因此未被发现。本次添加的 `syntax_error.py` 黄金测试文件首次触发了该路径，暴露了此 bug。

## TDD 证据

### RED 阶段

创建黄金测试文件和单元测试后，运行 `python -m pytest tests/unit/test_python_plugin.py -v`，5 个测试失败：

```
FAILED tests/unit/test_python_plugin.py::test_python_selective_golden[full_mode]
FAILED tests/unit/test_python_plugin.py::test_python_selective_golden[syntax_error]
FAILED tests/unit/test_python_plugin.py::test_strip_full_removes_comments
FAILED tests/unit/test_python_plugin.py::test_strip_full_removes_docstrings_when_configured
FAILED tests/unit/test_python_plugin.py::test_python_full_golden[full_mode]
5 failed, 11 passed in 0.60s
```

失败原因：
1. `strip_full` 当前为占位符，直接返回原内容
2. `tokenize.TokenizeError` 不存在，导致 syntax_error 的异常捕获失败
3. `full_mode.py` 被选择性黄金测试捕获，但期望输出是 full 模式的输出

### GREEN 阶段

实现 `strip_full`、`_is_preserved_comment`，修复 `tokenize.TokenError`，修改选择性测试排除 "full" 文件后，运行全部测试：

```
tests/unit/test_python_plugin.py::test_plugin_name PASSED
tests/unit/test_python_plugin.py::test_plugin_extensions PASSED
tests/unit/test_python_plugin.py::test_python_selective_golden[docstring_selective] PASSED
tests/unit/test_python_plugin.py::test_python_selective_golden[docstring_whole] PASSED
tests/unit/test_python_plugin.py::test_python_selective_golden[internal_comment] PASSED
tests/unit/test_python_plugin.py::test_python_selective_golden[string_with_hash] PASSED
tests/unit/test_python_plugin.py::test_python_selective_golden[syntax_error] PASSED
tests/unit/test_python_plugin.py::test_strip_full_removes_comments PASSED
tests/unit/test_python_plugin.py::test_strip_full_preserves_shebang PASSED
tests/unit/test_python_plugin.py::test_strip_full_preserves_todo PASSED
tests/unit/test_python_plugin.py::test_strip_full_preserves_encoding PASSED
tests/unit/test_python_plugin.py::test_strip_full_preserves_type_comment PASSED
tests/unit/test_python_plugin.py::test_strip_full_removes_docstrings_when_configured PASSED
tests/unit/test_python_plugin.py::test_strip_full_preserves_docstrings_by_default PASSED
tests/unit/test_python_plugin.py::test_python_full_golden[full_mode] PASSED
15 passed in 0.34s
```

全量测试 `python -m pytest -v`：27 passed in 0.28s。

## 偏离 brief 的地方

### 1. 列号为 0 的注释使用整行删除

Brief 中的 `strip_full` 代码对所有非保留注释统一使用列级删除 `(tok.start[0], tok.start[1], tok.end[1])`。但 brief 的期望文件 `full_mode.expected.py` 中，列号为 0 的注释行（如 `# 普通注释，应删除`）被完全移除（不留空行），而列级删除会产生空行。

**修改**：当注释起始列为 0 时，使用 `(line_num, 0, -1)` 触发整行删除（含换行符）。列号大于 0 的注释仍使用列级删除，删除注释后行内容为空白则变为空行（保留换行符）。这与期望文件行为一致：

- `# 普通注释` (col 0) → 整行删除
- `    # 函数内注释` (col 4) → 列级删除 → 空行
- `    x = 1  # 行尾注释` (col 11) → 列级删除 → rstrip

### 2. 修复 tokenize.TokenizeError → tokenize.TokenError

Brief 中 `strip_full` 和现有 `strip_selective` 都使用了 `tokenize.TokenizeError`，但 Python 标准库中该异常类名为 `tokenize.TokenError`。在 `strip_selective` 和 `strip_full` 中均修正为 `tokenize.TokenError`。

### 3. 选择性黄金测试排除 "full" 文件

Brief 未提及修改选择性黄金测试，但添加 `full_mode.py` 后，该文件会被 `test_python_selective_golden` 自动捕获。由于 `full_mode.expected.py` 是 full 模式的期望输出（非 selective 模式），selective 测试会失败。

**修改**：将选择性黄金测试参数化列表改为 `_selective_golden_cases`，过滤掉文件名含 "full" 的用例，与 full 模式黄金测试（仅测试含 "full" 的用例）形成互补。

### 4. syntax_error.expected.py 修正

Brief 中的 `syntax_error.expected.py` 缺少 `    # 语法错误，缺少右括号` 行。在 selective 模式下，tokenize 失败后走正则回退 `_fallback_regex_selective`，正则只删除含 `@internal` 的行，非 `@internal` 的 `# 语法错误` 行应保留。

**修改**：期望文件中保留 `    # 语法错误，缺少右括号` 行，与正则回退的实际行为一致。

## 变更文件

| 文件 | 操作 |
|------|------|
| `markstrip/languages/python_plugin.py` | 修改：实现 strip_full 和 _is_preserved_comment，修复 TokenizeError bug |
| `tests/unit/test_python_plugin.py` | 修改：追加 7 个 strip_full 单元测试、1 个 full 模式黄金测试，修改选择性测试排除 "full" 文件 |
| `tests/golden/python/full_mode.py` | 新增：full 模式黄金输入 |
| `tests/golden/python/full_mode.expected.py` | 新增：full 模式黄金期望输出 |
| `tests/golden/python/syntax_error.py` | 新增：语法错误回退黄金输入 |
| `tests/golden/python/syntax_error.expected.py` | 新增：语法错误回退黄金期望输出（selective 模式） |

## 提交

- Commit: `8baec6e` - feat: 添加 PythonPlugin strip_full 模式和保留规则
- 6 files changed, 180 insertions(+), 6 deletions(-)
