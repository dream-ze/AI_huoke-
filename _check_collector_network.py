import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("116.62.86.160", username="root", password="Yang@666", timeout=30)

def run(cmd, timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", "replace").strip()
    err = stderr.read().decode("utf-8", "replace").strip()
    return out or err

print("Gateway:", run("docker exec zhihuokeke-backend python3 -c 'import struct,socket; f=open(\"/proc/net/route\"); lines=f.readlines(); gws=[l.split() for l in lines[1:] if l.split()[1]==\"00000000\"]; print([socket.inet_ntoa(struct.pack(\"<L\",int(gw[2],16))) for gw in gws])'"))

# 写临时 Python 文件到容器内测试
test_script = '''
import urllib.request, sys
for ip in ["172.18.0.1", "172.17.0.1", "116.62.86.160"]:
    try:
        r = urllib.request.urlopen("http://" + ip + ":8005/health", timeout=5)
        print(ip, "OK", r.read().decode())
    except Exception as e:
        print(ip, "FAIL", str(e))
'''.strip()

run("cat > /tmp/test_collector.py << 'PYEOF'\n" + test_script + "\nPYEOF")
print("Connectivity test:")
print(run("docker exec zhihuokeke-backend python3 /tmp/test_collector.py", timeout=20))

# 更新 .env
print("\nUpdating .env...")
print(run("sed -i 's|BROWSER_COLLECTOR_BASE_URL=.*|BROWSER_COLLECTOR_BASE_URL=http://172.18.0.1:8005|' /opt/zhihuokeke/backend/.env"))
print(run("grep BROWSER_COLLECTOR /opt/zhihuokeke/backend/.env"))
print(run("cd /opt/zhihuokeke/backend && docker compose -f docker-compose.prod.yml restart backend 2>&1 | tail -3", timeout=30))

ssh.close()
print("Done.")
