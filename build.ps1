<#
.SYNOPSIS
  智获客 一键打包脚本
  打包顺序：
    1. 后端 Python → PyInstaller → backend/dist/backend/backend.exe
    2. 前端 React → Vite → desktop/dist/
    3. Electron-builder → desktop/release/智获客 Setup x.x.x.exe

.USAGE
  在项目根目录下执行:
    .\build.ps1
  可选参数:
    -SkipBackend   跳过后端打包（backend.exe 已存在时可用）
    -SkipFrontend  跳过前端编译
#>

param(
    [switch]$SkipBackend,
    [switch]$SkipFrontend
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

function Write-Step($msg) {
    Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "  $msg" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
}

function Assert-Command($cmd) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Host "[错误] 未找到命令: $cmd" -ForegroundColor Red
        exit 1
    }
}

# ─── 前置检查 ─────────────────────────────────────────────────────
Write-Step "环境检查"
Assert-Command "python"
Assert-Command "npm"

$pythonVersion = python --version 2>&1
Write-Host "Python: $pythonVersion"
$nodeVersion = node --version 2>&1
Write-Host "Node:   $nodeVersion"

# ─── Step 1: 打包 Python 后端 ────────────────────────────────────
if (-not $SkipBackend) {
    Write-Step "Step 1/3 — 打包 Python 后端 (PyInstaller)"

    Set-Location "$Root\backend"

    # 确保 PyInstaller 已安装
    $pyiInstalled = python -c "import PyInstaller" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "安装 PyInstaller..." -ForegroundColor Yellow
        pip install pyinstaller --quiet
    }

    # 清理旧产物
    if (Test-Path "dist") { Remove-Item "dist" -Recurse -Force }
    if (Test-Path "build") { Remove-Item "build" -Recurse -Force }

    Write-Host "运行 PyInstaller..." -ForegroundColor Yellow
    pyinstaller backend.spec --clean --noconfirm

    if (-not (Test-Path "dist\backend\backend.exe")) {
        Write-Host "[错误] PyInstaller 打包失败，未找到 dist\backend\backend.exe" -ForegroundColor Red
        exit 1
    }
    Write-Host "[完成] 后端打包成功: backend\dist\backend\backend.exe" -ForegroundColor Green
} else {
    Write-Host "[跳过] 后端打包" -ForegroundColor Yellow
    if (-not (Test-Path "$Root\backend\dist\backend\backend.exe")) {
        Write-Host "[警告] 未找到 backend\dist\backend\backend.exe，打包的安装包将缺少后端！" -ForegroundColor Yellow
    }
}

# ─── Step 2: 编译前端 ────────────────────────────────────────────
Set-Location "$Root\desktop"

if (-not $SkipFrontend) {
    Write-Step "Step 2/3 — 编译前端 (Vite)"

    # 安装依赖（如果 node_modules 不存在）
    if (-not (Test-Path "node_modules")) {
        Write-Host "安装前端依赖..." -ForegroundColor Yellow
        npm install
    }

    Write-Host "Vite 构建..." -ForegroundColor Yellow
    npm run build:web

    if (-not (Test-Path "dist\index.html")) {
        Write-Host "[错误] Vite 构建失败，未找到 dist\index.html" -ForegroundColor Red
        exit 1
    }
    Write-Host "[完成] 前端构建成功" -ForegroundColor Green
} else {
    Write-Host "[跳过] 前端构建" -ForegroundColor Yellow
}

# ─── Step 3: electron-builder 打包 ──────────────────────────────
Write-Step "Step 3/3 — electron-builder 打包 Windows 安装程序"

# 检查图标文件，没有就创建占位
$iconDir = "$Root\desktop\build"
if (-not (Test-Path $iconDir)) { New-Item -ItemType Directory -Path $iconDir -Force | Out-Null }
if (-not (Test-Path "$iconDir\icon.ico")) {
    Write-Host "[提示] 未找到 build\icon.ico，将使用默认图标" -ForegroundColor Yellow
    # 移除 package.json 中的 icon 引用不报错：electron-builder 会用默认图标
}

npm run dist

# 输出结果
Write-Step "打包完成"
$exeFiles = Get-ChildItem "$Root\desktop\release" -Filter "*.exe" -Recurse -ErrorAction SilentlyContinue
if ($exeFiles) {
    Write-Host "`n安装包位置:" -ForegroundColor Green
    $exeFiles | ForEach-Object { Write-Host "  $($_.FullName)" -ForegroundColor White }
} else {
    Write-Host "[警告] 未在 release 目录找到 .exe 文件，请检查 electron-builder 日志" -ForegroundColor Yellow
}

Set-Location $Root
