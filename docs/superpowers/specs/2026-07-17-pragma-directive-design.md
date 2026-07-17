# Pragma 指令式注释过滤设计

> **日期**: 2026-07-17
> **状态**: 已批准(待实现)
> **作者**: Trae AI
> **关联**: markstrip v1.1 块级定界标记后续演进

## 背景与动机

markstrip v1.1 已具备 `@internal` 行标记、`@internal-docstring` docstring 整体标记、`@internal-start`/`@internal-end` 块定界标记(selective 模式),以及 CLI `--mode full` 全量删除(full 模式)。

实际使用中存在两类痛点:

1. **整文件注释清理需逐行加标记**:某文件希望全量删除所有 `#` 注释(保留代码),但不想逐行加 `# @internal`,也不想在 CLI 单独传 `--mode full`(影响同批次其他文件)。
2. **散布注释的区间批量清理**:某段代码中 `#` 注释散布在有效代码行之间(非连续),希望声明一个区间一次性删除这些注释,但**保留区间内的有效代码行**。现有 `@internal-start/end` 会删除区间内一切内容(含代码),不满足需求。

### 需求确认(经澄清)

- **核心诉求**:声明一次,批量删除范围内的所有注释,**保留有效代码**
- **"跨行注释"含义**:散布在代码行之间的 `#` 行注释(与代码交错),非三引号字符串
- **动机**:简化标记,避免逐行加 `# @internal`
- 两个需求本质统一:**"full 模式删除逻辑(只删注释保留代码),但作用域可控(整文件/区间),且通过文件内声明触发"**

## 设计方案:Pragma 指令系统

引入独立的 `# markstrip:` pragma 命名空间,与 `@internal` 标记体系分离。

- `@internal` 体系 = **selective**(标记驱动,逐行/逐块选择性删除)
- `markstrip:` pragma = **full**(全量删注释,作用域可控)

两者独立、可共存。

## 1. Pragma 语法与识别规则

### 指令格式

```
# markstrip: <directive>
```

固定前缀 `markstrip:`(不可配置,独立于 `@internal` 标记体系),后接指令名:

| 指令 | 作用域 | 行为 |
|------|--------|------|
| `# markstrip: full` | 整文件 | 全量删注释,保留代码(等同 full 模式) |
| `# markstrip: full-start` | 区间起点 | 标记一个"全量删注释"区间开始 |
| `# markstrip: full-end` | 区间终点 | 标记区间结束 |

### 识别规则

- **语言前缀自适应**:Python 用 `#`、JS/Java 用 `//`、YAML/Bash 用 `#`。pragma 复用各语言的注释前缀,由插件传入 `comment_prefix` 给扫描器
- **大小写敏感**:`markstrip:` 全小写
- **空白容错**:`#markstrip:full`、`#  markstrip :  full` 均识别(前缀后、冒号两侧空格可选,`\s*` 容错)
- **行尾可附说明**:`# markstrip: full  ← 本文件全量清理` 可识别(指令后空白+文字视为注释,忽略)
- **文件级 pragma 位置**:惯例放文件头,但技术上任意位置均生效(扫描全文);区间级 `full-start`/`full-end` 在出现位置生效
- **pragma 正则**:`^\s*{prefix}\s*markstrip:\s*{directive}(?:\s|$)`(冒号两侧 `\s*` 容错,与 `@internal` 的 `_build_delimiter_regex` 结构相似但独立)

### 与现有标记的关系

- `@internal` 体系 = selective(标记驱动,逐行/逐块)
- `markstrip:` pragma = full(全量删注释,作用域可控)
- 两者独立、可共存:文件内既有 `# markstrip: full-start/end` 区间,又有区间外 `# @internal` 行标记,各自按规则处理

## 2. 文件级 pragma 行为

### 触发与作用

`# markstrip: full` 出现在文件任意位置 → 该文件整文件走 **full 模式注释删除**:

- 删除所有 `#` 行注释
- 删除所有 docstring(`"""..."""`),除非 `preserve_docstrings=True`
- 保留 shebang(`#!/usr/bin/env python`)、coding 声明(`# -*- coding: utf-8 -*-`)
- 保留 TODO/FIXME(除非 `preserve_todo=False`)
- **保留所有有效代码行**
- pragma 行本身被删除(它也是注释)

### CLI 交互矩阵

| CLI 模式 | 文件有 pragma | 结果 |
|----------|--------------|------|
| `selective` | 有 | **该文件走 full**(pragma 覆盖 CLI 默认) |
| `selective` | 无 | selective(现行行为) |
| `full` | 有 | full(pragma 冗余,无副作用) |
| `full` | 无 | full(CLI 驱动) |

**核心价值**:一条 `markstrip src/ --recursive` 命令即可处理混合目录——有 pragma 的文件全量删注释,无 pragma 的文件按 `@internal` 选择性过滤。

## 3. 区间级 pragma 行为

### 触发与作用

`# markstrip: full-start` 与 `# markstrip: full-end` 配对,定义一个"全量删注释"区间:

```python
x = 1                          # 区间外,selective 正常
# markstrip: full-start
# 注释 A                       ← 删除(注释)
y = 2                          ← 保留(代码)
# 注释 B                       ← 删除(注释)
def foo():
    """docstring"""           ← 删除(docstring,除非 preserve_docstrings)
# markstrip: full-end
z = 3  # @internal 行尾标记     # 区间外,@internal 正常生效
```

### 与 `@internal-start/end` 的关键区别

| 维度 | `@internal-start/end` | `# markstrip: full-start/end` |
|------|----------------------|-------------------------------|
| 删除对象 | **一切**(注释+代码+docstring) | **仅注释**(保留代码) |
| 语义 | selective(块整体剔除) | full(全量删注释,作用域化) |
| 标记体系 | `@internal` 族 | `markstrip:` pragma 族 |
| BlockRange.mode | `"all"` | `"comments"` |

### 块语义(复用 block_scanner 模式)

- 首个 `full-start` 到首个 `full-end` = 一个区间(含两端定界行)
- **不支持嵌套**:内层 `full-start` 视为错配,警告并忽略
- 孤立 `full-end`(无 start)→ 警告并忽略
- 未闭合 `full-start`(至 EOF)→ 警告并忽略
- 区间内含 `# @internal` 标记 → 无额外效果(注释已被全量删除)

### 文件级与区间级共存

- 文件有 `# markstrip: full`(文件级)时,区间级 `full-start/end` **冗余**——整文件已 full,发出警告"文件级 full 已生效,区间标记冗余"并忽略区间标记
- 文件无文件级 pragma 时,区间级正常生效

## 4. 架构集成

### 新增模块:`core/pragma_scanner.py`

纯函数模块,与 `block_scanner.py` 平级,接收 `comment_prefix` 参数:

```python
def scan_file_pragma(lines: list[str], comment_prefix: str) -> bool:
    """检测是否存在 # markstrip: full(文件级)。
    扫描全部行,任意位置出现即返回 True。
    """

def scan_full_ranges(
    lines: list[str], comment_prefix: str
) -> BlockScanResult:
    """扫描 # markstrip: full-start / full-end 区间。
    返回 BlockScanResult,ranges 中 BlockRange.mode = 'comments'。
    块语义与 scan_blocks 一致(首 start 到首 end 闭区间、不支持嵌套、错配警告)。
    """
```

- pragma 正则更宽松(冒号两侧 `\s*` 容错):`^\s*{prefix}\s*markstrip:\s*{directive}(?:\s|$)`
- `scan_full_ranges` 复用 block_scanner 的块语义逻辑(首 start 到首 end 闭区间、不支持嵌套、错配警告),但产出的 `BlockRange.mode = "comments"`
- 不直接复用 `scan_blocks` 函数(pragma 语法含冒号,正则结构不同),但逻辑结构相似

### BlockRange 扩展

```python
@dataclass
class BlockRange:
    start_line: int
    end_line: int
    mode: str = "all"   # "all"=删全部(@internal-start/end), "comments"=只删注释(markstrip pragma)
```

向后兼容:现有 `@internal-start/end` 区间默认 `mode="all"`,行为不变。现有 `scan_blocks` 产出的 range 不设置 mode(取默认 "all")。

### 插件处理流程(Python 插件为例)

```
strip_selective(content, config):
  1. scan_file_pragma(lines, "#") → True?
       └─ 是:委托 strip_full(content, config)  ← 文件级 pragma,直接切 full
  2. scan_blocks(...)         → @internal ranges        (mode="all")
  3. scan_full_ranges(...)    → markstrip pragma ranges  (mode="comments")
  4. tokenize 词法分析
  5. 遍历 COMMENT token:
       ├─ 在 mode="all" 区间      → 删除(块整体剔除)
       ├─ 在 mode="comments" 区间 → 删除(full 逻辑,只删注释)
       ├─ 含 @internal 标记        → 删除(selective 逻辑)
       └─ 否则                     → 保留
  6. docstring 处理:
       ├─ 在 mode="comments" 区间 → 删除(除非 preserve_docstrings)
       ├─ @internal-docstring     → 整体删除
       └─ @internal 逐行           → 整行删除
  7. 行级重组(剔除被删行,含 pragma 定界行)
```

`_fallback_regex_selective`(tokenize 失败回退)同步接入:scan_file_pragma 检测 → 委托 `_fallback_regex_full`;scan_full_ranges 区间内行注释按 full 逻辑删除、代码保留。

### Markdown 插件集成

`_fallback_strip`(兜底语言如 yaml/bash)同步接入:
- `scan_file_pragma` 检测 → 走全量删除
- `scan_full_ranges` 区间内 `#` 注释按 full 逻辑删除、代码保留

Markdown 代码块内的 pragma 由委托的 Python/兜底插件处理,Markdown 自身的 HTML 注释 pragma(如 `<!-- markstrip: full -->`)本期不支持(YAGNI)。

### 各组件职责

| 组件 | 变更 |
|------|------|
| `core/pragma_scanner.py` | **新增**:pragma 扫描纯函数(scan_file_pragma、scan_full_ranges) |
| `core/block_scanner.py` | `BlockRange` 加 `mode` 字段(默认 "all",向后兼容) |
| `core/engine.py` | **无变更**:pragma 逻辑在插件层,引擎不感知 |
| `languages/python_plugin.py` | `strip_selective` 加 pragma 检测 + 区间处理;`_fallback_regex_selective` 同步 |
| `languages/markdown_plugin.py` | `_fallback_strip` 加 pragma 检测 + 区间处理 |
| `core/config.py` | **无变更**:pragma 固定语法,不进配置 |
| `cli.py` | **无变更**:pragma 纯文件内容驱动 |

### 设计要点

- **pragma 逻辑在插件层**:插件知道自己的 `comment_prefix`,引擎无需感知 pragma
- **engine 零变更**:保持引擎简洁,pragma 是"文件内容 → 插件行为"的映射,不涉及引擎调度
- **BlockRange.mode 复用**:不新建数据结构,统一区间处理逻辑

## 5. 错误处理与警告

### 错配处理(复用 block_scanner 模式)

| 场景 | 行为 | 警告 |
|------|------|------|
| `full-end` 无匹配 `full-start` | 忽略该行 | `孤立 markstrip: full-end, 已忽略` |
| `full-start` 无匹配至 EOF | 忽略该块 | `未闭合 markstrip: full-start, 已忽略` |
| 嵌套 `full-start`(区间内再出现) | 内层忽略 | `嵌套 markstrip: full-start, 已忽略` |
| 文件级 `full` + 区间标记共存 | 文件级生效,区间冗余 | `文件级 full 已生效, 区间标记冗余` |
| 拼写错误(`# markstrip: ful`) | 不识别为 pragma | 无警告(视为普通注释) |

### 警告传播

复用现有 warnings 链路:`pragma_scanner` → `BlockScanResult.warnings` → 插件 `config.warnings.extend(...)` → 引擎 `list(config.warnings)` → `StripResult.warnings` → CLI `--verbose` 输出。**无新机制**。

## 6. 测试策略

### 单元测试(`tests/unit/test_pragma_scanner.py`)

- `scan_file_pragma`:有/无 pragma、不同空白写法(`#markstrip:full`、`#  markstrip :  full`)、注释后附文字、大小写敏感(大写不识别)
- `scan_full_ranges`:单区间、多区间、孤立 end、未闭合 start、嵌套、自定义空白
- `BlockRange.mode` 字段:pragma 区间 mode="comments"、@internal 区间 mode="all"(回归)

### 黄金测试(`tests/golden/python/`)

| 用例 | 覆盖点 |
|------|--------|
| `pragma_full.py` | 文件级 pragma,全量删注释保留代码 |
| `pragma_range.py` | 区间级,散布 `#` 注释删除、代码保留 |
| `pragma_range_docstring.py` | 区间内 docstring 删除(验证 mode="comments" 对 docstring 生效) |
| `pragma_mismatched_end.py` | 孤立 end → 忽略 + 警告 |
| `pragma_nested.py` | 嵌套 start → 忽略 + 警告 |
| `pragma_with_selective.py` | 区间外 `@internal` 正常生效,区间内冗余无副作用 |

### CLI 集成测试(`tests/integration/test_cli.py`)

- 文件有 pragma + CLI selective → 输出为 full 效果
- 文件有 pragma + CLI full → 一致(full 冗余无副作用)
- `--verbose` 输出 pragma 警告

### 回归保护

- 现有 76 个测试全部不受影响(`BlockRange.mode` 默认 "all",行为不变)
- 全量回归作为合并门槛

## 范围边界(YAGNI)

本期**不实现**:

- pragma 前缀可配置(固定 `markstrip:`,不支持自定义)
- `--no-pragma` 禁用开关(pragma 默认启用,无关闭选项)
- Markdown HTML 注释 pragma(`<!-- markstrip: full -->`)
- pragma 嵌套支持(明确不支持,内层忽略)
- 区间级行号声明(如 `# markstrip: full lines 10-20`,本期用内容标记式 full-start/end)

## 更新记录

| 日期 | 版本 | 更新内容 | 作者 |
|------|------|----------|------|
| 2026-07-17 | v1.0 | 初始设计:pragma 指令系统(full / full-start / full-end) | Trae AI |
