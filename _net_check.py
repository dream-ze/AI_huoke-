import paramiko, textwrap

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("116.62.86.160", username="root", password="Yang@666", timeout=30)

def run(cmd, timeout=20):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode("utf-8", "replace").strip() + stderr.read().decode("utf-8", "replace").strip()

# Write test script to host then copy into container
code_lines = [
    "import socket, urllib.request",
    "for ip in ['172.18.0.1','172.17.0.1','116.62.86.160']:",
    "    try:",
    "        r=urllib.request.urlopen('http://'+ip+':8005/health',timeout=5)",
    "        print(ip,'OK',r.read().decode())",
    "    except Exception as e:",
    "        print(ip,'FAIL',str(e))",
]
code = "\n".join(code_lines)

# write via python on remote
write_cmd = f"python3 -c \"open('/tmp/chk.py','w').write({repr(code)})\""
print("write:", run(write_cmd))
print("cp:", run("docker cp /tmp/chk.py zhihuokeke-backend:/tmp/chk.py"))
print("test result:")
print(run("docker exec zhihuokeke-backend python3 /tmp/chk.py", timeout=30))

# Also check iptables for 8005 
print("\niptables port 8005:")
print(run("iptables -L INPUT -n | grep 8005 || echo no-rule"))
print("firewall status:", run("ufw status 2>/dev/null | head -5 || echo no-ufw"))

ssh.close()
print("Done.")
