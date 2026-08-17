# DocReview V1.0 — 构建与打包说明

## 打包为 Windows 可执行程序

### 前置条件（Windows 机器）

1. **Python 3.11+**
   - 下载：https://www.python.org/downloads/
   - 安装时勾选 `Add Python to PATH`

2. **Node.js 18+**
   - 下载：https://nodejs.org/
   - 用于构建前端（如果 dist 已存在则跳过）

### 构建步骤

#### 方式一：一键构建（推荐）

```batch
# 将本 win-build 目录复制到 Windows 机器
# 双击运行：
build.bat
```

构建完成后，`dist/DocReview.exe` 即为可执行程序。

#### 方式二：手动构建

```batch
# 1. 安装依赖
pip install -r requirements-win.txt
pip install pyinstaller

# 2. 构建前端（如果 frontend/dist 不存在）
cd frontend
npm install
npm run build
cd ..

# 3. 打包
pyinstaller --clean docreview.spec
```

### 运行方式

```batch
# 方式一：双击 dist\DocReview.exe
# 方式二：命令行运行
dist\DocReview.exe
```

启动后自动打开浏览器访问 `http://127.0.0.1:3000`（前端服务），后端 API 仍运行在 `http://127.0.0.1:9002`

### 默认管理员账号

- 用户名：`admin`
- 密  码：`admin123`

### 目录结构

```
DocReview.exe 运行时同级目录：
├── backend/
│   ├── app/          # 后端代码
│   ├── main.py       # FastAPI 入口
│   └── docreview.db  # SQLite 数据库（自动创建）
├── frontend/
│   └── dist/         # 前端构建产物
└── doc-repo/         # 文档存储目录（自动创建）
```

### 常见问题

**Q: 启动后浏览器打开空白页？**
A: 等待 3-5 秒，后端启动完成后刷新页面。
   命令行窗口会显示启动日志，看到 `Uvicorn running on http://127.0.0.1:9002` 即表示启动成功。

**Q: 端口 9002 被占用？**
A: 修改 `main_win.py` 中的 `port=9002` 为其他端口。

**Q: 杀毒软件误报？**
A: PyInstaller 打包的 exe 有时被误报。可添加信任或使用 `--console` 模式运行确认。
