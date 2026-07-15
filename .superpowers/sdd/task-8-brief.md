# Task 8: MarkdownPlugin - HTML 注释 + 兜底测试

## 目标

为 MarkdownPlugin 添加 HTML 注释过滤（`<!-- @internal ... -->`），并测试未知语言兜底。

## 文件清单

- Modify: `markstrip/languages/markdown_plugin.py`
- Golden: `tests/golden/markdown/html_comment.md` + `.expected.md`
- Golden: `tests/golden/markdown/unknown_lang.md` + `.expected.md`
- Test: `tests/unit/test_markdown_plugin.py`（已存在，collect_golden_cases 自动收集新黄金文件）

## 实现变更

1. 添加 `HTML_COMMENT_RE = re.compile(r"<!--.*?-->\n?", re.DOTALL)` — `\n?` 移除注释后清理行尾换行
2. 添加 `_process_html_comments(content, config, mode)` 方法
3. 修改 `strip_selective` 和 `strip_full` 在代码块处理后调用 `_process_html_comments`

## 已知陷阱

### HTML 注释移除后留空行

计划用 `r"<!--.*?-->"` 只匹配注释本身，不移除行尾换行，导致删行后留空行。
修复：用 `r"<!--.*?-->\n?"` 同时匹配换行符。

### selective 模式 col 0 注释留空行

PythonPlugin 的 selective 模式对 col 0 的 `# @internal` 注释用列级删除（非整行删除），结果留空行。
`html_comment.expected.md` 中代码块内 `# @internal` 删除后应留空行。

### line 1 路径注释

`markdown_plugin.py` 第 1 行有 `# markstrip/languages/markdown_plugin.py` 路径注释，可删除。

## TDD 步骤

1. 创建黄金测试文件（4个）
2. 运行测试验证失败（HTML 注释未处理）
3. 实现 HTML 注释处理
4. 运行测试验证通过
5. 提交
