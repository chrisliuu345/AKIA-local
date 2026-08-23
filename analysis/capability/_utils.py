"""过程能力分析共享工具函数"""
from config.settings import CAPABILITY_GRADES


def get_capability_grade(cpk: float) -> str:
    """
    根据 Cpk/Ppk 值返回能力等级
    
    Args:
        cpk: 能力指数值
        
    Returns:
        格式化的等级字符串，如 "A+ (特优)"
    """
    for grade, (low, high, desc) in CAPABILITY_GRADES.items():
        if low <= cpk < high:
            return f"{grade} ({desc})"
    return "D (差)"
