"""一次性远程部署脚本 - 用完即删"""
import paramiko, os, sys, time

SERVER = "116.62.86.160"
USER = "root"
PASSWD = "Yang@666"
PROJECT_ROOT = r"D:\智获客"
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
DESKTOP_DIST = os.path.join(PROJECT_ROOT, "desktop", "dist")

SKIP_DIRS = {".venv", "__pycache__", ".git", "node_modules", "build", "dist", ".pytest_cache", ".mypy_cache"}
SKIP_EXTS = {".pyc"}

print("=" * 50)
print(" 智获客 - 远程部署脚本")
print(f" 目标: {USER}@{SERVER}")
print("=" * 50)

# ── 连接（大超时 + 重试） ──────────────────────────────────
print("\n[1/5] 连接服务器...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
for _attempt in range(5):
    try:
        print(f"  连接尝试 {_attempt+1}/5 ...", flush=True)
        ssh.connect(SERVER, username=USER, password=PASSWD,
                    timeout=120, banner_timeout=120, auth_timeout=120)
        break
    except Exception as _e:
        print(f"  失败: {_e}", flush=True)
        if _attempt < 4:
            _wait = 15 * (_attempt + 1)
            print(f"  等待 {_wait}s 后重试...", flush=True)
            time.sleep(_wait)
        else:
            print("所有连接尝试失败，退出", flush=True)
            sys.exit(1)
sftp = ssh.open_sftp()
print("  OK - SSH 连接成功")


def ssh_exec(cmd, check=True):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=300)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    if check and exit_code != 0:
        print(f"  [WARN] exit={exit_code}: {cmd[:80]}")
        if err.strip():
            print(f"  stderr: {err[:300]}")
    return out, err, exit_code


def sftp_mkdir_p(remote_dir):
    dirs = []
    d = remote_dir
    while d and d != "/":
        dirs.append(d)
        d = os.path.dirname(d)
    dirs.reverse()
    for d in dirs:
        try:
            sftp.stat(d)
        except FileNotFoundError:
            sftp.mkdir(d)


def upload_dir(local_dir, remote_dir, skip_dirs=None, skip_exts=None):
    if skip_dirs is None:
        skip_dirs = set()
    if skip_exts is None:
        skip_exts = set()
    count = 0
    for root, dirs, files in os.walk(local_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        rel = os.path.relpath(root, local_dir).replace(os.sep, "/")
        remote_path = remote_dir if rel == "." else f"{remote_dir}/{rel}"
        sftp_mkdir_p(remote_path)
        for f in files:
            if any(f.endswith(ext) for ext in skip_exts):
                continue
            if f == ".env":
                continue
            local_file = os.path.join(root, f)
            remote_file = f"{remote_path}/{f}"
            try:
                sftp.put(local_file, remote_file)
                count += 1
                if count % 50 == 0:
                    print(f"    已上传 {count} 个文件...")
            except Exception as e:
                print(f"    [WARN] 跳过 {f}: {e}")
    return count


# ── 创建目录 ────────────────────────────────────────────────
print("\n[2/5] 创建服务器目录...")
ssh_exec("mkdir -p /opt/zhihuokeke/backend /opt/zhihuokeke/desktop/dist")
print("  OK - 目录已创建")

# ── 上传后端 ────────────────────────────────────────────────
print("\n[3/5] 上传后端代码...")
n = upload_dir(BACKEND_DIR, "/opt/zhihuokeke/backend", SKIP_DIRS, SKIP_EXTS)
print(f"  OK - 后端已上传 ({n} 个文件)")

# ── 上传前端 ────────────────────────────────────────────────
print("\n[4/5] 上传前端 dist...")
n2 = upload_dir(DESKTOP_DIST, "/opt/zhihuokeke/desktop/dist")
print(f"  OK - 前端已上传 ({n2} 个文件)")

# ── 远程部署 ────────────────────────────────────────────────
print("\n[5/5] 在服务器执行 deploy.sh（Docker 构建 + 启动）...")
deploy_cmd = (
    "cd /opt/zhihuokeke/backend && "
    "sed -i 's/\\r//' deploy.sh entrypoint.sh 2>/dev/null; "
    "chmod +x deploy.sh entrypoint.sh; "
    "bash deploy.sh 2>&1"
)
out, err, code = ssh_exec(deploy_cmd, check=False)
print(out)
if err.strip():
    print("--- stderr ---")
    print(err[-500:])

# ── 输出结果 ────────────────────────────────────────────────
print("\n" + "=" * 50)
if code == 0:
    print(" 部署完成！")
else:
    print(f" 部署脚本退出码: {code}")
print("=" * 50)
print(f"  API 地址 : http://{SERVER}:8000")
print(f"  API 文档 : http://{SERVER}:8000/docs")
print(f"  健康检查 : http://{SERVER}:8000/health")
print(f"  前端页面 : http://{SERVER}:8000/")

sftp.close()
ssh.close()
