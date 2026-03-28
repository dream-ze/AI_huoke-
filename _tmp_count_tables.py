"""临时脚本：检查远端各表行数 & 可选执行 backfill"""
import paramiko, os, sys, time

SERVER = "116.62.86.160"
USER = "root"
PASSWD = "Yang@666"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER, username=USER, password=PASSWD, timeout=30)

# 先把诊断脚本上传到容器内
DIAG_SCRIPT = """\
import os, sys
sys.path.insert(0, '/app')
os.chdir('/app')
os.environ.setdefault('SECRET_KEY', 'tmp-diag-key-not-used-for-auth')
os.environ.setdefault('DEBUG', 'false')

from sqlalchemy import text, create_engine
db_url = os.environ.get('DATABASE_URL', '')
engine = create_engine(db_url)

tables = ['content_assets', 'material_items', 'source_contents', 'insight_contents', 'users']
with engine.connect() as conn:
    for t in tables:
        try:
            row = conn.execute(text(f'SELECT COUNT(*) FROM {t}')).scalar()
            print(f'{t}: {row}')
        except Exception as e:
            print(f'{t}: ERROR - {str(e)[:80]}')
"""

sftp = ssh.open_sftp()
with sftp.open('/tmp/diag_count.py', 'w') as f:
    f.write(DIAG_SCRIPT)
sftp.close()

# 把脚本复制进容器并运行
stdin, stdout, stderr = ssh.exec_command(
    "docker cp /tmp/diag_count.py zhihuokeke-backend:/tmp/diag_count.py && "
    "docker exec zhihuokeke-backend python3 /tmp/diag_count.py",
    timeout=60
)
ec = stdout.channel.recv_exit_status()
out = stdout.read().decode("utf-8", errors="replace")
err = stderr.read().decode("utf-8", errors="replace")
print("=== 远端各表行数 ===")
print(out.strip() or "(无输出)")
if err.strip():
    print("STDERR:", err[:400])
ssh.close()
