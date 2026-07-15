# Task 2 报告：核心数据结构 (StripConfig, StripResult, errors)

## 实现内容

按照任务简报的规范，实现了 markstrip 库的核心数据结构：

### 1. StripConfig（配置数据类）
- 文件：`markstrip/core/config.py`
- 基于 `@dataclass` 的配置类，包含 5 个字段：
  - `line_marker`：行级标记符号，默认 `@internal`
  - `docstring_marker`：整体 docstring 标记，默认 `@internal-docstring`
  - `preserve_docstrings`：full 模式下是否保留 docstring，默认 `True`
  - `preserve_todo`：full 模式下是否保留 TODO/FIXME，默认 `True`
  - `custom_markers`：自定义额外标记列表，使用 `field(default_factory=list)` 保证实例独立

### 2. StripResult（结果数据类）
- 文件：`markstrip/core/result.py`
- 基于 `@dataclass` 的结果类，包含 4 个字段：
  - `cleaned_content`：清理后的内容（必填）
  - `removed_count`：删除的行数（必填）
  - `detected_language`：检测到的语言标识符，默认空字符串
  - `warnings`：警告信息列表，使用 `field(default_factory=list)` 保证实例独立

### 3. 异常定义
- 文件：`markstrip/core/errors.py`
- 定义了 3 个异常类：
  - `MarkstripError`：基础异常，继承自 `Exception`
  - `PluginNotFoundError`：未找到匹配的语言插件，继承自 `MarkstripError`
  - `TokenizeError`：tokenize 词法分析失败，继承自 `MarkstripError`

## TDD 证据

### RED 阶段（实现前测试失败）

运行 `python -m pytest tests/unit/test_config.py tests/unit/test_result.py -v` 后输出：

```
collected 0 items / 2 errors

ERROR collecting tests/unit/test_config.py
E   ModuleNotFoundError: No module named 'markstrip.core.config'

ERROR collecting tests/unit/test_result.py
E   ModuleNotFoundError: No module named 'markstrip.core.result'

2 errors in 1.48s
```

测试因模块不存在而失败，符合预期。

### GREEN 阶段（实现后测试通过）

运行 `python -m pytest tests/unit/ -v` 后输出：

```
collected 6 items

tests/unit/test_config.py::test_default_config PASSED                    [ 16%]
tests/unit/test_config.py::test_custom_config PASSED                     [ 33%]
tests/unit/test_config.py::test_custom_markers_independent PASSED        [ 50%]
tests/unit/test_result.py::test_basic_result PASSED                      [ 66%]
tests/unit/test_result.py::test_result_with_warnings PASSED              [ 83%]
tests/unit/test_result.py::test_warnings_independent PASSED              [100%]

6 passed in 0.31s
```

全部 6 个测试通过。

## 变更文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `tests/unit/test_config.py` | 新建 | StripConfig 单元测试（3 个测试） |
| `tests/unit/test_result.py` | 新建 | StripResult 单元测试（3 个测试） |
| `markstrip/core/config.py` | 新建 | StripConfig 配置数据类 |
| `markstrip/core/result.py` | 新建 | StripResult 结果数据类 |
| `markstrip/core/errors.py` | 新建 | 异常定义（MarkstripError、PluginNotFoundError、TokenizeError） |

## 提交信息

- Commit SHA: `f11d589`
- 提交消息：`feat: 添加 StripConfig、StripResult 和异常定义`
- 变更统计：5 files changed, 116 insertions(+)

## 问题与说明

1. **终端中文显示乱码**：Windows PowerShell 终端显示 Git 提交消息时出现乱码（GBK/UTF-8 编码差异），但 Git 实际存储的是正确的 UTF-8 编码内容，与 Task 1 提交情况一致，不影响功能。
2. **PEP 8 导入顺序**：所有实现文件均遵循 PEP 8 导入规范（仅使用标准库 `dataclasses`，无第三方或本地导入）。
3. **零运行时依赖**：所有代码仅使用 Python 标准库，符合项目约束。
4. **代码注释**：所有 docstring 和注释均使用中文，符合项目规范。
