"""EWMA 向量化性能测试"""
import time
import numpy as np
import pandas as pd
from analysis.spc.ewma import analyze


def test_ewma_performance():
    """EWMA 性能测试"""
    # 生成测试数据
    np.random.seed(42)
    n = 10000
    data = pd.Series(np.random.normal(0, 1, n))

    # 运行 EWMA 分析
    start = time.time()
    result = analyze(data, lam=0.2, L=3.0)
    elapsed = time.time() - start

    print(f"EWMA 分析 (n={n}): {elapsed*1000:.2f}ms")
    print(f"违规点数: {len(result['ewma_chart']['violations'])}")

    # 性能要求：< 50ms
    assert elapsed < 0.05, f"性能不达标: {elapsed*1000:.2f}ms > 50ms"


def test_ewma_correctness():
    """EWMA 正确性测试"""
    data = pd.Series([10.0, 11.0, 12.0, 11.0, 10.0, 9.0, 8.0, 9.0, 10.0, 11.0])
    result = analyze(data, lam=0.2, L=3.0)

    # 检查基本结构
    assert result["chart_type"] == "EWMA"
    assert result["num_points"] == 10
    assert len(result["ewma_chart"]["data"]) == 10
    assert len(result["ewma_chart"]["ucl"]) == 10
    assert len(result["ewma_chart"]["lcl"]) == 10


if __name__ == "__main__":
    test_ewma_performance()
    test_ewma_correctness()
    print("所有测试通过!")
