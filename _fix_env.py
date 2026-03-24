"""修复服务器 .env 文件"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("116.62.86.160", username="root", password="Yang@666", timeout=30)
sftp = ssh.open_sftp()

# 写一个 Python 修复脚本到服务器
fix_script = r'''
path = "/opt/zhihuokeke/backend/.env"
with open(path) as f:
    lines = f.read().splitlines()

new_lines = []
for line in lines:
    s = line.strip()
    # 删除坏的行（被 sed 搞坏的 DATABASE_URL）
    if s.startswith("@postgres:"):
        continue
    if s.startswith("DATABASE_URL="):
        continue
    # 在 DATABASE_HOST 前插入正确的 DATABASE_URL
    if s.startswith("DATABASE_HOST="):
        new_lines.append("DATABASE_URL=postgresql://postgres:Zhk_Db_2024@postgres:5432/zhihuokeke")
        new_lines.append("DATABASE_HOST=postgres")
        continue
    # 修复 OLLAMA_BASE_URL
    if s.startswith("OLLAMA_BASE_URL="):
        new_lines.append("OLLAMA_BASE_URL=http://ollama:11434")
        continue
    new_lines.append(line)

with open(path, "w") as f:
    f.write("\n".join(new_lines) + "\n")

print("=== .env 已修复，关键配置 ===")
with open(path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and any(line.startswith(k) for k in [
            "DATABASE_URL=", "DATABASE_PASSWORD=", "DATABASE_HOST=",
            "OLLAMA_BASE_URL=", "SECRET_KEY=", "ENVIRONMENT="
        ]):
            print(line)
'''

with sftp.open("/tmp/fix_env.py", "w") as f:
    f.write(fix_script)

# 执行修复
_, o, e = ssh.exec_command("python3 /tmp/fix_env.py", timeout=10)
print(o.read().decode("utf-8", errors="replace"))
err = e.read().decode("utf-8", errors="replace").strip()
if err:
    print(f"ERR: {err}")

sftp.close()
ssh.close()
