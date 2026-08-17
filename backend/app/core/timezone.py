"""
时区工具

提供北京时间（UTC+8）的当前时间获取函数，用于统一系统所有时间戳。
"""
from datetime import datetime, timezone, timedelta

BEIJING_TZ = timezone(timedelta(hours=8))


def beijing_now() -> datetime:
    """返回当前北京时间（UTC+8），不带微秒"""
    return datetime.now(BEIJING_TZ).replace(microsecond=0)