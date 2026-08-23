"""
密码复杂度策略 — 统一入口
规则: 至少 8 位; 必须同时包含字母与数字。
"""

MIN_PASSWORD_LEN = 8


def validate_password(password: str) -> tuple[bool, str]:
    """校验密码复杂度。返回 (是否通过, 失败原因中文提示)。"""
    if not password:
        return False, "密码不能为空"
    if len(password) < MIN_PASSWORD_LEN:
        return False, f"密码长度至少 {MIN_PASSWORD_LEN} 位"
    has_alpha = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    if not has_alpha or not has_digit:
        return False, "密码必须同时包含字母和数字"
    return True, ""


def is_valid_password(password: str) -> bool:
    return validate_password(password)[0]
