# LibreOffice 安装脚本
# 用于支持 Office 文件转 PDF 预览功能

$ErrorActionPreference = "Stop"

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  LibreOffice 安装脚本" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# 检查是否已安装
$libreOfficePath = "C:\Program Files\LibreOffice\program\soffice.exe"
if (Test-Path $libreOfficePath) {
    Write-Host "LibreOffice 已安装：$libreOfficePath" -ForegroundColor Green
    Write-Host "无需重复安装" -ForegroundColor Green
    exit 0
}

# 下载 LibreOffice
$downloadUrl = "https://download.documentfoundation.org/libreoffice/stable/24.8.4/win/x86_64/LibreOffice_24.8.4_Win_x86-64.msi"
$installerPath = "$env:TEMP\LibreOffice_Installer.msi"

Write-Host "正在下载 LibreOffice..." -ForegroundColor Yellow
Write-Host "下载地址：$downloadUrl" -ForegroundColor Gray

try {
    # 使用 Invoke-WebRequest 下载
    Invoke-WebRequest -Uri $downloadUrl -OutFile $installerPath -UseBasicParsing
    Write-Host "下载完成" -ForegroundColor Green
} catch {
    Write-Host "下载失败：$_" -ForegroundColor Red
    Write-Host ""
    Write-Host "请手动下载 LibreOffice：" -ForegroundColor Yellow
    Write-Host "https://www.libreoffice.org/download/download/" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "安装后重新运行此脚本" -ForegroundColor Yellow
    exit 1
}

# 安装 LibreOffice（静默安装）
Write-Host ""
Write-Host "正在安装 LibreOffice（静默模式）..." -ForegroundColor Yellow
Write-Host "这可能需要几分钟时间..." -ForegroundColor Gray

try {
    Start-Process msiexec.exe -ArgumentList "/i `"$installerPath`" /quiet /norestart" -Wait -NoNewWindow
    Write-Host "安装完成" -ForegroundColor Green
} catch {
    Write-Host "安装失败：$_" -ForegroundColor Red
    exit 1
}

# 验证安装
if (Test-Path $libreOfficePath) {
    Write-Host ""
    Write-Host "=====================================" -ForegroundColor Green
    Write-Host "  LibreOffice 安装成功！" -ForegroundColor Green
    Write-Host "=====================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "安装路径：$libreOfficePath" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "现在可以上传 Office 文件，系统会自动转换为 PDF 用于预览" -ForegroundColor Yellow
} else {
    Write-Host "安装似乎未完成，请检查：$libreOfficePath" -ForegroundColor Red
    exit 1
}

# 清理安装文件
Remove-Item $installerPath -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "按任意键退出..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
