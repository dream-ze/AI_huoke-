import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("116.62.86.160", username="root", password="Yang@666", timeout=30)

def run(cmd, timeout=20):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode("utf-8", "replace").strip() + stderr.read().decode("utf-8", "replace").strip()

# SFTP write the test script
sftp = ssh.open_sftp()
with sftp.open("/tmp/chk.py", "w") as f:
    f.write("import urllib.request\n")
    f.write("for ip in ['172.18.0.1','172.17.0.1','116.62.86.160']:\n")
    f.write("    try:\n")
    f.write("        r=urllib.request.urlopen('http://'+ip+':8005/health',timeout=5)\n")
    f.write("        print(ip,'OK',r.read().decode())\n")
    f.write("    except Exception as e:\n")
    f.write("        print(ip,'FAIL',str(e))\n")
sftp.close()
print("wrote /tmp/chk.py")

print("cp:", run("docker cp /tmp/chk.py zhihuokeke-backend:/tmp/chk.py"))
print("result:\n", run("docker exec zhihuokeke-backend python3 /tmp/chk.py", timeout=30))

# Also verify BROWSER_COLLECTOR_BASE_URL in container env
print("\ncontainer env:", run("docker exec zhihuokeke-backend env | grep BROWSER"))

ssh.close()
print("Done.")
