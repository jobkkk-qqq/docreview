<#
.SYNOPSIS
  前端构建脚本 — 在 C 盘执行 npm install + vite build，将产物复制回 D 盘
  原因：D 盘无法正确安装 @rolldown 等原生二进制包的 node_modules
#>

$SrcDir = "D:\python\docreview\frontend"
$DstDir = "C:\Users\Liang\temp_frontend"
$Project = "D:\python\docreview"

Write-Host "=== 构建前端 ===" -ForegroundColor Cyan

# Step 1: 同步源码到 C 盘（排除 node_modules、dist）
Write-Host "[1/4] 同步源码到 C 盘..." -ForegroundColor Yellow
if (Test-Path $DstDir) { Remove-Item $DstDir -Recurse -Force }
New-Item $DstDir -ItemType Directory -Force | Out-Null

Get-ChildItem $SrcDir -Recurse -File | Where-Object {
    $_.FullName -notmatch '\\node_modules\\' -and $_.FullName -notmatch '\\dist\\'
} | ForEach-Object {
    $rel = $_.FullName.Substring($SrcDir.Length + 1)
    $tgt = "$DstDir\$rel"
    $parent = Split-Path $tgt -Parent
    if (-not (Test-Path $parent)) { New-Item $parent -ItemType Directory -Force | Out-Null }
    Copy-Item $_.FullName $tgt -Force
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
python -c "
import shutil, os
src = r'$DstDir\dist'
dst = r'$SrcDir\dist'
if os.path.exists(dst):
    shutil.rmtree(dst)
shutil.copytree(src, dst)
print('   产物同步完成：' + str(len(os.listdir(os.path.join(dst, 'assets')))) + ' 个文件')
"

Set-Location $Project
Write-Host "=== 前端构建成功！===" -ForegroundColor Green
