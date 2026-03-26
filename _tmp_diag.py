import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("116.62.86.160", username="root", password="Yang@666", timeout=15)

checks = [
    ("容器状态",      "docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'"),
    ("backend日志",   "docker logs zhihuokeke-backend --tail 40 2>&1"),
    ("前端文件",      "ls -lh /opt/zhihuokeke/desktop/dist/ 2>/dev/null || echo 'dist目录不存在'"),
    ("backend静态挂载", "docker exec zhihuokeke-backend ls /app/static/ 2>&1 || echo 'no /app/static'"),
]
for label, cmd in checks:
    print(f"\n{'='*10} {label} {'='*10}")
    _, o, _ = ssh.exec_command(cmd, timeout=15)
    o.channel.recv_exit_status()
    print(o.read().decode("utf-8", errors="replace").strip())

ssh.close()
