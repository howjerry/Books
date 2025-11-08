"""
範例：計算器工具函數

這是一個簡單的範例程式碼，用於展示測試生成系統。
"""


def calculate_discount(price: float, discount_percent: float) -> float:
    """
    計算折扣後的價格

    Args:
        price: 原始價格
        discount_percent: 折扣百分比（0-100）

    Returns:
        折扣後的價格

    Raises:
        ValueError: 如果價格為負或折扣百分比無效
    """
    if price < 0:
        raise ValueError("價格不能為負數")

    if not 0 <= discount_percent <= 100:
        raise ValueError("折扣百分比必須在 0-100 之間")

    discount_amount = price * (discount_percent / 100)
    return price - discount_amount


def calculate_tax(amount: float, tax_rate: float = 0.05) -> float:
    """
    計算稅金

    Args:
        amount: 金額
        tax_rate: 稅率（預設 5%）

    Returns:
        稅金金額
    """
    if amount < 0:
        raise ValueError("金額不能為負數")

    return amount * tax_rate


def calculate_total(items: list, discount: float = 0.0) -> float:
    """
    計算商品總價（含折扣）

    Args:
        items: 商品價格列表
        discount: 折扣百分比（0-100）

    Returns:
        總價
    """
    if not items:
        return 0.0

    subtotal = sum(items)
    return calculate_discount(subtotal, discount)
