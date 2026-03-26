param(
    [string]$Keyword = "贷款",
    [int]$MaxItems = 10,
    [switch]$NeedDetail = $true,
    [switch]$NeedComments = $true,
    [int]$TimeoutSec = 180,
    [string]$Host = "127.0.0.1",
    [int]$Port = 8005,
    [string]$PythonExe = "C:\Users\ASUS\miniconda3\python.exe",
    [string]$WorkspaceRoot = "D:\Playwright爬虫"
)

$ErrorActionPreference = "Stop"

$collectorRoot = Join-Path $WorkspaceRoot "browser_collector"
$exportDir = Join-Path $WorkspaceRoot "exports"

Write-Host "[1/3] 启动采集服务..." -ForegroundColor Cyan
$uvicornArgs = @(
    "-m", "uvicorn",
    "app.main:app",
    "--app-dir", $collectorRoot,
    "--host", $Host,
    "--port", "$Port"
)
$serverProc = Start-Process -FilePath $PythonExe -ArgumentList $uvicornArgs -PassThru

try {
    Start-Sleep -Seconds 3

    Write-Host "[2/3] 调用采集并导出 Excel..." -ForegroundColor Cyan
    $collectArgs = @(
        (Join-Path $collectorRoot "run_collect_to_excel.py"),
        "--host", $Host,
        "--port", "$Port",
        "--keyword", $Keyword,
        "--max-items", "$MaxItems",
        "--timeout", "$TimeoutSec",
        "--output-dir", $exportDir
    )

    if ($NeedDetail) {
        $collectArgs += "--need-detail"
    }
    if ($NeedComments) {
        $collectArgs += "--need-comments"
    }

    & $PythonExe @collectArgs

    Write-Host "[3/3] 导出完成，目录: $exportDir" -ForegroundColor Green
}
finally {
    if ($null -ne $serverProc -and -not $serverProc.HasExited) {
        Write-Host "停止采集服务进程..." -ForegroundColor Yellow
        Stop-Process -Id $serverProc.Id -Force
    }
}