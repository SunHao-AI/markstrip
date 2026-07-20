# markstrip

标记式选择性注释过滤库 —— 基于标记自动清理源代码中的指定注释，保留其他注释不变。

## 目录

- [项目概述](#项目概述)
- [核心特性](#核心特性)
- [安装部署](#安装部署)
- [快速开始](#快速开始)
- [标记类型详解](#标记类型详解)
- [Pragma 指令系统](#pragma-指令系统)
- [--check 模式](#check-模式)
- [stdin/stdout 管道](#stdinstdout-管道)
- [CLI 命令行使用指南](#cli-命令行使用指南)
- [Python API 使用指南](#python-api-使用指南)
- [配置参数完整说明](#配置参数完整说明)
- [Markdown 支持](#markdown-支持)
- [全量模式（full）保留规则](#全量模式full保留规则)
- [项目架构](#项目架构)
- [模块说明](#模块说明)
- [扩展开发指南](#扩展开发指南)
- [常见问题（FAQ）](#常见问题faq)
- [已知限制](#已知限制)
- [测试](#测试)
- [后续发展方向](#后续发展方向)
- [License](#license)

---

## 项目概述

在多分支代码管理场景中（如 `master` 保留完整代码和注释，`release` 分发给第三方时需隐藏核心设计注释），开发者需要在注释中添加特定标记以区分"内部注释"和"公开注释"。

**markstrip** 是一个 Python 库 + CLI 工具，专门解决这一问题：

- 在注释中写入 `@internal` 标记
- 发布时运行 markstrip，自动删除所有带标记的注释
- 普通注释原样保留，不影响文档可读性

### 典型应用场景

| 场景 | 说明 |
|------|------|
| 代码分发 | 将内部实现细节标记为 `@internal`，分发时隐藏 |
| 技术文档 | Markdown 中嵌入含内部注释的代码块，发布时自动清理 |
| CI/CD 集成 | 在构建流水线中自动清理标记注释后再部署 |
| 多版本维护 | 同一代码库维护内部版和公开版，通过标记控制注释可见性 |

---

## 核心特性

- **选择性过滤**：仅删除含 `@internal` 标记的注释，普通注释原样保留
- **行级精确删除**：行尾标记注释仅删除注释部分（`# @internal`），保留同行的代码
- **块级定界过滤**：`@internal-start` / `@internal-end` 标记可一次性过滤连续的注释区域，含定界行整体删除
- **Docstring 整体删除**：`@internal-docstring` 标记可整体删除整个 docstring
- **Docstring 逐行过滤**：docstring 内逐行 `@internal` 标记仅删除对应行
- **Markdown 支持**：解析代码块并委托对应语言插件处理，支持嵌套代码块删除和 HTML 注释过滤
- **全量模式**：`full` 模式删除所有注释（保留 shebang / TODO / 编码声明等）
- **插件架构**：内置 Python 和 Markdown 插件，支持自定义插件和 `entry_points` 自动发现
- **语法错误容错**：`tokenize` 失败时自动回退到正则匹配，不中断处理
- **零运行时依赖**：仅使用 Python 标准库
- **Pragma 指令式全量删注释**：`# markstrip: full` 文件级 / `full-start`/`full-end` 区间级指令
- **CI 守门 `--check`**：扫描 @internal 标记并输出位置到 stderr，退出码 0/1
- **stdin/stdout 管道**：`-` 占位符触发，接入 Unix 工作流

---

## 安装部署

### 环境要求

- Python >= 3.10
- 无外部依赖

### 从 PyPI 安装（推荐）

```bash
pip install markstrip
```

### 开发安装（可编辑模式）

```bash
git clone <repo-url>
cd markstrip
pip install -e .
```

安装后验证：

```bash
markstrip --help
```

---

## 快速开始

### 命令行

```bash
# 预览清理效果（不修改文件）
markstrip source.py --dry-run

# 原地清理文件
markstrip source.py

# 输出到指定文件
markstrip source.py -o cleaned.py

# 递归清理目录
markstrip src/ --recursive

# 删除所有注释（full 模式）
markstrip source.py --mode full
```

### Python API

```python
from markstrip import strip

# 清理字符串
result = strip(
    "# @internal 内部注释\nx = 1\n",
    language="python"
)
print(result.cleaned_content)  # 'x = 1\n'
print(result.removed_count)    # 1
```

---

## 标记类型详解

| 标记 | 位置 | 作用域 | 行为 |
|------|------|--------|------|
| `@internal` | 行注释 `# @internal` | 单行 | 删除该注释行，或删除行尾注释部分 |
| `@internal` | docstring 内行首 | docstring 内单行 | 整行删除该标记行 |
| `@internal-docstring` | docstring 首行 | 整个 docstring | 整体删除 docstring |
| `@internal-start` / `@internal-end` | 行注释定界对 | 块区域 | 删除两个定界行及其间的所有行（含纯注释与代码行） |
| `<!-- @internal -->` | Markdown HTML 注释 | 整个注释 | 删除含标记的 HTML 注释 |
| `# markstrip: full` | 文件任意行 | 整个文件 | 该文件所有注释全量删除，保留代码 |
| `# markstrip: full-start` | 区间起始行 | 区间内 | 区间内注释全量删除，保留代码 |
| `# markstrip: full-end` | 区间结束行 | 区间内 | 与 full-start 配对，闭区间 |

### 示例 1：行注释过滤

**输入：**

```python
# 普通注释，应保留
# @internal 这行应被删除
x = 1  # @internal 行尾标记也应删除
# 另一条普通注释
y = 2
```

**输出（selective 模式）：**

```python
# 普通注释，应保留

x = 1
# 另一条普通注释
y = 2
```

### 示例 2：Docstring 逐行过滤

**输入：**

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

**输出：**

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

### 示例 3：Docstring 整体删除

**输入：**

```python
def online_predict():
    """
    @internal-docstring
    Online 推理任务调度 - 自适应超时策略
    本模块调度任务到 native worker
    """
    timeout = 1
    return timeout
```

**输出：**

```python
def online_predict():

    timeout = 1
    return timeout
```

### 示例 4：块级定界过滤

**输入：**

```python
# @internal-start
# 这是一段被注释掉的内部实现细节
# logger = logging.getLogger("celery")
# logger.setLevel(logging.INFO)
# @internal-end
x = 1  # @internal 行尾标记
y = 2  # 普通行尾注释
# @internal-start
z = 3  # 块内代码行也会被删除
# @internal-end
w = 4
```

**输出（selective 模式）：**

```python
x = 1
y = 2  # 普通行尾注释
w = 4
```

块内所有行（含定界行、纯注释行与代码行）整体删除；块外的 `@internal` 行尾标记仍按行级规则处理。

---

## Pragma 指令系统

Pragma 指令是 markstrip 的"clean zone"机制：用一行指令让整个文件或某段代码在 selective 模式下自动转 full 模式（全量删注释保留代码），无需逐行 `@internal`。

### 语法示例

文件级（整个文件全量删注释）：

```python
# markstrip: full
import os
# 这条注释会被删除
x = 1  # 行尾注释也会被删除
```

区间级（区间内全量删注释，区间外保留 selective）：

```python
# markstrip: full-start
# 这段代码内的所有注释都会被删除
def f():
    # 包括这条
    return 1
# markstrip: full-end

# @internal 这条仍按 selective 标记处理
y = 2
```

### 与 @internal 的关系

| 维度 | `@internal` 标记 | `# markstrip:` pragma |
|------|----------------|----------------------|
| 作用 | 标记应删除的注释 | 指令该范围转 full 模式 |
| 删除范围 | 仅标记的注释 | 范围内所有注释 |
| 是否保留代码 | 是 | 是 |
| CLI 交互 | selective 模式 | selective 内嵌 full |

### CLI 交互矩阵

| 输入 | CLI mode | 行为 |
|------|----------|------|
| 文件含 `# markstrip: full` | selective | 等价 full，全量删注释 |
| 文件含 `# markstrip: full` | full | 一致（冗余） |
| 区间 `full-start/end` | selective | 区间内 full，外 selective |

### FAQ

- **pragma 是否支持嵌套**：不支持。内层 `full-start` 视为错配，输出 warning 后忽略。
- **release 文件该用 pragma 还是 @internal**：文件整体无注释 → 用 `# markstrip: full`；大部分注释保留、仅特定行删除 → 用 `@internal`。
- **HTML 注释是否支持 pragma**：不支持。pragma 仅作用于 `#` / `//` 前缀的代码注释。

---

## --check 模式

CI 守门用，扫描 `@internal` 标记并输出精确位置到 stderr，不修改文件。

### 典型 CI 用法

```bash
# 在 CI 中守门：有 @internal 残留则失败
markstrip src/ --recursive --check
if [ $? -ne 0 ]; then
    echo "Build failed: @internal markers found"
    exit 1
fi
```

### 检测范围

仅 `@internal` 体系（`# markstrip:` pragma 不算违规）：

- 行标记 `# @internal ...`
- 块定界 `@internal-start` / `-end`
- docstring 整体 `@internal-docstring` 或逐行 `@internal`
- 自定义 marker（`--marker @private`）

### 退出码

| 退出码 | 含义 |
|--------|------|
| 0 | 无标记 |
| 1 | 发现标记 |
| 2 | 参数错误/路径不存在 |

## stdin/stdout 管道

Unix 风格管道接入。

### 触发与语言检测

`path` 参数传 `-` 触发 stdin 模式。语言检测优先级：

1. `--language` 显式指定
2. 内容探测（自动遍历已注册插件）

### 输出流分离

| 输出 | 目标流 |
|------|--------|
| 清理后内容 | stdout |
| 警告 | stderr |
| 标记列表（--check） | stderr |
| 错误信息 | stderr |

---

## CLI 命令行使用指南

### 命令格式

```
markstrip <路径> [选项]
```

### 参数说明

| 参数 | 简写 | 类型 | 默认值 | 说明 |
|------|------|------|--------|------|
| `path` | — | 位置参数 | 必填 | 文件或目录路径 |
| `--mode` | — | `selective` / `full` | `selective` | 清理模式 |
| `--marker` | — | 字符串 | `@internal` | 行级标记符号 |
| `--docstring-marker` | — | 字符串 | 空（自动派生为 `{marker}-docstring`） | docstring 整体标记 |
| `--block-start-marker` | — | 字符串 | 空（自动派生为 `{marker}-start`） | 块起始定界标记 |
| `--block-end-marker` | — | 字符串 | 空（自动派生为 `{marker}-end`） | 块结束定界标记 |
| `--dry-run` | — | 布尔标志 | `False` | 预览模式，不修改文件，输出到 stdout |
| `--output` | `-o` | 路径 | — | 输出文件路径（仅单文件模式） |
| `--recursive` | `-r` | 布尔标志 | `False` | 递归处理目录 |
| `--preserve-docstrings` | — | 布尔标志 | `False` | full 模式下保留 docstring |
| `--verbose` | `-v` | 布尔标志 | `False` | 显示详细处理信息与警告 |

### 使用示例

```bash
# 预览清理结果
markstrip source.py --dry-run

# 输出到指定文件
markstrip input.py -o output.py

# 原地修改文件
markstrip source.py

# 递归处理目录
markstrip src/ --recursive

# 递归处理目录（预览 + 详情）
markstrip src/ --recursive --dry-run --verbose

# 使用 full 模式
markstrip source.py --mode full

# full 模式 + 保留 docstring
markstrip source.py --mode full --preserve-docstrings

# 自定义标记
markstrip source.py --marker @private --dry-run

# 自定义 docstring 标记
markstrip source.py --docstring-marker @private-doc --dry-run

# 自定义块定界标记（成对使用）
markstrip source.py --marker @private --block-start-marker @private-start --block-end-marker @private-end

# 处理 Markdown 文件
markstrip docs/guide.md --dry-run

# 文件含 # markstrip: full，selective 模式自动转 full
markstrip src.py --dry-run

# 区间 pragma 与 selective 共存
markstrip app/ --recursive
```

### 退出码

| 退出码 | 含义 |
|--------|------|
| `0` | 成功 |
| `1` | 错误（路径不存在 / 目录缺少 --recursive） |

### `--check` 模式

扫描文件/目录/stdin 中的 `@internal` 标记，输出详细位置到 stderr，不修改文件。退出码：0（无标记）/1（有标记）/2（参数错误）。

```bash
# 单文件检查
markstrip src.py --check

# 递归检查目录
markstrip src/ --recursive --check

# stdin 检查
cat file.py | markstrip --check -

# 自定义标记检查
markstrip src.py --check --marker @private
```

输出示例：

```
src/main.py:12:5  @internal (line)	# @internal 使用 TensorRT
src/main.py:45:1  @internal-start (block-start)
src/main.py:52:1  @internal-end (block-end)

Found 3 markers in 1 files
```

### stdin 管道（`-` 占位符）

`path` 参数传 `-` 触发 stdin 模式：

```bash
markstrip - < file.py                       # 清理后输出到 stdout
cat file.py | markstrip - --mode full       # 管道 + full
cat file.py | markstrip --check -           # 管道 + check
markstrip - -o cleaned.py < file.py         # 写入文件，stdout 空
echo '# @internal x\ny=1' | markstrip - --language python
```

语言检测优先级：`--language` 显式 > 内容探测（`plugin.detect()`）。

### 参数互斥表

| 组合 | 行为 |
|------|------|
| `--check --mode full` | exit 2（互斥） |
| `--check --output FILE` | exit 2（check 不写文件） |
| `- --recursive` | exit 2（stdin 无递归） |

---

## Python API 使用指南

### 核心函数

#### `strip()`

清理字符串内容中的标记注释。

```python
from markstrip import strip

result = strip(
    content: str,
    *,
    language: str | None = None,      # 显式指定语言
    filename: str | None = None,      # 文件名（用于扩展名检测）
    mode: str = "selective",          # "selective" | "full"
    config: StripConfig | None = None, # 清理配置
) -> StripResult
```

**StripResult 属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `cleaned_content` | `str` | 清理后的内容 |
| `removed_count` | `int` | 删除/变更的行数 |
| `detected_language` | `str` | 检测到的语言标识符 |
| `warnings` | `list[str]` | 警告信息列表 |

#### `strip_file()`

清理文件中的标记注释。

```python
from markstrip import strip_file

result = strip_file(
    path: str | Path,
    *,
    mode: str = "selective",
    config: StripConfig | None = None,
    inplace: bool = False,  # True 则原地修改文件
) -> StripResult
```

#### `strip_directory()`

批量清理目录下的文件。

```python
from markstrip import strip_directory

results = strip_directory(
    path: str | Path,
    *,
    mode: str = "selective",
    config: StripConfig | None = None,
    extensions: list[str] | None = None,  # 限制扩展名，如 [".py"]
    inplace: bool = False,
) -> list[StripResult]
```

#### `register_plugin()`

注册自定义语言插件。

```python
from markstrip import register_plugin

register_plugin(my_custom_plugin)
```

### 使用示例

```python
from markstrip import strip, strip_file, strip_directory, StripConfig

# --- 清理字符串 ---
result = strip(
    "# @internal 删除\nx = 1\n",
    language="python"
)
print(result.cleaned_content)
print(result.detected_language)  # "python"
print(result.removed_count)      # 1

# --- 通过文件名检测语言 ---
result = strip(content, filename="test.py")

# --- 清理 Markdown ---
result = strip(
    "```python\n# @internal 删除\nx = 1\n```\n",
    filename="doc.md"
)

# --- 清理文件（原地修改） ---
strip_file("source.py", inplace=True)

# --- 清理文件（不修改，仅获取结果） ---
result = strip_file("source.py")
cleaned = result.cleaned_content

# --- 批量清理目录 ---
results = strip_directory("src/", mode="selective", inplace=True)
for r in results:
    print(f"移除了 {r.removed_count} 处")

# --- 限制扩展名 ---
results = strip_directory("src/", extensions=[".py", ".md"])
```

### `MarkerLocation` 与 `markers_found`

`--check` 模式对应的 API 字段：

```python
from markstrip import strip, MarkerLocation

result = strip(
    "# @internal x\ny = 1\n",
    language="python",
    check_mode=True,
)
for m in result.markers_found:
    print(f"{m.line}:{m.col} {m.marker_text} ({m.marker_type})")
    # 输出：1:0 @internal (line)
```

`MarkerLocation` 字段：`line` / `col` / `marker_type` / `marker_text` / `content_preview`。

---

## 配置参数完整说明

### StripConfig 数据类

```python
from markstrip import StripConfig

config = StripConfig(
    line_marker="@internal",           # 行级标记符号
    docstring_marker="",               # 空→自动派生为 f"{line_marker}-docstring"
    block_start_marker="",             # 空→自动派生为 f"{line_marker}-start"
    block_end_marker="",               # 空→自动派生为 f"{line_marker}-end"
    preserve_docstrings=True,          # full 模式下是否保留 docstring
    preserve_todo=True,                # full 模式下是否保留 TODO/FIXME
    custom_markers=[],                 # 额外的自定义标记列表
    # warnings: 引擎瞬态通道，非用户配置，由插件回填后并入 StripResult.warnings
)
```

空字符串的标记字段会在运行时通过 `effective_docstring_marker()` / `effective_block_start()` / `effective_block_end()` 自动派生，无需显式指定即可与 `line_marker` 联动。

### 参数详解

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `line_marker` | `str` | `"@internal"` | 行级标记符号。含此标记的注释行或行尾注释将被删除 |
| `docstring_marker` | `str` | `""` | docstring 整体标记。空时自动派生为 `{line_marker}-docstring` |
| `block_start_marker` | `str` | `""` | 块起始定界标记。空时自动派生为 `{line_marker}-start` |
| `block_end_marker` | `str` | `""` | 块结束定界标记。空时自动派生为 `{line_marker}-end` |
| `preserve_docstrings` | `bool` | `True` | full 模式下是否保留 docstring |
| `preserve_todo` | `bool` | `True` | full 模式下是否保留 TODO/FIXME 注释 |
| `custom_markers` | `list[str]` | `[]` | 额外标记列表，与 `line_marker` 等效 |
| `warnings` | `list[str]` | `[]` | 引擎瞬态回填通道，非用户配置；插件写入后由引擎复制到 `StripResult.warnings` |

### 自定义标记示例

```python
from markstrip import strip, StripConfig

config = StripConfig(
    line_marker="@private",
    docstring_marker="@private-doc",          # 显式指定，或留空自动派生
    block_start_marker="@private-start",      # 显式指定，或留空自动派生
    block_end_marker="@private-end",
    custom_markers=["@confidential", "@secret"],
)

result = strip(content, language="python", config=config)
# 会删除所有 # @private, # @confidential, # @secret 注释
# 以及 @private-start / @private-end 包裹的块区域
```

---

## Markdown 支持

### 代码块委托

Markdown 中的围栏代码块会被解析，并委托给对应语言插件处理：

````markdown
## 文档标题

```python
# @internal 内部实现细节
# 公开注释
x = 1  # @internal 行尾标记
```

一些说明文字

```yaml
# @internal 内部配置
key: value
```
````

处理后，Python 代码块使用 `tokenize` 精确处理，YAML 代码块使用正则兜底。

### HTML 注释过滤

**selective 模式**：仅删除含 `@internal` 标记的 HTML 注释：

```markdown
<!-- @internal 内部说明 -->        ← 删除
<!-- 公开说明 -->                  ← 保留
```

**full 模式**：删除所有 HTML 注释。

### 嵌套代码块删除

代码块内部缩进的 ``` 围栏被识别为嵌套代码块，整体删除：

````markdown
```python
def process(data):
    data = preprocess(data)

    ```
    内部算法细节
    ```

    return model.predict(data)
```
````

处理后嵌套代码块整体删除，保留外层代码逻辑。

### 未知语言兜底

对于未注册语言（如 `rust`），代码块内容原样保留。以下语言有正则兜底模板：

| 语言 | 注释语法 | 示例 |
|------|----------|------|
| `yaml`, `bash`, `shell` | `#` | `# @internal key: val` |
| `javascript`, `java`, `c`, `cpp` | `//` | `// @internal console.log()` |

---

## 全量模式（full）保留规则

`--mode full` 删除所有注释，但以下内容会被保留：

| 保留项 | 示例 | 控制参数 |
|--------|------|----------|
| Shebang | `#!/usr/bin/env python` | 始终保留 |
| 编码声明 | `# -*- coding: utf-8 -*-` | 始终保留 |
| TODO/FIXME | `# TODO: fix later` | `preserve_todo`（默认 True） |
| 类型注释 | `# type: ignore` | 始终保留 |
| Docstring | `"""module doc"""` | `preserve_docstrings`（默认 True） |

---

## 项目架构

```
用户调用 strip(content, language="python")
    │
    ▼
┌─────────────────────────────────────────────┐
│              StripEngine                      │
│  主引擎：调度插件执行清理                      │
│  语言解析优先级：显式指定 > 扩展名 > 内容探测   │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│           LanguageRegistry                    │
│  插件注册表：按名称/扩展名查找插件              │
└─────────────────────────────────────────────┘
    │
    ├──► PythonPlugin  ── tokenize 词法分析 + 块定界扫描 + 行级重组
    │
    ├──► MarkdownPlugin ── 代码块委托 + HTML 注释 + 块定界兜底
    │         │
    │         └──► PythonPlugin (委托)
    │
    └──► 第三方插件 (entry_points 自动发现)
```

### 处理流程

```
源代码
  │
  ├─ Phase 1: 块定界扫描
  │   └─ scan_blocks() 识别 @internal-start / @internal-end 包裹的块范围
  │      （block_scanner.py 为块语义唯一真理源，Python 与 Markdown 兜底共用）
  │
  ├─ Phase 2: tokenize 词法分析
  │   └─ 精确识别 COMMENT / STRING token 位置
  │
  ├─ Phase 3: 注释处理
  │   ├─ selective: 仅删除含 @internal 标记的 COMMENT（块内行整体跳过）
  │   └─ full: 删除所有 COMMENT（保留 shebang/TODO 等）
  │
  ├─ Phase 4: Docstring 处理
  │   ├─ 检查 @internal-docstring → 整体删除
  │   └─ 检查 @internal 逐行 → 整行删除标记行
  │
  └─ Phase 5: 行级重组
      └─ 按行号映射，保留非注释代码，块范围行整体剔除
```

---

## 模块说明

| 模块 | 路径 | 职责 |
|------|------|------|
| 公共 API | `markstrip/__init__.py` | `strip()`, `strip_file()`, `strip_directory()`, `register_plugin()` |
| CLI | `markstrip/cli.py` | argparse 命令行入口 |
| 核心引擎 | `markstrip/core/engine.py` | `StripEngine`：插件调度、语言解析、warnings 传播 |
| 配置 | `markstrip/core/config.py` | `StripConfig` 数据类（含 `effective_*` 标记派生方法） |
| 块扫描器 | `markstrip/core/block_scanner.py` | `scan_blocks()`：块定界扫描纯函数，块语义唯一真理源 |
| 结果 | `markstrip/core/result.py` | `StripResult` 数据类 |
| 异常 | `markstrip/core/errors.py` | `MarkstripError`, `PluginNotFoundError`, `TokenizeError` |
| 插件基类 | `markstrip/languages/base.py` | `LanguagePlugin` 抽象基类 |
| 注册表 | `markstrip/languages/registry.py` | `LanguageRegistry` 插件注册与查找 |
| Python 插件 | `markstrip/languages/python_plugin.py` | `PythonPlugin`：tokenize + 块定界扫描 + 行级重组 |
| Markdown 插件 | `markstrip/languages/markdown_plugin.py` | `MarkdownPlugin`：代码块解析 + 委托 + 块定界兜底 |
| 内置注册 | `markstrip/languages/_builtin.py` | 默认插件注册 + entry_points 自动发现 |

---

## 扩展开发指南

### 方式一：代码内注册

实现 `LanguagePlugin` 抽象基类，然后调用 `register_plugin()` 注册：

```python
from markstrip import register_plugin
from markstrip.core.config import StripConfig
from markstrip.languages.base import LanguagePlugin
import re


class JavaScriptPlugin(LanguagePlugin):
    """JavaScript 语言插件"""

    @property
    def name(self) -> str:
        return "javascript"

    @property
    def file_extensions(self) -> list[str]:
        return [".js", ".jsx", ".mjs"]

    def strip_selective(self, content: str, config: StripConfig) -> str:
        # 收集所有标记
        markers = [config.line_marker] + config.custom_markers
        marker_alt = "|".join(re.escape(m) for m in markers)

        # 删除 // @internal 行注释
        line_pattern = rf"^\s*//\s*(?:{marker_alt}).*$\n?"
        content = re.sub(line_pattern, "", content, flags=re.MULTILINE)

        # 删除 /* @internal */ 块注释
        block_pattern = rf"/\*[^*]*?(?:{marker_alt}).*?\*/"
        content = re.sub(block_pattern, "", content, flags=re.DOTALL)

        return content

    def strip_full(self, content: str, config: StripConfig) -> str:
        # 删除所有 // 注释
        content = re.sub(r"^\s*//.*$\n?", "", content, flags=re.MULTILINE)
        # 删除所有 /* */ 块注释
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
        return content


# 注册插件
register_plugin(JavaScriptPlugin())
```

### 方式二：entry_points 自动发现（推荐用于第三方包）

在第三方包的 `pyproject.toml` 中注册：

```toml
[project.entry-points."markstrip.plugins"]
javascript = "my_package.js_plugin:JavaScriptPlugin"
java = "my_package.java_plugin:JavaPlugin"
```

markstrip 启动时会通过 `_builtin.py` 中的 `_discover_entry_point_plugins()` 自动加载。

### 插件开发要点

| 关注点 | 建议 |
|--------|------|
| `#` 注释语言 | Python / Ruby / YAML / Bash：正则 `^\s*#\s*@internal` 即可 |
| `//` 注释语言 | JS / Java / C++：正则 `^\s*//\s*@internal` + 块注释 `/* */` |
| 字符串安全 | 如需精确处理（避免误删字符串中的 `#`），使用该语言的词法分析器 |
| Docstring | 仅 Python 有 docstring 概念，其他语言无需实现 |
| `detect()` | 可选实现，用于内容探测（无文件名/语言指定时的回退） |

---

## 常见问题（FAQ）

### Q1：markstrip 会误删字符串中的 `#` 吗？

**A**：不会。Python 插件使用 `tokenize` 词法分析器精确识别注释，能区分注释中的 `#` 和字符串中的 `#`。例如：

```python
url = "https://example.com/path#fragment"  # 不会被误删
```

但在语法错误代码中（tokenize 失败），会回退到正则匹配，此时无法区分字符串中的 `#`。

### Q2：selective 模式和 full 模式有什么区别？

- **selective**：仅删除含 `@internal` 标记的注释，保留所有其他注释
- **full**：删除所有注释，但保留 shebang、编码声明、TODO/FIXME（可配置）、docstring（可配置）

### Q3：如何自定义标记符号？

```python
config = StripConfig(line_marker="@private")
result = strip(content, language="python", config=config)
```

或 CLI：

```bash
markstrip source.py --marker @private
```

### Q4：如何同时使用多个标记？

使用 `custom_markers` 参数：

```python
config = StripConfig(custom_markers=["@secret", "@confidential"])
result = strip(content, language="python", config=config)
```

### Q5：如何只处理特定类型的文件？

使用 `strip_directory()` 的 `extensions` 参数：

```python
results = strip_directory("src/", extensions=[".py", ".pyi"])
```

### Q6：如何在 CI/CD 中集成 markstrip？

```bash
# 在构建脚本中
pip install markstrip
markstrip src/ --recursive --verbose
# 或在 Python 中
python -c "from markstrip import strip_directory; strip_directory('src/', inplace=True)"
```

### Q7：markstrip 会修改文件编码吗？

不会。所有文件读/写均使用 UTF-8 编码。

### Q8：为什么 `# @internal` 行删除后还留有空行？

行尾标记注释（如 `x = 1  # @internal`）删除注释部分后，代码部分保留，因此该行不会变成空行。整行都是 `# @internal` 的行会被完全删除（含换行符），不留空行。

### Q9：支持哪些 Python 版本？

Python 3.10 及以上。

### Q10：如何处理 Git 仓库中的清理？

建议在构建/发布流程中自动运行 markstrip，而非直接修改仓库中的源码。也可以使用 `--dry-run` 预览效果后再决定。

### Q11：块级定界标记（`@internal-start` / `@internal-end`）支持嵌套吗？

不支持。块定界扫描采用"首个 start 到首个 end 闭区间"语义，内层 `@internal-start` 视为错配并忽略（输出警告）。如需多段过滤，请使用多对独立的 start/end。

### Q12：`--verbose` 会输出哪些警告？

块定界扫描中检测到的错配（嵌套 start、未匹配的 end、未闭合的 start）、无法识别语言等情况，都会以 `Warning: ...` 形式输出到 stderr。`--verbose` 同时显示这些警告与逐文件的处理统计。

### Q13：pragma 与 @internal 有什么区别？

pragma 指令（"该范围转 full"）与 @internal 标记（"这条注释应删除"）互补。pragma 用于整段无注释的 clean zone，@internal 用于精确标记单条注释。

### Q14：--check 检测哪些标记？

仅 `@internal` 体系（行/块/docstring 标记）。`# markstrip:` pragma 指令不算违规（是有意处理指令，非"未清理"）。块定界区间内的 collateral 代码行也不报告（不是 marker）。

### Q15：--check 与 --dry-run 有什么区别？

`--dry-run` 输出清理后的内容到 stdout（预览），不输出标记列表。`--check` 输出标记位置列表到 stderr，不输出清理内容。两者均不修改文件，可共存。

### Q16：stdin 模式如何指定语言？

用 `--language` 显式指定（如 `--language python`）；否则 markstrip 会用内容探测（`plugin.detect()`）自动判断。

---

## 已知限制

1. **语法错误时的正则回退**：当 Python 代码存在语法错误导致 `tokenize` 失败时，回退到正则匹配。正则回退**无法区分字符串中的 `#` 和注释 `#`**，可能误删字符串中含标记的内容。此为已知限制，仅在 tokenize 失败时触发。

2. **Markdown 嵌套代码块**：仅支持删除无语言标识的嵌套代码块。有语言标识的嵌套代码块不会被删除。

3. **Markdown HTML 注释**：仅支持 `<!-- -->` 格式的 HTML 注释，不支持条件注释等复杂格式。

4. **不支持的语言**：未注册插件的语言代码块在 Markdown 中会原样保留（除非有正则兜底模板）。

5. **块定界标记不支持嵌套**：`@internal-start` / `@internal-end` 采用单层闭区间语义，内层 start 会被忽略并发出警告；未闭合或无匹配的定界行也会被忽略并警告。

6. **Pragma 不支持嵌套**：`# markstrip: full-start` 采用单层闭区间语义，内层视为错配。

7. **HTML 注释不支持 pragma**：pragma 仅作用于代码注释前缀（`#`/`//`），不作用于 Markdown HTML 注释。

8. **`--check` 不报告块内 collateral 代码行**：块定界区间内被连带删除的代码/普通注释行不算 marker，不报告。

9. **stdin 不支持 `--recursive`**：stdin 是单流，无递归概念。

---

## 测试

### 运行测试

```bash
# 运行全部测试
python -m pytest tests/ -v

# 仅运行单元测试
python -m pytest tests/unit/ -v

# 仅运行 CLI 集成测试
python -m pytest tests/integration/ -v

# 运行特定测试文件
python -m pytest tests/unit/test_python_plugin.py -v
```

### 测试策略

项目采用 **Golden File 测试策略**：每个测试用例包含输入文件（`xxx.py`）和期望输出文件（`xxx.expected.py`），通过 `conftest.py` 中的 `collect_golden_cases()` 自动收集匹配，使用 pytest 参数化测试自动验证。

```
tests/
├── unit/                          # 单元测试
│   ├── test_config.py             # StripConfig 测试（含 effective_* 派生）
│   ├── test_result.py             # StripResult 测试
│   ├── test_registry.py           # LanguageRegistry 测试
│   ├── test_block_scanner.py      # 块定界扫描器测试
│   ├── test_python_plugin.py      # PythonPlugin 测试（含 Golden 测试）
│   ├── test_markdown_plugin.py    # MarkdownPlugin 测试（含 Golden 测试）
│   └── test_engine.py             # StripEngine、warnings 传播与公共 API 测试
├── integration/
│   └── test_cli.py                # CLI 集成测试（含块标记与 warnings 输出）
├── golden/
│   ├── python/                    # Python Golden 测试文件（含 block_* 系列）
│   └── markdown/                  # Markdown Golden 测试文件（含 block_in_yaml）
└── conftest.py                    # Golden 文件收集工具
```

---

## 后续发展方向

### 已实现（v1.1）

- [x] 块级定界标记（`@internal-start` / `@internal-end`），一次性过滤连续注释区域
- [x] warnings 瞬态通道与 `StripResult.warnings` 传播，CLI `--verbose` 输出警告
- [x] 标记字段自动派生（`docstring_marker` / `block_start_marker` / `block_end_marker` 留空时从 `line_marker` 派生）

### 已实现（v1.2）

- [x] Pragma 指令系统（`# markstrip: full` / `full-start` / `full-end`）
- [x] `pragma_scanner` 模块、`BlockRange.mode` 字段
- [x] Python 与 Markdown 兜底接入 pragma

### 已实现（v1.3）

- [x] `--check` 模式（CI 守门用，扫描 @internal 标记并输出位置）
- [x] stdin/stdout 管道（`-` 占位符触发）
- [x] `MarkerLocation` 与 `markers_found` 瞬态通道
- [x] `PythonPlugin.detect()` 与 `MarkdownPlugin.detect()` 内容探测
- [x] Markdown 代码块内 markers 行号翻译为 .md 绝对行号

### 短期（v0.2.x）

- [ ] 新增 JavaScript / TypeScript 插件（`tokenize` 替代方案）
- [ ] 新增 Java 插件
- [ ] 新增 C / C++ 插件
- [ ] 支持 `--config` 配置文件（JSON/YAML）
- [ ] 支持 `--ignore` 忽略特定文件/目录

### 中期（v0.3.x）

- [ ] 新增 Rust 插件
- [ ] 新增 Go 插件
- [ ] 支持行内块注释标记（如 `/* @internal */` 在 JS/Java 中）

### 长期（v1.0）

- [ ] tree-sitter 集成（替代纯正则兜底，提供跨语言精确 AST 解析）
- [ ] 增量模式（仅处理变更文件）
- [ ] VS Code 扩展
- [ ] pre-commit hook 集成
- [ ] 性能优化（大文件并行处理）

### 贡献指南

欢迎贡献新语言插件。请参考 [扩展开发指南](#扩展开发指南) 和现有的 `PythonPlugin` / `MarkdownPlugin` 实现。提交 PR 时请确保：

1. 新增语言插件实现 `LanguagePlugin` 接口
2. 包含对应的 Golden 测试文件
3. 所有现有测试继续通过

---

## License

MIT