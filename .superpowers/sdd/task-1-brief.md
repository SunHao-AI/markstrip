### Task 1: 项目脚手架

**Files:**
- Create: `pyproject.toml`
- Create: `markstrip/__init__.py`
- Create: `markstrip/py.typed`
- Create: `markstrip/core/__init__.py`
- Create: `markstrip/languages/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/integration/__init__.py`
- Create: `tests/golden/python/.gitkeep`
- Create: `tests/golden/markdown/.gitkeep`

**Interfaces:**
- Produces: 可安装的 Python 包骨架，`pip install -e .` 可用

- [ ] **Step 1: 创建 pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.backends._legacy:_backend"
[project]
name = "markstrip"
version = "0.1.0"
description = "标记式选择性注释过滤库"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [{name = "markstrip contributors"}]
classifiers = [
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Libraries",
    "Topic :: Utilities",
]

[project.scripts]
markstrip = "markstrip.cli:main"

[project.entry-points."markstrip.plugins"]

[tool.setuptools.packages.find]
include = ["markstrip*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]

[tool.ruff]
line-length = 100
target-version = "py310"
```

- [ ] **Step 2: 创建包目录和 __init__.py 文件**

创建以下空 `__init__.py` 文件（每个只包含一行注释）：

`markstrip/__init__.py`:
```python
"""markstrip - 标记式选择性注释过滤库。"""
```

`markstrip/core/__init__.py`:
```python
"""核心模块。"""
```

`markstrip/languages/__init__.py`:
```python
"""语言插件模块。"""
```

`tests/__init__.py`、`tests/unit/__init__.py`、`tests/integration/__init__.py`:
```python
```

（空文件即可）

`markstrip/py.typed`:
```
```
（空文件，标记 PEP 564 类型支持）

- [ ] **Step 3: 安装包并验证**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; pip install -e .`
Expected: 成功安装，无错误

Run: `python -c "import markstrip; print(markstrip.__doc__)"`
Expected: 输出 `标记式选择性注释过滤库。`

- [ ] **Step 4: 验证 pytest 可运行**

Run: `cd d:\WorkPlace\Pycharm\markstrip ; python -m pytest --co`
Expected: `no tests ran` 或 `collected 0 items`（无错误）

- [ ] **Step 5: 提交**

```bash
cd d:\WorkPlace\Pycharm\markstrip
git init
git add pyproject.toml markstrip/ tests/
git commit -m "feat: 初始化项目脚手架"
```
