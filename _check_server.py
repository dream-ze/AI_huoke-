"""快速检查服务器状态"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("116.62.86.160", username="root", password="Yang@666", timeout=30)

cmds = [
    "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'",
    "docker images --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}'",
    "ls -la /opt/zhihuokeke/backend/.env 2>/dev/null || echo '.env 不存在'",
    "ls /opt/zhihuokeke/backend/*.sh 2>/dev/null || echo '无 .sh 文件'",
    "cat /opt/zhihuokeke/backend/.env 2>/dev/null | grep -E '^(DATABASE_URL|SECRET_KEY|ENVIRONMENT)' || echo '无.env'",
]

for cmd in cmds:
    _, o, e = ssh.exec_command(cmd, timeout=15)
    print(f"\n>>> {cmd[:80]}")
    print(o.read().decode("utf-8", errors="replace").strip())
    err = e.read().decode("utf-8", errors="replace").strip()
    if err:
        print(f"  stderr: {err[:200]}")

ssh.close()
