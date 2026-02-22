# Portfolio Lab 部署指南

## 项目概述

投资组合实验室 - 基于 GCP 预计算 + 轻量服务器查询的金融分析平台

**技术栈**：
- 后端：FastAPI + PostgreSQL + Redis
- 前端：React + Vite + Zustand + Plotly.js
- 部署：Docker Compose
- 镜像仓库：DockerHub (fuzhouxing)

---

## 快速开始

### 1. 本地开发环境

#### 后端启动
```bash
# 安装依赖
pip install -r requirements.txt

# 启动 PostgreSQL 和 Redis（使用 Docker）
docker-compose up -d postgres redis

# 运行后端
cd app
uvicorn main:app --reload --port 8030
```

访问 API 文档：http://localhost:8030/api/v1/docs

#### 前端启动
```bash
cd frontend
npm install
npm run dev
```

访问前端：http://localhost:3000

---

## Docker 部署

### 2. 构建镜像

#### 后端镜像
```bash
docker build -f infra/docker/backend.Dockerfile -t fuzhouxing/portfolio-lab-backend:latest .
docker push fuzhouxing/portfolio-lab-backend:latest
```

#### 前端镜像
```bash
cd frontend
docker build -t fuzhouxing/portfolio-lab-frontend:latest .
docker push fuzhouxing/portfolio-lab-frontend:latest
```

### 3. 一键部署

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

**服务端口**：
- 后端 API：http://localhost:8030
- 前端界面：http://localhost:8032
- PostgreSQL：localhost:8031
- Redis：localhost:8033

---

## GCP 计算任务

### 4. 数据准备（Day 1-2）

#### 安装依赖
```bash
pip install yfinance pandas numpy scipy pyarrow
```

#### 获取历史数据
```bash
python jobs/scripts/00_fetch_yfinance.py --output data/raw_prices.parquet
```

**资产池**：SPY, QQQ, IWM, TLT, GLD, BTC, EEM, EFA, FXI, USO, DBA
**时间跨度**：2000-01-01 至 2025-12-31

#### 数据清洗
```bash
python jobs/scripts/01_clean_align_prices.py \
  --input data/raw_prices.parquet \
  --output data/clean_prices.parquet
```

### 5. 高性能计算（Day 3-7）

#### GCP 资源配置

**数据准备**：
```bash
gcloud compute instances create portfolio-data-prep \
  --machine-type=e2-standard-4 \
  --zone=us-central1-a \
  --image-family=debian-11 \
  --image-project=debian-cloud
```

**蒙特卡洛模拟**（最耗资源）：
```bash
gcloud compute instances create portfolio-monte-carlo \
  --machine-type=c2-standard-60 \
  --zone=us-central1-a \
  --preemptible \
  --image-family=debian-11 \
  --image-project=debian-cloud
```

**协方差计算**：
```bash
gcloud compute instances create portfolio-covariance \
  --machine-type=n2-highmem-16 \
  --zone=us-central1-a \
  --image-family=debian-11 \
  --image-project=debian-cloud
```

#### 计算任务清单

| 优先级 | 任务 | 脚本 | 预估时间 | 输出 |
|--------|------|------|----------|------|
| P0 | 数据获取 | `00_fetch_yfinance.py` | 2-4h | `raw_prices.parquet` |
| P0 | 数据清洗 | `01_clean_align_prices.py` | 2-4h | `clean_prices.parquet` |
| P0 | 滚动协方差 | `10_compute_rolling_cov.py` | 6-10h | `covariance_matrices_*.npz` |
| P0 | 蒙特卡洛 | `30_compute_monte_carlo.py` | 12-24h | `mc_quantiles.parquet` |
| P1 | 投资组合优化 | `20_compute_markowitz_bl_rp.py` | 8-14h | `portfolio_lookup_table.parquet` |
| P1 | 压力测试 | `40_compute_stress_tests.py` | 4-8h | `stress_test_results_*.json` |

### 6. 数据导入（Day 8）

#### 导出预计算结果
```bash
python jobs/scripts/50_export_artifacts.py \
  --input-dir data/ \
  --output-dir artifacts/ \
  --verify
```

#### 导入到 PostgreSQL
```bash
python jobs/scripts/60_load_postgres.py \
  --artifacts-dir artifacts/ \
  --postgres-dsn "postgresql://portfolio:portfolio@localhost:8031/portfolio_lab"
```

#### Redis 缓存预热
```bash
python jobs/scripts/70_cache_warmup.py \
  --redis-url "redis://localhost:8033/0" \
  --postgres-dsn "postgresql://portfolio:portfolio@localhost:8031/portfolio_lab"
```

---

## 性能测试

### 7. API 压测

#### 安装 wrk
```bash
# Ubuntu/Debian
sudo apt-get install wrk

# macOS
brew install wrk
```

#### 运行压测
```bash
# 健康检查端点
wrk -t4 -c100 -d30s --latency http://localhost:8030/api/v1/health/live

# 资产列表端点
wrk -t4 -c100 -d30s --latency http://localhost:8030/api/v1/meta/assets
```

**性能目标**：
- P95 延迟：< 500ms
- P99 延迟：< 800ms
- 错误率：< 0.5%

### 8. 前端性能

#### Bundle 分析
```bash
cd frontend
npm install --save-dev vite-plugin-visualizer
npm run build
```

**优化目标**：
- 首屏加载：< 2s
- Bundle 大小：< 500KB (gzipped)
- Plotly.js 动态导入

---

## 生产部署

### 9. 轻量服务器部署

#### 环境要求
- Docker 20.10+
- Docker Compose 2.0+
- 内存：4GB+
- 磁盘：20GB+

#### 部署步骤

1. **克隆项目**
```bash
git clone https://github.com/yourusername/portfolio-lab.git
cd portfolio-lab
```

2. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，设置数据库密码等
```

3. **启动服务**
```bash
docker-compose up -d
```

4. **验证部署**
```bash
# 检查服务状态
docker-compose ps

# 查看日志
docker-compose logs -f backend

# 测试 API
curl http://localhost:8030/api/v1/health/ready
```

5. **访问应用**
- 前端界面：http://your-server-ip:8032
- API 文档：http://your-server-ip:8030/api/v1/docs

---

## 监控与维护

### 10. 日志管理

#### 查看实时日志
```bash
# 所有服务
docker-compose logs -f

# 特定服务
docker-compose logs -f backend
docker-compose logs -f postgres
```

#### 日志持久化
```yaml
# docker-compose.yml 中添加
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 11. 数据备份

#### PostgreSQL 备份
```bash
# 备份
docker exec portfolio-lab-postgres pg_dump -U portfolio portfolio_lab > backup.sql

# 恢复
docker exec -i portfolio-lab-postgres psql -U portfolio portfolio_lab < backup.sql
```

#### Redis 持久化
```bash
# 手动保存
docker exec portfolio-lab-redis redis-cli SAVE

# 备份 RDB 文件
docker cp portfolio-lab-redis:/data/dump.rdb ./redis-backup.rdb
```

---

## 故障排查

### 12. 常见问题

#### 后端无法连接数据库
```bash
# 检查 PostgreSQL 是否运行
docker-compose ps postgres

# 检查连接字符串
docker-compose exec backend env | grep POSTGRES_DSN

# 测试连接
docker-compose exec postgres psql -U portfolio -d portfolio_lab -c "SELECT 1;"
```

#### Redis 连接失败
```bash
# 检查 Redis 是否运行
docker-compose ps redis

# 测试连接
docker-compose exec redis redis-cli ping
```

#### 前端无法访问后端 API
```bash
# 检查 Nginx 配置
docker-compose exec frontend cat /etc/nginx/conf.d/default.conf

# 检查网络连通性
docker-compose exec frontend ping backend
```

---

## 更新与升级

### 13. 镜像更新

#### 拉取最新镜像
```bash
docker-compose pull
```

#### 重启服务
```bash
docker-compose down
docker-compose up -d
```

#### 滚动更新（零停机）
```bash
# 更新后端
docker-compose up -d --no-deps --build backend

# 更新前端
docker-compose up -d --no-deps --build frontend
```

---

## 安全建议

### 14. 生产环境安全

1. **修改默认密码**
```yaml
# docker-compose.yml
environment:
  POSTGRES_PASSWORD: "your-strong-password"
```

2. **启用 HTTPS**
```bash
# 使用 Let's Encrypt
docker run -it --rm \
  -v /etc/letsencrypt:/etc/letsencrypt \
  certbot/certbot certonly --standalone \
  -d your-domain.com
```

3. **限制端口访问**
```yaml
# docker-compose.yml
ports:
  - "127.0.0.1:8031:5432"  # 仅本地访问
```

4. **API 限流**
```python
# app/main.py
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
```

---

## 联系与支持

- **项目仓库**：https://github.com/yourusername/portfolio-lab
- **Docker Hub**：https://hub.docker.com/u/fuzhouxing
- **问题反馈**：提交 GitHub Issue

---

## 附录

### A. 完整目录结构
```
portfolio-lab/
├── app/                    # 后端应用
│   ├── main.py
│   ├── core/
│   ├── api/v1/endpoints/
│   ├── services/
│   └── repositories/
├── frontend/               # 前端应用
│   ├── src/
│   ├── public/
│   ├── Dockerfile
│   └── nginx.conf
├── jobs/scripts/           # GCP 计算任务
│   ├── 00_fetch_yfinance.py
│   ├── 01_clean_align_prices.py
│   ├── 10_compute_rolling_cov.py
│   ├── 20_compute_markowitz_bl_rp.py
│   ├── 30_compute_monte_carlo.py
│   ├── 40_compute_stress_tests.py
│   ├── 50_export_artifacts.py
│   ├── 60_load_postgres.py
│   └── 70_cache_warmup.py
├── sql/                    # 数据库脚本
│   └── 001_init_portfolio_lab.sql
├── infra/docker/           # Docker 构建文件
│   ├── backend.Dockerfile
│   └── compute.Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

### B. 环境变量说明

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `APP_ENV` | `prod` | 应用环境（dev/prod） |
| `API_PREFIX` | `/api/v1` | API 路径前缀 |
| `POSTGRES_DSN` | - | PostgreSQL 连接字符串 |
| `REDIS_URL` | - | Redis 连接字符串 |
| `DATASET_VERSION` | `current` | 数据集版本 |
| `CACHE_DEFAULT_TTL_SECONDS` | `604800` | 缓存 TTL（7天） |

---

**版本**：v1.0.0
**更新日期**：2026-02-22
