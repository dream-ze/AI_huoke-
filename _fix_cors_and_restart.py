"""修复CORS配置并重启backend"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("116.62.86.160", username="root", password="Yang@666", timeout=30)

update_env_py = r'''
from pathlib import Path
p = Path('/opt/zhihuokeke/backend/.env')
text = p.read_text(encoding='utf-8', errors='ignore')
lines = text.splitlines()
out = []
replaced = False
value = 'CORS_ORIGINS=["http://116.62.86.160:8000","http://localhost:5173","http://127.0.0.1:5173"]'
for ln in lines:
    if ln.startswith('CORS_ORIGINS='):
        out.append(value)
        replaced = True
    else:
        out.append(ln)
if not replaced:
    out.append(value)
p.write_text('\n'.join(out) + '\n', encoding='utf-8')
print('CORS_ORIGINS updated')
'''

with ssh.open_sftp().open('/tmp/fix_cors.py', 'w') as f:
    f.write(update_env_py)

commands = [
    ("python3 /tmp/fix_cors.py", "更新CORS配置"),
    ("cd /opt/zhihuokeke/backend && docker compose -f docker-compose.prod.yml restart backend", "重启backend"),
    ("for i in $(seq 1 30); do curl -sf http://localhost:8000/health && exit 0; sleep 2; done; echo '后端未就绪'", "健康检查"),
    ("docker logs zhihuokeke-backend --tail 80 2>&1", "后端日志"),
    ("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'", "容器状态"),
]

for cmd, title in commands:
    _, o, e = ssh.exec_command(cmd, timeout=120)
    print(f"\n=== {title} ===")
    out = o.read().decode('utf-8', errors='replace').strip()
    err = e.read().decode('utf-8', errors='replace').strip()
    if out:
        print(out)
    if err:
        print('stderr:', err)

ssh.close()
