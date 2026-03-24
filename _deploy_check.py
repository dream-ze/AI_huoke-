"""检查后台构建进度"""
import paramiko, sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("116.62.86.160", username="root", password="Yang@666", timeout=30)

# 查看构建日志尾部
_, o, _ = ssh.exec_command("tail -80 /tmp/deploy.log 2>/dev/null || echo '日志文件不存在'", timeout=15)
print("=== 构建日志（最后80行）===")
print(o.read().decode("utf-8", errors="replace"))

# 查看容器状态
_, o, _ = ssh.exec_command("docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'", timeout=10)
print("\n=== 容器状态 ===")
print(o.read().decode("utf-8", errors="replace"))

# 检查是否有构建进程
_, o, _ = ssh.exec_command("pgrep -fa 'docker' | head -5", timeout=10)
print("=== Docker 进程 ===")
print(o.read().decode("utf-8", errors="replace"))

# 尝试健康检查
_, o, _ = ssh.exec_command("curl -sf http://localhost:8000/health 2>&1 || echo '后端未就绪'", timeout=10)
print("=== 健康检查 ===")
print(o.read().decode("utf-8", errors="replace"))

ssh.close()
