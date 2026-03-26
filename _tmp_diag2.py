import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("116.62.86.160", username="root", password="Yang@666", timeout=15)

checks = [
    ("容器内前端目录",   "docker exec zhihuokeke-backend ls -lh /desktop/dist/ 2>&1 || echo 'NOT FOUND'"),
    ("index.html内容",   "docker exec zhihuokeke-backend cat /desktop/dist/index.html 2>&1 | head -20"),
    ("docker-compose volumes", "cat /opt/zhihuokeke/backend/docker-compose.prod.yml"),
    ("host index.html",  "head -5 /opt/zhihuokeke/desktop/dist/index.html"),
]
for label, cmd in checks:
    print(f"\n{'='*12} {label} {'='*12}")
    _, o, _ = ssh.exec_command(cmd, timeout=10)
    o.channel.recv_exit_status()
    print(o.read().decode("utf-8", errors="replace").strip())

ssh.close()
