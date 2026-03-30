FROM python:3.10-slim

WORKDIR /app

# Install Python dependencies via requirements.txt.
# Use a China mirror to speed up downloads on domestic networks.
COPY requirements.txt ./
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# Install Playwright browser and dependencies for internal collector
RUN playwright install chromium && playwright install-deps chromium

# Copy application code
COPY . .

# Fix Windows CRLF line endings and make entrypoint executable
RUN sed -i 's/\r//' entrypoint.sh && chmod +x entrypoint.sh

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/app/entrypoint.sh"]
