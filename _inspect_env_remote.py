"""检查远程.env中CORS相关配置"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("116.62.86.160", username="root", password="Yang@666", timeout=30)

commands = [
    ("nl -ba /opt/zhihuokeke/backend/.env | sed -n '1,120p'", "前120行"),
    ("grep -n 'CORS_ORIGINS' /opt/zhihuokeke/backend/.env", "CORS行"),
    ("grep -n '\\*' /opt/zhihuokeke/backend/.env || true", "包含*的行"),
]

for cmd, title in commands:
    _, o, e = ssh.exec_command(cmd, timeout=20)
    print(f"\n=== {title} ===")
    print(o.read().decode("utf-8", errors="replace"))
    err = e.read().decode("utf-8", errors="replace").strip()
    if err:
        print("stderr:", err)

ssh.close()
