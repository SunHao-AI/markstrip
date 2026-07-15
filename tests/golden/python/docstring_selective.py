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
