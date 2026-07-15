## 核心算法

```python
def process_data(data):
    """数据处理"""
    clean_data = preprocess(data)

    ```
    核心算法细节：
    1. 使用TensorRT加速
    2. batch_size=4最优
    ```

    result = model.predict(clean_data)
    return result
```
