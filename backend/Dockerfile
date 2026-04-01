FROM python:3.10-slim

WORKDIR /app

# Install Python dependencies via requirements.txt.
# Use a China mirror to speed up downloads on domestic networks.
COPY requirements.txt ./
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# Switch apt sources to Aliyun mirror for faster downloads in China
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null; \
    sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null; \
    true

# Install Playwright browser and dependencies for internal collector
# Step 1: Download Chromium via npmmirror CDN (fast in China)
RUN PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/chrome-for-testing \
    playwright install chromium; \
    playwright install ffmpeg || true; \
    playwright install-deps chromium

# Copy application code
COPY . .

# Fix Windows CRLF line endings and make entrypoint executable
RUN sed -i 's/\r//' entrypoint.sh && chmod +x entrypoint.sh

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/app/entrypoint.sh"]
