# @internal 这行应被正则删除
# 普通注释，应保留
def broken(
    # 语法错误，缺少右括号
    # @internal 缩进的标记注释也应删除
    x = 1  # @internal 行内标记也应删除
# @internal 正则回退也应删除这行
    # 普通缩进注释，应保留
    y = 2
