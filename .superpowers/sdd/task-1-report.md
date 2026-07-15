# Task 1: 项目脚手架 - 报告

## 实现内容

按照任务简报创建了 markstrip 库的项目脚手架，包含以下文件：

### 配置文件
- `pyproject.toml` — 项目配置，使用 setuptools 构建，定义了包名、版本、Python >= 3.10 要求、CLI 入口点、pytest 和 ruff 配置
- `README.md` — 项目说明文件（pyproject.toml 中 `readme = "README.md"` 引用了此文件，必须创建否则安装失败）
- `.gitignore` — Git 忽略规则，排除 `__pycache__/`、`*.egg-info/`、`dist/`、`build/` 等构建产物

### 包目录
- `markstrip/__init__.py` — 包入口，包含 docstring `"""markstrip - 标记式选择性注释过滤库。"""`
- `markstrip/py.typed` — PEP 564 类型标记（空文件）
- `markstrip/core/__init__.py` — 核心模块，包含 docstring `"""核心模块。"""`
- `markstrip/languages/__init__.py` — 语言插件模块，包含 docstring `"""语言插件模块。"""`

### 测试目录
- `tests/__init__.py` — 空文件
- `tests/unit/__init__.py` — 空文件
- `tests/integration/__init__.py` — 空文件
- `tests/golden/python/.gitkeep` — 占位文件
- `tests/golden/markdown/.gitkeep` — 占位文件

## 测试与验证

### 1. 包安装 (`pip install -e .`)
- **结果**: 成功，退出码 0

### 2. 包导入验证 (`python -c "import markstrip; print(markstrip.__doc__)"`)
- **结果**: 成功
- **输出**: `markstrip - 标记式选择性注释过滤库。`

### 3. pytest 验证 (`python -m pytest --co`)
- **结果**: 成功
- **输出**: `collected 0 items` / `no tests collected in 0.03s`
- **说明**: 退出码 5 是 pytest "无测试收集"的标准退出码，符合预期

## 变更文件清单

| 文件 | 操作 |
|------|------|
| `pyproject.toml` | 新建 |
| `README.md` | 新建 |
| `.gitignore` | 新建 |
| `markstrip/__init__.py` | 新建 |
| `markstrip/py.typed` | 新建 |
| `markstrip/core/__init__.py` | 新建 |
| `markstrip/languages/__init__.py` | 新建 |
| `tests/__init__.py` | 新建 |
| `tests/unit/__init__.py` | 新建 |
| `tests/integration/__init__.py` | 新建 |
| `tests/golden/python/.gitkeep` | 新建 |
| `tests/golden/markdown/.gitkeep` | 新建 |

## Git 提交

- 提交 SHA: `b8f3e9f`
- 提交信息: `feat: 初始化项目脚手架`
- 包含 12 个文件

## 问题与说明

1. **README.md**: 任务简报未在文件列表中明确列出 README.md，但 pyproject.toml 中 `readme = "README.md"` 引用了它。setuptools 在构建时需要此文件存在，因此创建了最小化的 README.md。这是安装成功的必要条件。

2. **.gitignore**: 任务简报未要求创建 .gitignore，但首次提交时 `git add markstrip/` 意外包含了 `__pycache__/__init__.cpython-312.pyc` 构建产物。创建了 .gitignore 并通过 `git rm --cached` 和 `git commit --amend` 修复了此问题，确保仓库干净。

3. **终端中文显示**: git log 在终端中显示中文提交信息时出现乱码，但这只是终端编码显示问题，实际的 git 提交信息内容正确。
