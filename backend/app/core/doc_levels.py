"""
文档级别常量（三级分类）

三级分类：文档级别，共 5 级，为内置固定级别，不允许增删。
排序即显示顺序：索引 0 为最高级。
"""
DOC_LEVELS = ["Ⅰ级文件", "Ⅱ级文件", "Ⅲ级文件", "Ⅳ级文件", "无级别"]

# 默认文档级别（新增文档未指定时使用）
DEFAULT_DOC_LEVEL = DOC_LEVELS[-1]


def is_valid_doc_level(value: str | None) -> bool:
    """判断文档级别是否为合法取值（None/空视为合法，表示未指定）"""
    if not value:
        return True
    return value in DOC_LEVELS