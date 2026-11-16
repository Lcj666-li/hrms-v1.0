# HRMS 事务 Agent 镜像
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY run.py .
COPY eval ./eval
COPY scripts ./scripts

# 8010 是 Agent 服务端口；HRMS 通过 HRMS_BASE_URL 指定
EXPOSE 8010
CMD ["python", "run.py"]
