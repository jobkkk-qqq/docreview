"""菜单-功能树配置与同步服务"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Permission


# 菜单-功能树配置
# 注意：code 必须全局唯一；type 为 "menu" 表示菜单入口，"function" 表示功能点
MENU_FUNCTION_TREE = [
    # 1. 仪表盘
    {"code": "view_dashboard", "name": "仪表盘", "type": "menu", "menu_key": "dashboard", "sort": 1},

    # 2. 文档管理
    {"code": "view_doc_list", "name": "文档管理", "type": "menu", "menu_key": "document", "sort": 2},
    {"code": "view_doc_detail", "name": "查看文档详情", "type": "function", "parent": "view_doc_list", "sort": 1},
    {"code": "upload_doc", "name": "上传文档", "type": "function", "parent": "view_doc_list", "sort": 2},
    {"code": "modify_doc", "name": "修改文档信息", "type": "function", "parent": "view_doc_list", "sort": 3},
    {"code": "delete_doc", "name": "删除文档", "type": "function", "parent": "view_doc_list", "sort": 4},
    {"code": "print_doc", "name": "预览/打印文档", "type": "function", "parent": "view_doc_list", "sort": 5},
    {"code": "download_doc", "name": "下载文档", "type": "function", "parent": "view_doc_list", "sort": 6},
    {"code": "manage_doc_permissions", "name": "管理文档权限", "type": "function", "parent": "view_doc_list", "sort": 7},

    # 3. 文档上传（独立菜单入口）
    {"code": "document_upload", "name": "文档上传", "type": "menu", "menu_key": "document_upload", "sort": 3},

    # 4. 分类管理
    {"code": "manage_categories", "name": "分类管理", "type": "menu", "menu_key": "category", "sort": 4},

    # 5. 用户管理
    {"code": "manage_users", "name": "用户管理", "type": "menu", "menu_key": "user", "sort": 5},

    # 6. 部门管理
    {"code": "manage_departments", "name": "部门管理", "type": "menu", "menu_key": "department", "sort": 6},

    # 7. 角色管理
    {"code": "assign_roles", "name": "角色管理", "type": "menu", "menu_key": "role", "sort": 7},

    # 8. 权限矩阵
    {"code": "permission_matrix", "name": "权限矩阵", "type": "menu", "menu_key": "permission_matrix", "sort": 8},
    {"code": "manage_doc_permissions", "name": "文档权限", "type": "function", "parent": "permission_matrix", "sort": 1},
    {"code": "manage_menu_permissions", "name": "菜单功能权限", "type": "function", "parent": "permission_matrix", "sort": 2},

    # 9. 操作日志
    {"code": "view_audit_logs", "name": "操作日志", "type": "menu", "menu_key": "log", "sort": 9},

    # 10. 系统配置
    {"code": "manage_system", "name": "系统配置", "type": "menu", "menu_key": "settings", "sort": 10},
]


def build_tree(flat_list: list[dict]) -> list[dict]:
    """将扁平配置转换为树形结构"""
    nodes = {}
    roots = []
    for item in flat_list:
        node = {
            "code": item["code"],
            "name": item["name"],
            "type": item["type"],
            "menu_key": item.get("menu_key"),
            "sort": item["sort"],
            "children": [],
        }
        nodes[item["code"]] = node

    for item in flat_list:
        node = nodes[item["code"]]
        parent_code = item.get("parent")
        if parent_code and parent_code in nodes:
            nodes[parent_code]["children"].append(node)
        else:
            roots.append(node)

    # 同级排序
    roots.sort(key=lambda x: x["sort"])
    for node in nodes.values():
        node["children"].sort(key=lambda x: x["sort"])

    return roots


async def sync_permissions_to_db(session: AsyncSession, tree_config: list = None) -> None:
    """将 MENU_FUNCTION_TREE 同步到数据库（幂等）"""
    if tree_config is None:
        tree_config = MENU_FUNCTION_TREE

    code_set = set()
    for node in tree_config:
        code = node["code"]
        code_set.add(code)
        result = await session.execute(select(Permission).where(Permission.code == code))
        perm = result.scalar_one_or_none()

        if perm is None:
            perm = Permission(
                code=code,
                name=node["name"],
                permission_type=node["type"],
                parent_code=node.get("parent"),
                menu_key=node.get("menu_key"),
                sort_order=node["sort"],
                is_deprecated=False,
            )
            session.add(perm)
        else:
            perm.name = node["name"]
            perm.permission_type = node["type"]
            perm.parent_code = node.get("parent")
            perm.menu_key = node.get("menu_key")
            perm.sort_order = node["sort"]
            perm.is_deprecated = False

    # 标记废弃节点
    deprecated_result = await session.execute(
        select(Permission).where(~Permission.code.in_(code_set))
    )
    for perm in deprecated_result.scalars().all():
        perm.is_deprecated = True

    await session.flush()


def get_menu_function_tree() -> list[dict]:
    """获取配置好的菜单-功能树"""
    return build_tree(MENU_FUNCTION_TREE)


def get_permission_name_map() -> dict[str, str]:
    """获取权限 code → 中文名称 的映射字典"""
    return {item["code"]: item["name"] for item in MENU_FUNCTION_TREE}


def translate_permission_codes(codes: list[str]) -> list[str]:
    """将权限 code 列表翻译为中文名称列表"""
    name_map = get_permission_name_map()
    return [name_map.get(c, c) for c in codes]
