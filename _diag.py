import paramiko, time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('116.62.86.160', username='root', password='Yang@666', timeout=30)

cmds = [
    ('docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"', 'docker状态'),
    ('docker inspect zhihuokeke-backend --format "Restart={{.RestartCount}} Status={{.State.Status}} Exit={{.State.ExitCode}}"', '容器详情'),
    ('docker logs zhihuokeke-backend --since 5m 2>&1 | tail -40', '最近5分钟日志'),
    ('curl -si http://localhost:8000/ 2>&1 | head -5', '本机探测'),
]

for cmd, title in cmds:
    _, o, e = ssh.exec_command(cmd, timeout=25)
    print(f'\\n=== {title} ===')
    out = o.read().decode('utf-8', errors='replace').strip()
    err = e.read().decode('utf-8', errors='replace').strip()
    print(out or '(empty)')
    if err: print('ERR:', err[:300])
ssh.close()
