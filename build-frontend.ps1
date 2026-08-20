<#
.SYNOPSIS
  前端构建脚本 — 在 C 盘执行 npm install + vite build，将产物复制回 D 盘
  原因：D 盘无法正确安装 @rolldown 等原生二进制包的 node_modules
#>

$SrcDir = "D:\python\docreview\frontend"
$DstDir = "C:\Users\Liang\temp_frontend"
$Project = "D:\python\docreview"

# 本环境的 PATH 可能不含 System32，使用完整路径调用系统工具
$ROBO = "$env:SystemRoot\System32\robocopy.exe"

Write-Host "=== 构建前端 ===" -ForegroundColor Cyan

# Step 1: 同步源码到 C 盘（排除 node_modules、dist；/XJ 跳过损坏的 junction/断链）
Write-Host "[1/4] 同步源码到 C 盘..." -ForegroundColor Yellow
if (Test-Path $DstDir) { Remove-Item $DstDir -Recurse -Force }
New-Item $DstDir -ItemType Directory -Force | Out-Null

& $ROBO $SrcDir $DstDir /E /XD node_modules dist /XJ /NFL /NDL /NJH /NJS /NC /NS /NP
if ($LASTEXITCODE -ge 8) {
    Write-Host "   robocopy 同步失败（退出码 $LASTEXITCODE）！" -ForegroundColor Red
    exit 1
}
Write-Host "   同步完成" -ForegroundColor Green

# Step 2: npm install
Write-Host "[2/4] 安装 npm 依赖..." -ForegroundColor Yellow
Set-Location $DstDir
npm install
if (-not $?) { Write-Host "   npm install 失败！" -ForegroundColor Red ; exit 1 }
Write-Host "   npm install 完成" -ForegroundColor Green

# Step 3: vite build
Write-Host "[3/4] 构建生产版本..." -ForegroundColor Yellow
npx vite build
if (-not $?) { Write-Host "   vite build 失败！" -ForegroundColor Red ; exit 1 }
Write-Host "   构建完成" -ForegroundColor Green

# Step 4: 产物复制回 D 盘
Write-Host "[4/4] 复制产物到 D 盘..." -ForegroundColor Yellow
if (Test-Path "$SrcDir\dist") { Remove-Item "$SrcDir\dist" -Recurse -Force }
& $ROBO "$DstDir\dist" "$SrcDir\dist" /E /XJ /NFL /NDL /NJH /NJS /NC /NS /NP
if ($LASTEXITCODE -ge 8) {
    Write-Host "   产物同步失败（退出码 $LASTEXITCODE）！" -ForegroundColor Red
    exit 1
}
$assetCount = (Get-ChildItem "$SrcDir\dist\assets" -File -ErrorAction SilentlyContinue).Count
Write-Host "   产物同步完成（assets 共 $assetCount 个文件）" -ForegroundColor Green

Set-Location $Project
Write-Host "=== 前端构建成功！===" -ForegroundColor Green
