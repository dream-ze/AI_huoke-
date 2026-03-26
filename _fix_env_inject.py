import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("116.62.86.160", username="root", password="Yang@666", timeout=30)

def run(cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode("utf-8", "replace").strip() + stderr.read().decode("utf-8", "replace").strip()

print("=== docker-compose.prod.yml env_file config ===")
print(run("grep -A5 'env_file\\|environment' /opt/zhihuokeke/backend/docker-compose.prod.yml"))

print("\n=== .env content (relevant lines) ===")
print(run("grep -E 'BROWSER|DATABASE|SECRET|REDIS' /opt/zhihuokeke/backend/.env"))

# Do a full down + up to reload env
print("\n=== down + up (to reload env) ===")
print(run(
    "cd /opt/zhihuokeke/backend && "
    "docker compose -f docker-compose.prod.yml down backend && "
    "docker compose -f docker-compose.prod.yml up -d backend && "
    "sleep 4 && docker exec zhihuokeke-backend env | grep BROWSER",
    timeout=60
))

ssh.close()
print("Done.")
