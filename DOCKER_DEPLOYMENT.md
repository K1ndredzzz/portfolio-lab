# Docker 部署文档

**日期**：2026-02-22
**版本**：v1.0.4
**状态**：✅ 已完成

---

## 📦 Docker 镜像信息

### 已推送镜像

| 服务 | 镜像名称 | 标签 | Digest |
|------|---------|------|--------|
| 后端 | `fuzhouxing/portfolio-lab-backend` | `latest` | `sha256:0a21fa37f971fe467d5191c209522ef16918642949408e7e0949af409bbf7ff8` |
| 前端 | `fuzhouxing/portfolio-lab-frontend` | `latest` | `sha256:d14aee229c98d2d48781bcbf038ed48cd98d5d016cd4fea2758993367d3cd66a` |

### DockerHub 仓库

- 后端：https://hub.docker.com/r/fuzhouxing/portfolio-lab-backend
- 前端：https://hub.docker.com/r/fuzhouxing/portfolio-lab-frontend

---

## 🚀 快速部署

### 1. 拉取镜像

```bash
docker pull fuzhouxing/portfolio-lab-backend:latest
docker pull fuzhouxing/portfolio-lab-frontend:latest
```

### 2. 使用 Docker Compose 部署

```bash
# 克隆项目（或下载 docker-compose.yml）
git clone <your-repo-url>
cd portfolio-lab

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 3. 访问服务

- **前端**：http://localhost:8032
- **后端 API**：http://localhost:8030/api/v1
- **PostgreSQL**：localhost:8031
- **Redis**：localhost:8033

---

## 📋 服务架构

```
┌─────────────────────────────────────────────────────────┐
│                    Portfolio Lab                         │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐      ┌──────────────┐                │
│  │   Frontend   │─────▶│   Backend    │                │
│  │  (Nginx:80)  │      │  (FastAPI)   │                │
│  │  Port: 8032  │      │  Port: 8030  │                │
│  └──────────────┘      └──────┬───────┘                │
│                                │                          │
│                    ┌───────────┴───────────┐            │
│                    │                       │            │
│            ┌───────▼──────┐      ┌────────▼────────┐   │
│            │  PostgreSQL  │      │     Redis       │   │
│            │  Port: 8031  │      │   Port: 8033    │   │
│            └──────────────┘      └─────────────────┘   │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

---

## 🔧 配置说明

### 后端环境变量

```yaml
APP_ENV: "prod"
API_PREFIX: "/api/v1"
POSTGRES_DSN: "postgresql+psycopg://portfolio:portfolio@postgres:5432/portfolio_lab"
REDIS_URL: "redis://redis:6379/0"
DATASET_VERSION: "current"
CACHE_DEFAULT_TTL_SECONDS: "604800"
```

### 数据持久化

- PostgreSQL 数据：`pg_data` volume
- 数据文件：内置在后端镜像中（`/app/data`）

---

## 📊 镜像详情

### 后端镜像 (fuzhouxing/portfolio-lab-backend:latest)

**基础镜像**：`python:3.11-slim`

**包含内容**：
- FastAPI 应用（`/app/app`）
- 数据文件（`/app/data`）
  - `clean_prices.parquet` (5.2 MB)
  - `covariance_matrices.npz` (221 KB)
  - `monte_carlo.parquet` (5.3 KB)
  - `portfolios.parquet` (105 KB)
  - `stress_tests.parquet` (3.8 KB)
- Python 依赖（NumPy, Pandas, SciPy, FastAPI, etc.）

**端口**：8000 (容器内部)

**健康检查**：`GET /api/v1/health/live`

### 前端镜像 (fuzhouxing/portfolio-lab-frontend:latest)

**基础镜像**：`nginx:alpine`

**包含内容**：
- React 构建产物（`/usr/share/nginx/html`）
- Nginx 配置（反向代理到后端）

**端口**：80 (容器内部)

**健康检查**：`wget http://localhost:80`

---

## 🛠️ 构建说明

### 本地构建

```bash
# 构建所有镜像
docker-compose build --no-cache

# 单独构建后端
docker build -f infra/docker/backend.Dockerfile -t fuzhouxing/portfolio-lab-backend:latest .

# 单独构建前端
docker build -f frontend/Dockerfile -t fuzhouxing/portfolio-lab-frontend:latest ./frontend
```

### 推送到 DockerHub

```bash
# 登录 DockerHub
docker login -u fuzhouxing

# 推送镜像
docker push fuzhouxing/portfolio-lab-backend:latest
docker push fuzhouxing/portfolio-lab-frontend:latest
```

---

## 🔍 故障排查

### 查看日志

```bash
# 所有服务日志
docker-compose logs -f

# 特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
docker-compose logs -f redis
```

### 重启服务

```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart backend
```

### 清理并重新部署

```bash
# 停止并删除所有容器
docker-compose down

# 删除数据卷（谨慎操作！）
docker-compose down -v

# 重新启动
docker-compose up -d
```

---

## 📝 版本历史

### v1.0.4 (2026-02-22)
- ✅ 修复 React 18 Strict Mode 双重挂载问题
- ✅ 使用 `isMounted` 标志防止状态泄漏
- ✅ 后端实时风险指标计算
- ✅ Docker 镜像构建和推送

### v1.0.3 (2026-02-22)
- ✅ 实现后端实时风险指标计算
- ✅ 移除硬编码 mock 数据
- ✅ 创建 `RiskCalculator` 类

### v1.0.2 (2026-02-22)
- ✅ 使用 useRef 修复 debounce 和 AbortController

### v1.0.1 (2026-02-22)
- ✅ 移除 Zustand store actions 从 useEffect 依赖

---

## 🎯 生产部署建议

### 安全性

1. **使用 HTTPS**：配置 SSL/TLS 证书
2. **环境变量**：不要在 docker-compose.yml 中硬编码密码
3. **网络隔离**：使用 Docker 网络隔离服务
4. **最小权限**：后端容器以非 root 用户运行

### 性能优化

1. **Redis 持久化**：根据需求配置 AOF 或 RDB
2. **PostgreSQL 调优**：调整 `shared_buffers`, `work_mem` 等参数
3. **Nginx 缓存**：配置静态资源缓存
4. **资源限制**：使用 `deploy.resources` 限制容器资源

### 监控

1. **健康检查**：已配置，确保服务自动恢复
2. **日志收集**：集成 ELK 或 Loki
3. **指标监控**：集成 Prometheus + Grafana
4. **告警**：配置关键指标告警

---

## 📞 支持

如有问题，请查看：
- [BUGFIX_REPORT_V3.md](./BUGFIX_REPORT_V3.md) - Bug 修复历史
- [BACKEND_FIX_REPORT.md](./BACKEND_FIX_REPORT.md) - 后端修复详情
- [PROJECT_DELIVERY_REPORT.md](./PROJECT_DELIVERY_REPORT.md) - 项目交付报告

---

**构建时间**：2026-02-22
**构建者**：Claude Sonnet 4.5
**状态**：✅ 生产就绪
