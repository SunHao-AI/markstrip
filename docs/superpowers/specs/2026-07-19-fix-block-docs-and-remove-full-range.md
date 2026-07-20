# 设计文档：修正 @internal 块文档 + 废弃 full-start/full-end

## 动机

### 问题 1：README 中 `@internal-start`/`@internal-end` 描述错误

当前 README.md 第 143 行描述为：

> 删除两个定界行及其间的所有行（含纯注释与代码行）

但实际代码行为是：**仅删除注释**（纯注释整行删除，行尾注释仅删注释片段），**代码行保留**。参见 golden test `block_with_code.py`：

```python
# 输入
# @internal-start
x = 1  # @internal 行尾注释
y = 2  # 普通行尾注释
# 纯注释行应整行删除
# @internal-end
z = 3

# 输出
x = 1
y = 2
z = 3
```

结论：README 描述错误，需修正。

### 问题 2：`# markstrip: full-start` / `full-end` 与 `@internal-start`/`@internal-end` 功能重叠

两套区间定界符的语义几乎一致（区间内全量删注释，保留代码），仅 `full-start`/`full-end` 额外处理区间内 docstring 删除。用户认为这种重叠设计是冗余的，应当废弃 `full-start`/`full-end`，保留 `# markstrip: full`（文件级全量删除）不变。

## 设计决策

### 决策 1：仅修正 README，不改 `@internal-start`/`@internal-end` 代码行为

`@internal-start`/`@internal-end` 的代码行为（块内全量删注释，保留代码行）保持不变。仅修正 README 中的错误描述。

### 决策 2：废弃 `# markstrip: full-start` / `full-end`

直接废弃删除，不从代码中保留 deprecated 标记。保留 `# markstrip: full`（文件级全量删除）不变。

理由：
- v1.2 刚发布不久，`full-start`/`full-end` 的实际使用量几乎为零
- `@internal-start`/`@internal-end` 已覆盖区间内删注释的需求
- 文件级 `# markstrip: full` 保留，覆盖全量场景

## 变更清单

### 源代码

| 文件 | 变更 |
|------|------|
| `markstrip/core/pragma_scanner.py` | 移除 `scan_full_ranges()` 函数（约 40 行）及 `BlockRange`/`BlockScanResult` 导入 |
| `markstrip/languages/python_plugin.py` | 移除 `scan_full_ranges` 导入；移除 `strip_selective` 中 pragma 区间扫描逻辑（`pragma_scan`、`_in_pragma_range` 及 token 循环中 `in_pragma` 分支） |
| `markstrip/languages/markdown_plugin.py` | 移除 `scan_full_ranges` 导入；移除 `_fallback_strip` 中 pragma 区间扫描逻辑（`pragma_scan`、`pragma_ranges`、`_in_pragma_range`） |

### 测试

| 文件 | 变更 |
|------|------|
| `tests/unit/test_pragma_scanner.py` | 移除 `scan_full_ranges` 相关测试用例（约 70 行，`test_single_range` 至 `test_no_pragma`） |
| `tests/unit/test_python_plugin.py` | 移除 pragma 区间相关测试（如有） |
| `tests/golden/python/pragma_range.py` + `.expected.py` | 删除 |
| `tests/golden/python/pragma_range_docstring.py` + `.expected.py` | 删除 |
| `tests/golden/python/pragma_nested.py` + `.expected.py` | 删除 |
| `tests/golden/python/pragma_mismatched_end.py` + `.expected.py` | 删除 |
| `tests/golden/python/pragma_with_selective.py` + `.expected.py` | 删除 |
| `tests/golden/markdown/pragma_in_yaml.md` + `.expected.md` | 删除 |

### 文档

| 文件 | 变更 |
|------|------|
| `README.md` | 修正 `@internal-start`/`@internal-end` 描述为"删除两个定界行及其间的所有注释，保留代码行"；移除 `full-start`/`full-end` 行（标记类型表 + 核心特性 + 示例 + 交互表 + FAQ/已知限制相关内容）；更新 v1.2 已实现清单移除 `full-start`/`full-end` |
| `docs/markstrip-design.md` | 移除 `full-start`/`full-end` 相关章节（标记类型表 + 语义说明 + 测试用例表 + 示例表）；更新 v1.2 更新记录移除 `full-start`/`full-end`；修正 `@internal-start`/`@internal-end` 描述 |

### 不受影响

- `# markstrip: full`（文件级 pragma）**完全保留**，代码与文档均不变
- `scan_file_pragma()` 函数**保留**
- `@internal-start`/`@internal-end` 代码行为**不变**（仅文档修正）

## 测试策略

- 移除 `full-start`/`full-end` 相关测试后，全量回归测试应全部通过
- `# markstrip: full` 文件级 pragma 测试全部保留
- `@internal-start`/`@internal-end` 块测试全部保留
- 无新增测试需求（纯删除 + 文档修正）

## 风险

- **Breaking change**：`# markstrip: full-start`/`full-end` 被移除，但 v1.2 刚发布，影响面极小
- 无 API 签名变更，无数据迁移需求