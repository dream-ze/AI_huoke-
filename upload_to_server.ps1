# ============================================================
# upload_to_server.ps1   在本机(Windows)执行
# 把 browser_collector 上传到服务器 116.62.86.160
# 使用前提：本机已安装 ssh / scp（Win10/11 自带 OpenSSH）
# ============================================================

$SERVER     = "116.62.86.160"
$SERVER_USER= "root"
$REMOTE_DIR = "/www"
$LOCAL_DIR  = "$PSScriptRoot"   # 脚本所在目录（即 browser_collector/）

Write-Host "====== [1/3] 在服务器上创建目录 ======"
ssh "${SERVER_USER}@${SERVER}" "mkdir -p /www/browser_collector"

Write-Host "====== [2/3] 上传代码（排除缓存和本地 state）======"
# 用 scp -r 上传整个目录
# 注意：如果登录状态文件 xiaohongshu_state.json 已存在且已登录，才上传
scp -r `
    "${LOCAL_DIR}\app" `
    "${LOCAL_DIR}\requirements.txt" `
    "${LOCAL_DIR}\.env.prod" `
    "${LOCAL_DIR}\deploy.sh" `
    "${LOCAL_DIR}\browser_collector.service" `
    "${SERVER_USER}@${SERVER}:/www/browser_collector/"

Write-Host "====== [3/3] 上传小红书登录状态文件 ======"
$STATE_FILE = "${LOCAL_DIR}\xiaohongshu_state.json"
if (Test-Path $STATE_FILE) {
    scp $STATE_FILE "${SERVER_USER}@${SERVER}:/www/browser_collector/xiaohongshu_state.json"
    Write-Host "✅ xiaohongshu_state.json 上传成功"
} else {
    Write-Host "⚠️  未找到 xiaohongshu_state.json，登录状态未上传"
    Write-Host "   请先在本机运行 save_login.py 完成登录，再重新执行此脚本"
}

Write-Host ""
Write-Host "====== 上传完成，在服务器执行以下命令完成部署 ======"
Write-Host ""
Write-Host "  ssh ${SERVER_USER}@${SERVER}"
Write-Host "  chmod +x /www/browser_collector/deploy.sh"
Write-Host "  bash /www/browser_collector/deploy.sh"
Write-Host ""
