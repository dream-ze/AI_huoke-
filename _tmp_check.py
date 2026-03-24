import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("116.62.86.160", username="root", password="Yang@666", timeout=30)

cmds = [
    ('docker inspect zhihuokeke-backend --format "RestartCount={{.RestartCount}} Status={{.State.Status}} ExitCode={{.State.ExitCode}}"', "容器重启详情"),
    ("docker logs zhihuokeke-backend --tail 100 2>&1", "后端完整日志"),
    ("ss -lntp | grep :8000 || echo NO_LISTEN", "8000端口监听"),
]

for cmd, title in cmds:
    _, o, e = ssh.exec_command(cmd, timeout=20)
    print(f"\n=== {title} ===")
    print(o.read().decode("utf-8", errors="replace").strip())

ssh.close()
