# Task 7: MarkdownPlugin - 代码块解析 + 委托 + 嵌套块

## 目标

创建 MarkdownPlugin，解析 Markdown 围栏代码块后委托给对应语言插件处理。支持嵌套代码块删除。

## 文件清单

- Create: `markstrip/languages/markdown_plugin.py`
- Test: `tests/unit/test_markdown_plugin.py`
- Golden: `tests/golden/markdown/code_block_delegation.md` + `.expected.md`
- Golden: `tests/golden/markdown/nested_codeblock.md` + `.expected.md`

## 接口

- 消费: `LanguagePlugin`(Task 3), `LanguageRegistry`(Task 3), `StripConfig`(Task 2), `PythonPlugin`(Task 6)
- 产出: `MarkdownPlugin` 类, `name="markdown"`, `file_extensions=[".md", ".markdown"]`
- 构造函数: `__init__(self, registry: LanguageRegistry)`
- 方法: `strip_selective`, `strip_full`, `_process_code_blocks`, `_remove_nested_blocks`, `_fallback_strip`

## 关键设计

1. `CODE_BLOCK_RE`: 匹配围栏代码块 `` ```lang\ncode\n``` ``
2. `NESTED_BLOCK_RE`: 匹配代码块内的嵌套 ``` 对
3. `_process_code_blocks`: 遍历代码块，先删嵌套块，再委托语言插件
4. `_fallback_strip`: 未知语言的正则兜底（yaml/bash 用 #, js/java/c 用 //）

## 已知陷阱

### 嵌套围栏正则问题

计划中的 `CODE_BLOCK_RE` 使用非贪婪 `.*?` 配合 `(?P=fence)` 反向引用。
当代码块内含嵌套 ``` 标记时（如 `nested_codeblock.md`），非贪婪匹配会在第一个内嵌 ``` 处提前结束，导致外层代码块被截断。

**修复方案**: 在 `(?P=fence)` 前加 `^` 并启用 `re.MULTILINE`，要求闭合围栏在行首（无前导空格），从而跳过有缩进的内嵌围栏：

```python
CODE_BLOCK_RE = re.compile(
    r"^(?P<fence>`{3,})(?P<lang>\w*)\n(?P<code>.*?)(?P=fence)",
    re.DOTALL | re.MULTILINE,
)
```

### PythonPlugin.strip_selective 返回 str

PythonPlugin 的 `strip_selective` 返回 `str`（非 StripResult）。测试中直接 `assert result == expected`。

### collect_golden_cases 对 markdown 的支持

`collect_golden_cases("markdown", ".md")` 会匹配 `tests/golden/markdown/` 下的 `*.md` 文件（排除 `.expected.md`），配对 `xxx.md` 和 `xxx.expected.md`。

## TDD 步骤

1. 创建黄金测试文件
2. 创建单元测试
3. 运行测试验证失败（ModuleNotFoundError）
4. 实现 MarkdownPlugin
5. 运行测试验证通过
6. 提交
