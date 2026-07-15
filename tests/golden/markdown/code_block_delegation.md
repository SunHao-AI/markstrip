# 文档标题

```python
# @internal 这行应删除
# 普通注释保留
x = 1  # @internal 行尾标记删除
```

一些文字

```python
def func():
    """docstring"""
    # @internal 函数内注释删除
    return 1
```
