# Task 4 报告：PythonPlugin - selective 模式（行注释）

## 实现内容

### 新建文件

1. **`markstrip/languages/python_plugin.py`** — PythonPlugin 语言插件实现
   - `name` 属性返回 `"python"`
   - `file_extensions` 返回 `[".py", ".pyw", ".pyi"]`
   - `strip_selective(content, config)` — 使用 `tokenize` 词法分析精确定位含 `@internal` 标记的注释并删除
   - `strip_full(content, config)` — 占位方法，返回原内容（Task 6 实现）
   - `_has_marker(comment_text, config)` — 检查注释是否包含标记（支持 `line_marker` 和 `custom_markers`）
   - `_rebuild(lines, comment_removals)` — 按注释精确位置重组代码
   - `_fallback_regex_selective(content, config)` — tokenize 失败时的正则回退

2. **`tests/conftest.py`** — pytest 公共配置和黄金文件测试工具
   - `collect_golden_cases(lang, suffix)` — 自动匹配 `xxx.py` 和 `xxx.expected.py` 文件对

3. **`tests/unit/test_python_plugin.py`** — PythonPlugin 单元测试
   - `test_plugin_name` — 验证插件名称
   - `test_plugin_extensions` — 验证文件扩展名
   - `test_python_selective_golden` — 参数化黄金文件测试（2 个用例）

4. **黄金测试文件**（4 个）：
   - `tests/golden/python/internal_comment.py` + `.expected.py` — 行注释场景
   - `tests/golden/python/string_with_hash.py` + `.expected.py` — 字符串中含 # 的场景

## TDD 证据

### RED 阶段
```
ModuleNotFoundError: No module named 'markstrip.languages.python_plugin'
```
测试因模块不存在而无法收集，符合预期。

### GREEN 阶段
```
tests/unit/test_python_plugin.py::test_plugin_name PASSED                [ 25%]
tests/unit/test_python_plugin.py::test_plugin_extensions PASSED          [ 50%]
tests/unit/test_python_plugin.py::test_python_selective_golden[internal_comment] PASSED [ 75%]
tests/unit/test_python_plugin.py::test_python_selective_golden[string_with_hash] PASSED [100%]
============================== 4 passed in 0.13s ==============================
```

全量回归：16/16 通过（含原有 12 个测试）。

## 变更文件

| 文件 | 操作 |
|------|------|
| `markstrip/languages/python_plugin.py` | 新建 |
| `tests/conftest.py` | 新建 |
| `tests/unit/test_python_plugin.py` | 新建 |
| `tests/golden/python/internal_comment.py` | 新建 |
| `tests/golden/python/internal_comment.expected.py` | 新建 |
| `tests/golden/python/string_with_hash.py` | 新建 |
| `tests/golden/python/string_with_hash.expected.py` | 新建 |

## 设计说明：与 brief 算法的偏差

brief 中的 `_rebuild` 方法按 `(start_line, end_line)` 行号范围**整行删除**。但黄金文件期望输出表明：
- 独立注释行（如 `# @internal ...`）→ 变为空行（保留换行符）
- 行尾注释（如 `x = 1  # @internal ...`）→ 仅删除注释部分，保留代码 `x = 1`

因此对 `_rebuild` 进行了修正：改为记录注释的精确列位置 `(行号, 起始列, 结束列)`，按列删除注释文本。删除后若该行仅剩空白则整行变空；若仍有代码则去除行尾多余空白。其余方法（`strip_selective`、`_has_marker`、`strip_full`、`_fallback_regex_selective`）均与 brief 一致。

## 提交信息

- SHA: `811a9fe`
- 消息: `feat: 添加 PythonPlugin selective 模式（行注释过滤）`

## 问题与关注点

- **`_rebuild` 方法签名变更**：brief 中签名为 `_rebuild(lines, remove_ranges: list[tuple[int, int]])`，实际改为 `_rebuild(lines, comment_removals: list[tuple[int, int, int]])` 以支持精确列级删除。这是为了匹配黄金文件期望输出而做的必要修正。
- **`strip_full` 为占位**：按 brief 要求返回原内容，Task 6 将实现。
- **正则回退不处理行尾注释**：`_fallback_regex_selective` 仅处理独立注释行（`^\s*#\s*{marker}.*$`），不处理行尾注释。这在 tokenize 失败的极端场景下可能不完全匹配，但属于回退降级行为，可接受。
