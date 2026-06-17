# 06 — Docker 基础设施规格

## 6.1 概述

所有服务通过 Docker Compose 统一编排，实现一键部署。包括 API 服务、前端、数据库、缓存、向量数据库、监控栈和沙箱环境。

## 6.2 服务清单

| 服务 | 镜像 | 端口 | 用途 |
|------|------|------|------|
| api | python:3.12-slim | 8000 | FastAPI 后端 |
| frontend | nginx:alpine | 3000 | Vue 3 前端 + Nginx 反向代理 |
| redis | redis/redis-stack | 6379 | 短期记忆 + 会话缓存 + 消息队列 |
| api_data | - | - | 持久化数据卷（会话、消息、技能、MCP配置） |
| milvus | milvusdb/milvus | 19530 | 向量数据库（可选生产） |
| etcd | quay.io/coreos/etcd | 2379 | Milvus 依赖 |
| minio | minio/minio | 9001 | Milvus 依赖 |
| prometheus | prom/prometheus | 9090 | 指标采集 |
| grafana | grafana/grafana | 3001 | 可视化监控 |
| sandbox | python:3.12-slim | - | 工具执行隔离环境 |

## 6.3 Docker Compose 配置

```yaml
# docker/docker-compose.yml
version: '3.8'

services:
  # ========== FastAPI 后端 ==========
  api:
    build:
      context: ..
      dockerfile: docker/Dockerfile.api
    container_name: cs599-api
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql+asyncpg://agent:agent@postgres:5432/agent_db
      - CHROMA_HOST=chromadb
      - CHROMA_PORT=8000
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - DEEPSEEK_BASE_URL=${DEEPSEEK_BASE_URL:-https://api.deepseek.com}
    volumes:
      - ../src:/app/src
      - api_data:/app/data
    depends_on:
      redis:
        condition: service_healthy
      postgres:
        condition: service_healthy
    networks:
      - cs599-net
    restart: unless-stopped

  # ========== 前端 ==========
  frontend:
    build:
      context: ../frontend
      dockerfile: ../docker/Dockerfile.frontend
    container_name: cs599-frontend
    ports:
      - "3000:80"
    depends_on:
      - api
    networks:
      - cs599-net
    restart: unless-stopped

  # ========== Redis (短期记忆) ==========
  redis:
    image: redis/redis-stack:7.4.0-v2
    container_name: cs599-redis
    ports:
      - "6379:6379"
      - "8002:8001"   # RedisInsight
    volumes:
      - redis_data:/data
      - ./config/redis.conf:/usr/local/etc/redis/redis.conf
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - cs599-net
    restart: unless-stopped

  # ========== Prometheus (指标采集) ==========
  prometheus:
    image: prom/prometheus:latest
    container_name: cs599-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - cs599-net
    restart: unless-stopped

  # ========== Grafana (可视化) ==========
  grafana:
    image: grafana/grafana:latest
    container_name: cs599-grafana
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./config/grafana-dashboards:/etc/grafana/provisioning/dashboards
    depends_on:
      - prometheus
    networks:
      - cs599-net
    restart: unless-stopped

  # ========== 工具执行沙箱 ==========
  sandbox:
    image: python:3.12-slim
    container_name: cs599-sandbox
    volumes:
      - sandbox_data:/workspace
    command: tail -f /dev/null  # 保持运行
    networks:
      - cs599-net
    security_opt:
      - no-new-privileges:true
    read_only: false
    mem_limit: 512m
    cpu_shares: 512

volumes:
  redis_data:
  api_data:
  prometheus_data:
  grafana_data:

networks:
  cs599-net:
    driver: bridge
```

## 6.4 Dockerfile

### 6.4.1 API Dockerfile

```dockerfile
# docker/Dockerfile.api
FROM python:3.12-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 源代码
COPY src/ ./src/

# 启动
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### 6.4.2 前端 Dockerfile

```dockerfile
# docker/Dockerfile.frontend
FROM node:20-alpine AS builder

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY docker/config/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## 6.5 Nginx 配置

```nginx
# docker/config/nginx.conf
server {
    listen 80;
    server_name localhost;

    # 前端静态文件
    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理
    location /api/ {
        proxy_pass http://api:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;   # SSE 长连接
        proxy_buffering off;       # 流式输出禁用缓冲
    }
}
```

## 6.6 健康检查

```python
# 所有服务的健康检查端点
@app.get("/health")
async def health_check():
    checks = {
        "api": "ok",
        "redis": await check_redis(),
        "postgres": await check_postgres(),
        "chromadb": await check_chromadb(),
        "deepseek": await check_deepseek(),
    }
    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503
    return JSONResponse(content=checks, status_code=status_code)
```

## 6.7 启动脚本

```bash
#!/bin/bash
# start.sh

# 检查环境变量
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "Error: DEEPSEEK_API_KEY not set"
    exit 1
fi

# 创建 .env 文件
cat > .env << EOF
DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
DEEPSEEK_BASE_URL=${DEEPSEEK_BASE_URL:-https://api.deepseek.com}
EOF

# 启动所有服务
docker compose -f docker/docker-compose.yml up -d

# 等待健康检查
echo "Waiting for services..."
until curl -s http://localhost:8000/health | grep -q '"api":"ok"'; do
    sleep 2
done

echo "All services ready!"
echo "Frontend: http://localhost:3000"
echo "API Docs: http://localhost:8000/docs"
echo "Grafana: http://localhost:3001"
```

## 6.8 Redis 配置

```conf
# docker/config/redis.conf
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

## 6.9 PostgreSQL 初始化

```sql
-- docker/config/init.sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS memory_facts (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    memory_type VARCHAR(32) NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1536),
    importance FLOAT DEFAULT 0.5,
    access_count INT DEFAULT 0,
    last_accessed TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memory_user ON memory_facts(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_type ON memory_facts(memory_type);
```

## 6.10 Prometheus 配置

```yaml
# docker/config/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'api'
    static_configs:
      - targets: ['api:8000']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']
```

## 6.11 实现文件清单

| 文件 | 职责 |
|------|------|
| `docker/docker-compose.yml` | 服务编排 |
| `docker/Dockerfile.api` | API 镜像 |
| `docker/Dockerfile.frontend` | 前端镜像 |
| `docker/config/nginx.conf` | Nginx 配置 |
| `docker/config/redis.conf` | Redis 配置 |
| `docker/config/init.sql` | PostgreSQL 初始化 |
| `docker/config/prometheus.yml` | Prometheus 配置 |
| `start.sh` | 一键启动脚本 |
