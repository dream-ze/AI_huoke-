<#
.SYNOPSIS
    智获客一键初始化脚本 - 自动配置开发环境

.DESCRIPTION
    此脚本将自动执行以下步骤：
    1. 检查并创建 .env 配置文件
    2. 检查 Docker 运行状态
    3. 启动 Docker Compose 服务
    4. 等待 PostgreSQL 和 Redis 就绪
    5. 执行数据库迁移
    6. 运行种子数据脚本

.EXAMPLE
    ./scripts/init.ps1

.NOTES
    需要安装 Docker Desktop 和 PowerShell 7+
#>

param(
    [switch]$SkipSeed,      # 跳过种子数据
    [switch]$ForceEnv,      # 强制覆盖 .env 文件
    [int]$Timeout = 120     # 服务启动超时时间（秒）
)

$ErrorActionPreference = "Stop"
$StartTime = Get-Date

# 颜色输出函数
function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "    [OK] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "    [!] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "    [X] $Message" -ForegroundColor Red
}

# 获取项目根目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $ProjectRoot "backend"

Write-Host @"

========================================
  智获客 环境初始化脚本
========================================
项目根目录: $ProjectRoot
后端目录: $BackendDir

"@ -ForegroundColor White

# ==========================================
# 步骤 1: 检查 .env 文件
# ==========================================
Write-Step "检查环境配置文件"

$EnvFile = Join-Path $BackendDir ".env"
$EnvExample = Join-Path $BackendDir ".env.example"

if (Test-Path $EnvFile) {
    if ($ForceEnv) {
        Write-Warning "强制覆盖现有 .env 文件"
        Copy-Item $EnvExample $EnvFile -Force
        Write-Success ".env 文件已从 .env.example 重新创建"
    } else {
        Write-Success ".env 文件已存在"
    }
} else {
    if (Test-Path $EnvExample) {
        Copy-Item $EnvExample $EnvFile
        Write-Success ".env 文件已从 .env.example 创建"
        Write-Warning "请编辑 $EnvFile 设置必要配置（SECRET_KEY、DATABASE_PASSWORD 等）"
    } else {
        Write-Error ".env.example 文件不存在，请检查项目完整性"
        exit 1
    }
}

# ==========================================
# 步骤 2: 检查 Docker
# ==========================================
Write-Step "检查 Docker 运行状态"

try {
    $DockerVersion = docker --version 2>$null
    Write-Success "Docker 已安装: $DockerVersion"
} catch {
    Write-Error "Docker 未安装或不在 PATH 中"
    Write-Host "请先安装 Docker Desktop: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

try {
    $DockerInfo = docker info 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker 未运行"
    }
    Write-Success "Docker Desktop 正在运行"
} catch {
    Write-Error "Docker Desktop 未运行"
    Write-Host "请启动 Docker Desktop 后重试" -ForegroundColor Yellow
    exit 1
}

# ==========================================
# 步骤 3: 启动 Docker Compose
# ==========================================
Write-Step "启动 Docker Compose 服务"

Set-Location $BackendDir

# 检查 docker-compose.yml 是否存在
$ComposeFile = Join-Path $BackendDir "docker-compose.yml"
if (-not (Test-Path $ComposeFile)) {
    Write-Error "docker-compose.yml 不存在于 $BackendDir"
    exit 1
}

Write-Host "    执行: docker-compose up -d" -ForegroundColor Gray
docker-compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker Compose 启动失败"
    exit 1
}
Write-Success "Docker Compose 服务已启动"

# ==========================================
# 步骤 4: 等待 PostgreSQL 就绪
# ==========================================
Write-Step "等待 PostgreSQL 就绪"

$PostgresReady = $false
$Elapsed = 0

while (-not $PostgresReady -and $Elapsed -lt $Timeout) {
    try {
        # 使用 docker exec 检查 pg_isready
        $Result = docker exec zhihuokeke-db pg_isready -U postgres 2>$null
        if ($LASTEXITCODE -eq 0) {
            $PostgresReady = $true
            break
        }
    } catch {
        # 容器可能还未完全启动
    }

    Write-Host "    等待 PostgreSQL... ($Elapsed/$Timeout 秒)" -NoNewline -ForegroundColor Gray
    Write-Host "`r" -NoNewline
    Start-Sleep -Seconds 2
    $Elapsed += 2
}

if ($PostgresReady) {
    Write-Success "PostgreSQL 已就绪"
} else {
    Write-Error "PostgreSQL 启动超时（${Timeout}秒）"
    Write-Host "请检查日志: docker logs zhihuokeke-db" -ForegroundColor Yellow
    exit 1
}

# ==========================================
# 步骤 5: 等待 Redis 就绪
# ==========================================
Write-Step "等待 Redis 就绪"

$RedisReady = $false
$Elapsed = 0

while (-not $RedisReady -and $Elapsed -lt $Timeout) {
    try {
        $Result = docker exec zhihuokeke-redis redis-cli ping 2>$null
        if ($Result -match "PONG") {
            $RedisReady = $true
            break
        }
    } catch {
        # 容器可能还未完全启动
    }

    Write-Host "    等待 Redis... ($Elapsed/$Timeout 秒)" -NoNewline -ForegroundColor Gray
    Write-Host "`r" -NoNewline
    Start-Sleep -Seconds 1
    $Elapsed += 1
}

if ($RedisReady) {
    Write-Success "Redis 已就绪"
} else {
    Write-Error "Redis 启动超时（${Timeout}秒）"
    Write-Host "请检查日志: docker logs zhihuokeke-redis" -ForegroundColor Yellow
    exit 1
}

# ==========================================
# 步骤 6: 执行数据库迁移
# ==========================================
Write-Step "执行数据库迁移 (Alembic)"

Write-Host "    执行: alembic upgrade head" -ForegroundColor Gray

# 检查是否有 alembic 命令（需要 Python 环境）
try {
    Push-Location $BackendDir
    alembic upgrade head
    
    if ($LASTEXITCODE -ne 0) {
        throw "Alembic 迁移失败"
    }
    Write-Success "数据库迁移完成"
} catch {
    Write-Error "数据库迁移失败: $_"
    Write-Host "提示: 确保已安装 Python 依赖 (pip install -r requirements.txt)" -ForegroundColor Yellow
    Pop-Location
    exit 1
} finally {
    Pop-Location
}

# ==========================================
# 步骤 7: 运行种子数据脚本
# ==========================================
if (-not $SkipSeed) {
    Write-Step "运行种子数据脚本"

    $SeedScript = Join-Path $BackendDir "seed_mvp_data.py"
    
    if (Test-Path $SeedScript) {
        Write-Host "    执行: python seed_mvp_data.py" -ForegroundColor Gray
        
        try {
            Push-Location $BackendDir
            python seed_mvp_data.py
            
            if ($LASTEXITCODE -eq 0) {
                Write-Success "种子数据初始化完成"
            } else {
                Write-Warning "种子数据脚本执行异常（退出码: $LASTEXITCODE）"
            }
        } catch {
            Write-Warning "种子数据脚本执行失败: $_"
        } finally {
            Pop-Location
        }
    } else {
        Write-Warning "种子数据脚本不存在: $SeedScript"
    }
} else {
    Write-Step "跳过种子数据初始化（-SkipSeed 参数）"
}

# ==========================================
# 步骤 8: 输出成功信息
# ==========================================
$EndTime = Get-Date
$Duration = $EndTime - $StartTime

Write-Host @"

========================================
  初始化完成!
========================================
耗时: $($Duration.TotalSeconds.ToString('F1')) 秒

访问地址:
  - 后端 API:  http://localhost:8000
  - API 文档:  http://localhost:8000/docs
  - 健康检查:  http://localhost:8000/health
  - Ollama:    http://localhost:11434

服务状态:
  - PostgreSQL:  localhost:5432
  - Redis:       localhost:6379
  - Ollama:      localhost:11434

下一步操作:
  1. 编辑 backend/.env 配置必要参数
     - SECRET_KEY (至少32字符)
     - DATABASE_PASSWORD
     - ARK_API_KEY (如使用云端模型)
  
  2. 启动后端服务:
     cd backend && python main.py
     或
     cd backend && uvicorn main:app --reload

  3. 启动前端服务:
     cd desktop && npm run dev

常用命令:
  查看日志:     docker-compose logs -f
  停止服务:     docker-compose down
  重启服务:     docker-compose restart
  查看状态:     docker-compose ps

"@ -ForegroundColor Green
