"""把 backfill 脚本上传到远端 Docker 容器并执行"""
import paramiko, os, sys

SERVER = "116.62.86.160"
USER = "root"
PASSWD = "Yang@666"
LOCAL_SCRIPT = r"D:\智获客\scripts\backfill_material_pipeline.py"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER, username=USER, password=PASSWD, timeout=30)

# 上传 backfill 脚本到宿主机
sftp = ssh.open_sftp()
sftp.put(LOCAL_SCRIPT, "/tmp/backfill_material_pipeline.py")
sftp.close()

# 复制进容器
stdin, stdout, stderr = ssh.exec_command(
    "docker cp /tmp/backfill_material_pipeline.py zhihuokeke-backend:/tmp/backfill_material_pipeline.py",
    timeout=30
)
stdout.channel.recv_exit_status()

# 容器内运行
print("=== 开始回填 ===")
stdin, stdout, stderr = ssh.exec_command(
    "docker exec zhihuokeke-backend python3 /tmp/backfill_material_pipeline.py",
    timeout=120
)
ec = stdout.channel.recv_exit_status()
out = stdout.read().decode("utf-8", errors="replace")
err = stderr.read().decode("utf-8", errors="replace")
print(out.strip() or "(无输出)")
if err.strip():
    print("STDERR:", err[:800])
print("exit code:", ec)
ssh.close()
