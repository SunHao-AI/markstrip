# Task 3 报告：LanguagePlugin 抽象基类 + LanguageRegistry

## 实现内容

### 1. LanguagePlugin 抽象基类 (`markstrip/languages/base.py`)
- 基于 `abc.ABC` 的抽象基类，定义语言插件接口
- 抽象属性：`name`（语言标识符）、`file_extensions`（支持的扩展名列表）
- 抽象方法：`strip_selective`（标记式选择性过滤）、`strip_full`（全量注释删除）
- 具体方法：`detect`（内容探测，默认返回 False，子类可覆盖）

### 2. LanguageRegistry 注册表 (`markstrip/languages/registry.py`)
- `register(plugin)`：注册插件，同时建立扩展名到语言名的映射
- `get_plugin(name)`：按名称查找（大小写不敏感，使用 `name.lower()`）
- `get_plugin_by_extension(ext)`：按扩展名查找，通过扩展名映射表间接定位插件
- `list_languages()`：返回所有已注册语言标识符列表
- 重复注册同名插件会覆盖旧实例（符合测试 `test_register_overwrites`）

### 3. 单元测试 (`tests/unit/test_registry.py`)
6 个测试用例，覆盖核心场景：
- `test_register_and_get_by_name`：注册并按名获取
- `test_get_by_name_case_insensitive`：大小写不敏感查找
- `test_get_by_extension`：按扩展名查找
- `test_get_unknown_plugin`：未知语言返回 None
- `test_list_languages`：列出所有已注册语言
- `test_register_overwrites`：重复注册覆盖旧插件

## TDD 证据

### RED 阶段
```
ImportError while importing test module 'tests/unit/test_registry.py'.
tests\unit\test_registry.py:3: in <module>
    from markstrip.languages.base import LanguagePlugin
E   ModuleNotFoundError: No module named 'markstrip.languages.base'
=========================== short test summary info ===========================
ERROR tests/unit/test_registry.py
1 error in 0.50s
```

### GREEN 阶段
```
tests/unit/test_registry.py::test_register_and_get_by_name PASSED        [ 16%]
tests/unit/test_registry.py::test_get_by_name_case_insensitive PASSED    [ 33%]
tests/unit/test_registry.py::test_get_by_extension PASSED                [ 50%]
tests/unit/test_registry.py::test_get_unknown_plugin PASSED              [ 66%]
tests/unit/test_registry.py::test_list_languages PASSED                  [ 83%]
tests/unit/test_registry.py::test_register_overwrites PASSED             [100%]
============================== 6 passed in 0.17s ==============================
```

全量测试套件也通过（12 passed）：
- config: 3 passed
- registry: 6 passed
- result: 3 passed

## 文件变更

| 文件 | 操作 | 行数 |
|------|------|------|
| `markstrip/languages/base.py` | 新增 | 58 行 |
| `markstrip/languages/registry.py` | 新增 | 56 行 |
| `tests/unit/test_registry.py` | 新增 | 72 行 |

## 提交信息

- Commit: c6025e1
- 消息: `feat: 添加 LanguagePlugin 抽象基类和 LanguageRegistry`
- 3 files changed, 186 insertions(+)

## 问题与关注点

- **终端中文显示乱码**：commit 消息在 PowerShell 终端中显示为乱码（如 `娣诲姞`），这是 PowerShell 的编码问题，与之前两个任务（b8f3e9f, f11d589）一致。Git 仓库内存储的应是正确的 UTF-8 中文，此为环境显示问题，不影响数据完整性。
- **实现完全遵循 brief**：`base.py` 和 `registry.py` 代码与任务说明完全一致，未做任何额外修改。
- 无其他功能性问题或关注点。
