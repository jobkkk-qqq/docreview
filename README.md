# DocReview — 数字档案管理系统

一个面向企业/事业单位的文档档案管理平台，提供文档在线预览、权限管理、分类归档、审计追溯等能力。前端采用 Vue 3 + Element Plus，后端采用 FastAPI + SQLAlchemy + SQLite，轻量、可离线部署，支持 Windows 一键打包为桌面服务。

> 品牌名以 `XXX` 作为占位符，生产部署后可通过「系统设置」配置实际的单位名称，无需修改源码。

---

## 功能特性

- **文档管理**
  - 文档上传（批量）、下载、编辑、删除（回收站，管理员可恢复）
  - 支持文件类型标签展示（DOCX / PDF / XLSX / 图片…）
  - 在线预览：Office（Word / Excel / PPT）自动转换为 PDF 预览，PDF / TXT / 图片直接预览
  - 非公开文档预览时自动添加「用户名 + 日期」水印
- **三级分类归档**
  - 一级：文档分类
  - 二级：部门
  - 三级：文档级别（Ⅰ级文件 ~ 四级 + 无级别）
- **权限体系**
  - 基于角色的权限矩阵：菜单功能权限 + 文档级 / 分类级权限
  - 内置系统角色（系统管理员 / 文档管理员 / 部门管理员 / 普通用户）
  - 业务角色与业务范围（品质 / 行政 / 人事 / 财务 / 法务 / 采购 / 生产）自动映射
  - 多角色支持，新文档默认继承所属分类的权限
  - 批量授权（按部门 / 关键词添加用户）
- **审计与安全**
  - 全量操作审计日志，支持关键词检索与 JSON 导出
  - 密码统一加盐哈希，登录异常容错
- **运维能力**
  - 旧数据库自动迁移（schema 版本号机制），防止数据丢失
  - doc-repo 启动扫描关联已有 PDF，治理「孤儿 / 悬空文件」
  - 局域网访问，端口可通过环境变量调整

---

## 技术架构

```
           客户端浏览器
                │
      ┌─────────┴──────────┐
      │  前端服务  :3000   │  → 静态资源 + SPA 路由 + /api 反向代理
      └─────────┬──────────┘
                │ /api
      ┌─────────┴──────────┐
      │  后端  FastAPI      │  绑定 0.0.0.0:9002
      │  SQLAlchemy + SQLite│
      └────────────────────┘
```

- **前端**：Vue 3 + Element Plus + Vue Router + Pinia + Axios（Vite 构建）
- **后端**：FastAPI + SQLAlchemy + aiosqlite + PyJWT
- **桌面壳**：`main_win.py` 一键启动后端 + 前端，并由 `tray_app.py` 系统托盘管理
- **预览转换**：LibreOffice 无头模式将 Office 转 PDF（串行化、超时清理）
- **数据存储**：SQLite（`docreview.db`），文件存储于 `doc-repo/`

### 端口说明

| 服务 | 地址 | 说明 |
| --- | --- | --- |
| 前端服务 | `http://0.0.0.0:3000` | 静态页面 + `/api` 代理 |
| 后端 API | `http://0.0.0.0:9002` | FastAPI，支持局域网访问 |

端口可通过环境变量 `FRONTEND_PORT`、`BACKEND_URL` 调整。

---

## 目录结构

```
├── backend/                    # 后端
│   ├── app/
│   │   ├── api/                # 路由（文档/分类/用户/角色/权限/审计/系统…）
│   │   ├── core/               # 配置、安全、权限、迁移、时区
│   │   ├── models/             # SQLAlchemy 模型
│   │   ├── schemas/            # Pydantic 结构
│   │   ├── services/           # 业务服务层
│   │   └── utils/
│   ├── main.py                 # FastAPI 入口
│   └── serve_frontend_3000.py  # 生产前端静态服务 + API 代理
├── frontend/                   # 前端（Vue 3）
│   ├── src/
│   │   ├── views/              # 页面（文档、权限矩阵、用户、角色…）
│   │   ├── components/         # 组件
│   │   ├── api/                # 接口封装
│   │   └── utils/              # 工具（品牌名、格式化、下载…）
│   └── vite.config.js
├── main_win.py                 # Windows 桌面启动入口
├── tray_app.py                 # 系统托盘
├── docreview.spec              # PyInstaller 打包配置
├── build.bat / build-frontend.ps1
├── requirements-win.txt
└── README.md
```

---

## 本地开发

```bash
# 后端
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 9002

# 前端
cd frontend
npm install
npm run dev        # http://localhost:3000（含 /api 代理）
```

默认管理员账号：`admin` / `admin123`

> 首次登录后请在「系统设置」中修改默认密码、配置单位品牌名。

---

## Windows 生产构建与部署

### 一键构建

```batch
build.bat
```

构建完成后，`dist/` 下生成 `DocReview.exe` 及配套目录。

### 手动构建

```batch
pip install -r requirements-win.txt
pip install pyinstaller

# 构建前端（frontend/dist 不存在时）
cd frontend
npm install
npm run build
cd ..

# 打包
pyinstaller --clean docreview.spec
```

### 部署步骤（服务器）

1. 将构建产物 `DocReview-Windows/` 分发到服务器任意目录。
2. 运行 `DocReview.exe`（或一键脚本 `启动系统.bat`），自动启动前后端服务。
3. 放行防火墙端口（脚本 `开启防火墙端口.bat`，开放 TCP 3000）。
4. 客户端通过 `http://<服务器IP>:3000` 访问。
5. 已有文档放入 `doc-repo/`，首次启动会自动扫描并关联 PDF、迁移旧数据库。

### 常见问题

**Q：浏览器打开空白页？**
A：等待 3–5 秒后端就绪后刷新，或 Ctrl + F5 强制刷新清除缓存。

**Q：杀毒软件误报？**
A：PyInstaller 打包的 exe 偶有误报，可添加信任。

**Q：端口被占用？**
A：通过环境变量 `FRONTEND_PORT`、`BACKEND_URL` 调整端口。

---

## License

内部 / 私有使用，授权范围内分发。