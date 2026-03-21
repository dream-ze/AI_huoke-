# ============================================================
# 智获客 - Windows 端一键部署脚本
# 功能: 构建桌面端 → 上传 → 在服务器启动 Docker 服务
#
# 使用方法:
#   .\deploy.ps1
#   .\deploy.ps1 -ServerUser ubuntu  (云服务器默认账号可能是 ubuntu)
#   .\deploy.ps1 -KeyFile "C:\path\to\key.pem"
#
# 前置条件: 本机已安装 OpenSSH (Win10+ 已内置 ssh/scp)
# ============================================================
param(
    [string]$ServerIP   = "116.62.86.160",
    [string]$ServerUser = "root",
    [string]$KeyFile    = "",       # SSH 私钥路径，留空则用密码认证
    [switch]$SkipBuild  = $false    # 跳过前端构建（仅上传）
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$BackendDir  = "$ProjectRoot\backend"
$DesktopDir  = "$ProjectRoot\desktop"

# SSH/SCP 公共参数
$SshOpts = @("-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=30")
if ($KeyFile) { $SshOpts += @("-i", $KeyFile) }

function Run-SSH {
    param([string]$Cmd)
    & ssh @SshOpts "$ServerUser@$ServerIP" $Cmd
    if ($LASTEXITCODE -ne 0) { throw "SSH 命令失败: $Cmd" }
}

function Run-SCP {
    param([string]$Src, [string]$Dst)
    & scp @SshOpts -r $Src "${ServerUser}@${ServerIP}:$Dst"
    if ($LASTEXITCODE -ne 0) { throw "SCP 失败: $Src → $Dst" }
}

Write-Host ""
Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   智获客 一键部署脚本 (Windows → 服务器)   ║" -ForegroundColor Cyan
Write-Host "║   目标: $ServerUser@$ServerIP         ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: 构建桌面端 ───────────────────────────────────────────
if (-not $SkipBuild) {
    Write-Host "[1/4] 构建桌面端 (Vite)..." -ForegroundColor Green
    Push-Location $DesktopDir

    # 写入生产环境变量（指向服务器 API）
    "VITE_API_BASE_URL=http://${ServerIP}:8000" | Set-Content ".env.production" -Encoding UTF8
    Write-Host "      → VITE_API_BASE_URL=http://${ServerIP}:8000"

    npm run build:web
    if ($LASTEXITCODE -ne 0) { Pop-Location; throw "前端构建失败" }
    Pop-Location
    Write-Host "      ✓ 构建完成: desktop\dist\" -ForegroundColor Green
} else {
    Write-Host "[1/4] 跳过构建 (-SkipBuild)" -ForegroundColor Yellow
}

# ── Step 2: 在服务器创建目录 ─────────────────────────────────────
Write-Host ""
Write-Host "[2/4] 在服务器创建目录..." -ForegroundColor Green
Run-SSH "mkdir -p /opt/zhihuokeke/backend"
Write-Host "      ✓ /opt/zhihuokeke/backend"

# ── Step 3: 上传 backend 目录 ────────────────────────────────────
Write-Host ""
Write-Host "[3/4] 上传 backend 到服务器..." -ForegroundColor Green

# 创建临时排除列表（不上传 venv/__pycache__/本地.env）
$TempExclude = New-TemporaryFile
@(".venv", "__pycache__", ".env", "*.pyc", "*.egg-info") | Set-Content $TempExclude

# scp 不支持排除，用 rsync 更好；提供两种方式
if (Get-Command rsync -ErrorAction SilentlyContinue) {
    $excludeArgs = @("--exclude=.venv", "--exclude=__pycache__", "--exclude=.env",
                     "--exclude=*.pyc", "-az", "-e", "ssh $($SshOpts -join ' ')")
    & rsync @excludeArgs "$BackendDir/" "${ServerUser}@${ServerIP}:/opt/zhihuokeke/backend/"
} else {
    # 无 rsync，使用 scp（会上传 .venv 等，但不影响部署）
    Write-Host "      [提示] 建议安装 rsync 以加速上传，当前使用 scp"
    Run-SCP "$BackendDir" "/opt/zhihuokeke/"
}
Write-Host "      ✓ 上传完成"

# ── Step 4: 远程执行部署 ─────────────────────────────────────────
Write-Host ""
Write-Host "[4/4] 在服务器执行 deploy.sh..." -ForegroundColor Green
Run-SSH @"
cd /opt/zhihuokeke/backend
sed -i 's/\r//' deploy.sh entrypoint.sh setup-venv.sh 2>/dev/null || true
chmod +x deploy.sh entrypoint.sh setup-venv.sh
bash deploy.sh
"@

# ── 完成 ─────────────────────────────────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║            部署完成！                      ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "  服务器 API : http://${ServerIP}:8000" -ForegroundColor Cyan
Write-Host "  API  文档  : http://${ServerIP}:8000/docs" -ForegroundColor Cyan
Write-Host "  生产主路径 : Docker Compose (backend/docker-compose.prod.yml)" -ForegroundColor Cyan
Write-Host ""
Write-Host "  桌面端安装包: 执行 'npm run dist' 在 desktop\ 目录" -ForegroundColor Yellow
Write-Host "  安装包输出  : desktop\release\" -ForegroundColor Yellow
Write-Host ""
Write-Host "  查看服务器日志:" -ForegroundColor White
Write-Host "    ssh $ServerUser@$ServerIP 'docker compose -f /opt/zhihuokeke/backend/docker-compose.prod.yml logs -f'" -ForegroundColor Gray
