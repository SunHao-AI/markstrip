# Task 9: StripEngine + _builtin.py + 公共 API

## 目标

创建主引擎 StripEngine、内置插件注册 _builtin.py、公共 API（strip/strip_file/strip_directory/register_plugin）。

## 文件清单

- Create: `markstrip/core/engine.py`
- Create: `markstrip/languages/_builtin.py`
- Modify: `markstrip/__init__.py`（当前只有 docstring）
- Test: `tests/unit/test_engine.py`

## 关键设计

- `StripEngine.strip()`: 按优先级解析语言（显式 > 扩展名 > 内容探测），返回 StripResult
- `_create_default_registry()`: 注册 PythonPlugin + MarkdownPlugin + entry_points 发现
- 公共 API: `strip()`, `strip_file()`, `strip_directory()`, `register_plugin()`
- 模块级 `_default_engine = StripEngine()` 单例

## 已知陷阱

### removed_count 计算问题

计划用 `len(content.splitlines()) - len(cleaned.splitlines())` 计算 removed_count。
但 selective 模式下 col 0 的 `# @internal` 用列级删除（留空行），行数不变，removed_count=0。
测试 `test_strip_by_language` 期望 `removed_count >= 1`，会失败。

**修复方案**: 统计变更行数（行内容不同）+ 删除行数（行数差）:
```python
original_lines = content.splitlines()
cleaned_lines = cleaned.splitlines()
removed_count = sum(
    1 for o, c in zip(original_lines, cleaned_lines) if o != c
) + max(0, len(original_lines) - len(cleaned_lines))
```

### Windows NamedTemporaryFile

`test_strip_file_inplace` 用 `NamedTemporaryFile(delete=False)`，在 with 块外调用 `strip_file`。
Windows 上需确保文件已关闭再写入。

### _resolve_plugin 访问私有属性

`_resolve_plugin` 用 `self._registry._plugins.values()` 做内容探测，访问私有属性但包内可接受。

## TDD 步骤

1. 编写测试
2. 运行验证失败
3. 实现 _builtin.py
4. 实现 engine.py
5. 实现 __init__.py 公共 API
6. 运行验证通过
7. 提交
