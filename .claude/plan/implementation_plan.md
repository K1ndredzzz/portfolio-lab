# Portfolio Lab 实施计划

## 项目概述

**目标**：构建投资组合实验室，利用 GCP 算力进行重计算，部署到轻量服务器提供查询服务。

**技术栈**：
- 后端：FastAPI + PostgreSQL + Redis
- 前端：React + Vite + Zustand + Plotly.js
- 部署：Docker Compose → DockerHub (fuzhouxing)
- 端口：8030(后端)、8031(PostgreSQL)、8032(前端)、8033(Redis)

**时间限制**：10天内完成 GCP 计算任务

---

## 阶段 1：项目初始化（Day 1）

### 1.1 后端项目结构
```
portfolio-lab/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── security.py
│   ├── api/v1/
│   │   ├── router.py
│   │   └── endpoints/
│   │       ├── health.py
│   │       ├── meta.py
│   │       ├── portfolios.py
│   │       └── risk.py
│   ├── schemas/
│   │   ├── common.py
│   │   ├── portfolio.py
│   │   └── risk.py
│   ├── services/
│   │   ├── query_service.py
│   │   ├── interpolation_service.py
│   │   └── cache_service.py
│   ├── repositories/
│   │   ├── asset_repo.py
│   │   ├── portfolio_repo.py
│   │   └── risk_repo.py
│   └── db/
│       └── session.py
├── jobs/scripts/
│   ├── 00_fetch_yfinance.py
│   ├── 01_clean_align_prices.py
│   ├── 10_compute_rolling_cov.py
│   ├── 20_compute_markowitz_bl_rp.py
│   ├── 30_compute_monte_carlo.py
│   ├── 40_compute_stress_tests.py
│   ├── 50_export_artifacts.py
│   ├── 60_load_postgres.py
│   └── 70_cache_warmup.py
├── sql/
│   └── 001_init_portfolio_lab.sql
├── infra/docker/
│   ├── backend.Dockerfile
│   └── compute.Dockerfile
├── docker-compose.yml
└── requirements.txt
```

### 1.2 前端项目结构
```
frontend/
├── src/
│   ├── assets/
│   ├── components/
│   │   ├── common/
│   │   ├── layout/
│   │   └── charts/
│   ├── features/
│   │   ├── portfolio/
│   │   ├── dashboard/
│   │   ├── simulation/
│   │   └── analysis/
│   ├── hooks/
│   ├── services/
│   ├── stores/
│   ├── types/
│   ├── utils/
│   ├── App.tsx
│   └── main.tsx
├── public/
├── nginx.conf
├── Dockerfile
├── package.json
└── vite.config.ts
```

---

## 阶段 2：数据库设计与初始化（Day 1）

### 2.1 核心表结构

**dataset_versions**：数据集版本管理
```sql
CREATE TABLE dataset_versions (
    dataset_id UUID PRIMARY KEY,
    version_tag TEXT NOT NULL UNIQUE,
    date_start DATE NOT NULL,
    date_end DATE NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN NOT NULL DEFAULT FALSE
);
```

**assets**：资产定义
```sql
CREATE TABLE assets (
    asset_id SMALLSERIAL PRIMARY KEY,
    ticker TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    asset_class TEXT NOT NULL
);
```

**portfolios**：组合权重
```sql
CREATE TABLE portfolios (
    portfolio_id BIGSERIAL PRIMARY KEY,
    weights_hash CHAR(64) NOT NULL UNIQUE,
    weights_vector DOUBLE PRECISION[] NOT NULL,
    weights_json JSONB NOT NULL
);
```

**portfolio_metrics**：风险指标
```sql
CREATE TABLE portfolio_metrics (
    metric_id BIGSERIAL PRIMARY KEY,
    dataset_id UUID NOT NULL REFERENCES dataset_versions(dataset_id),
    portfolio_id BIGINT NOT NULL REFERENCES portfolios(portfolio_id),
    model model_type NOT NULL,
    as_of_date DATE NOT NULL,
    horizon_months SMALLINT NOT NULL,
    expected_return_ann DOUBLE PRECISION NOT NULL,
    volatility_ann DOUBLE PRECISION NOT NULL,
    sharpe DOUBLE PRECISION NOT NULL,
    var95 DOUBLE PRECISION NOT NULL,
    cvar95 DOUBLE PRECISION NOT NULL,
    max_drawdown DOUBLE PRECISION NOT NULL
);
```

### 2.2 索引策略
```sql
CREATE INDEX idx_portfolio_metrics_lookup
ON portfolio_metrics (dataset_id, model, as_of_date, horizon_months, portfolio_id);

CREATE INDEX idx_portfolios_weights_hash
ON portfolios (weights_hash);
```

---

## 阶段 3：GCP 计算任务（Day 2-7）

### 3.1 数据准备（Day 2）
**脚本**：`00_fetch_yfinance.py`
- 资产池：SPY, QQQ, IWM, TLT, GLD, BTC, EEM, EFA, FXI, USO, DBA
- 时间跨度：2000-01-01 至 2025-12-31
- 输出：`raw_prices.parquet`

**脚本**：`01_clean_align_prices.py`
- 数据清洗与对齐
- 输出：`clean_prices.parquet`

### 3.2 高性能计算（Day 3-5）

**任务 1：滚动协方差矩阵**（`10_compute_rolling_cov.py`）
- 窗口：5年（1260个交易日）
- 频率：每月快照
- 方法：shrinkage covariance
- 输出：`covariance_matrices_*.npz`

**任务 2：蒙特卡洛模拟**（`30_compute_monte_carlo.py`）
- 路径数：5,000,000
- 覆盖：1000+种资产配比组合
- 每种组合：5000条路径
- 输出：分位数摘要（q01/q05/q25/q50/q75/q95/q99）
- 文件：`mc_quantiles.parquet`

**任务 3：投资组合优化**（`20_compute_markowitz_bl_rp.py`）
- Markowitz 有效前沿
- Black-Litterman 模型
- Risk Parity 组合
- 输出：`portfolio_lookup_table.parquet`

**任务 4：压力测试**（`40_compute_stress_tests.py`）
- 场景：2008金融危机、2020 COVID、2022加息周期
- 指标：最大回撤、恢复时间
- 输出：`stress_test_results_*.json`

### 3.3 GCP 资源配置
- 数据准备：`e2-standard-4`（2-4小时）
- 协方差计算：`n2-highmem-16`（6-10小时）
- 蒙特卡洛：`c2-standard-60`（12-24小时，使用 preemptible）
- 优化与压力测试：`n2-highmem-32`（8-14小时）

---

## 阶段 4：后端 API 开发（Day 6-7）

### 4.1 核心 API 端点

**POST /api/v1/portfolios/quote**
```python
@router.post("/quote")
async def get_portfolio_quote(request: PortfolioQuoteRequest):
    # 1. 归一化权重
    # 2. 计算 weights_hash
    # 3. Redis 查询（read-through）
    # 4. PostgreSQL 回退
    # 5. 返回风险指标
    pass
```

**GET /api/v1/portfolios/frontier**
```python
@router.get("/frontier")
async def get_efficient_frontier(
    model: str,
    as_of_date: date,
    horizon_months: int
):
    # 查询预计算的有效前沿点
    pass
```

**POST /api/v1/risk/stress**
```python
@router.post("/stress")
async def get_stress_test(request: StressTestRequest):
    # 查询历史危机场景下的组合表现
    pass
```

**POST /api/v1/risk/monte-carlo**
```python
@router.post("/monte-carlo")
async def get_monte_carlo(request: MonteCarloRequest):
    # 返回分位数摘要
    pass
```

### 4.2 Redis 缓存策略
- 键格式：`pl:v1:{dataset_version}:{model}:{as_of}:{horizon}:{weights_hash}`
- TTL：7天（quote/stress）、24小时（frontier）
- 预热：加载常见组合（等权、60/40、Risk Parity）

### 4.3 性能目标
- P95 延迟：< 500ms
- P99 延迟：< 800ms
- 缓存命中率：> 80%

---

## 阶段 5：前端开发（Day 6-8）

### 5.1 状态管理（Zustand）

**PortfolioStore**
```typescript
interface PortfolioState {
  assets: Asset[];
  metrics: RiskMetrics | null;
  isLoading: boolean;

  addAsset: (ticker: string) => void;
  updateWeight: (ticker: string, weight: number) => void;
  fetchMetrics: () => Promise<void>;
}
```

### 5.2 核心组件

**PortfolioBuilder**
- 资产搜索（Autocomplete）
- 权重滑块（0-100%）
- 归一化按钮

**RiskDashboard**
- KPI 卡片：VaR、CVaR、Sharpe、Sortino、最大回撤
- 实时更新（防抖 500ms）

**EfficientFrontierChart**（Plotly.js）
```javascript
{
  data: [
    { x: risks, y: returns, mode: 'lines', name: 'Efficient Frontier' },
    { x: [currentRisk], y: [currentReturn], mode: 'markers', name: 'Your Portfolio' }
  ]
}
```

**MonteCarloChart**（Plotly.js）
```javascript
{
  data: [
    { x: dates, y: q05, name: '5th Percentile' },
    { x: dates, y: q50, name: 'Median' },
    { x: dates, y: q95, name: '95th Percentile' }
  ]
}
```

**StressTestChart**（Plotly.js）
```javascript
{
  data: [{
    x: ['2008 Crisis', 'COVID-19', '2022 Rates'],
    y: [-45, -30, -15],
    type: 'bar'
  }]
}
```

### 5.3 API 调用策略
- 防抖：500ms（滑块拖动）
- 乐观 UI：立即更新权重显示
- 错误处理：Toast 提示 + 重试按钮
- Loading 状态：图表角落的 spinner（非全屏）

---

## 阶段 6：Docker 构建与部署（Day 8-9）

### 6.1 后端 Dockerfile
```dockerfile
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

FROM python:3.11-slim AS runtime
COPY --from=builder /opt/venv /opt/venv
COPY app /app/app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 6.2 前端 Dockerfile
```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile
COPY . .
RUN yarn build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

### 6.3 Docker Compose
```yaml
services:
  backend:
    image: fuzhouxing/portfolio-lab-backend:latest
    ports: ["8030:8000"]
    environment:
      POSTGRES_DSN: "postgresql://portfolio:portfolio@postgres:5432/portfolio_lab"
      REDIS_URL: "redis://redis:6379/0"

  frontend:
    image: fuzhouxing/portfolio-lab-frontend:latest
    ports: ["8032:80"]

  postgres:
    image: postgres:15-alpine
    ports: ["8031:5432"]
    volumes: ["./data:/var/lib/postgresql/data"]

  redis:
    image: redis:7-alpine
    ports: ["8033:6379"]
```

### 6.4 部署流程
1. 构建镜像：`docker build -t fuzhouxing/portfolio-lab-backend:latest .`
2. 推送到 DockerHub：`docker push fuzhouxing/portfolio-lab-backend:latest`
3. 在轻量服务器上：`docker-compose up -d`

---

## 阶段 7：测试与优化（Day 9-10）

### 7.1 API 压测
```bash
# 使用 wrk 或 locust 进行压测
wrk -t4 -c100 -d30s --latency http://localhost:8030/api/v1/portfolios/quote
```

**目标**：
- P95 < 500ms
- P99 < 800ms
- 错误率 < 0.5%

### 7.2 前端性能优化
- Bundle 分析：`vite-plugin-visualizer`
- Plotly.js 动态导入：`React.lazy(() => import('./charts/EfficientFrontier'))`
- 图片优化：WebP 格式
- Gzip 压缩：Nginx 配置

### 7.3 数据完整性验证
```bash
# 验证预计算结果
python jobs/scripts/50_export_artifacts.py --verify
```

---

## 验收标准

### 功能完整性
- ✅ 组合构建器（拖拽 + 滑块）
- ✅ 实时风险仪表盘（<0.5s 响应）
- ✅ 有效前沿可视化
- ✅ 蒙特卡洛模拟（分位数）
- ✅ 压力测试（历史危机场景）

### 性能指标
- ✅ API P95 延迟 < 500ms
- ✅ 前端首屏加载 < 2s
- ✅ Docker 镜像 < 200MB（后端 + 前端）

### 部署要求
- ✅ Docker Compose 一键部署
- ✅ 镜像推送到 DockerHub (fuzhouxing)
- ✅ 端口配置：8030-8033

### 数据质量
- ✅ 预计算结果 checksum 验证
- ✅ 数据库索引优化
- ✅ Redis 缓存预热

---

## 风险与应对

### 风险 1：GCP 时间不足
**应对**：分层交付（MVP → 全量）
- MVP：核心资产池（SPY/QQQ/TLT/GLD）+ 基础指标
- 全量：完整资产池 + 高级指标

### 风险 2：数据质量问题
**应对**：增加数据校验与异常剔除
- 缺失值处理：前向填充 + 线性插值
- 异常值检测：3σ 规则

### 风险 3：模型不稳定
**应对**：引入 shrinkage covariance
- Ledoit-Wolf shrinkage
- 参数约束（权重上下限）

### 风险 4：性能波动
**应对**：严格禁止线上重计算
- 只允许查询预计算结果
- API 限流（100 req/min）

---

## 下一步行动

1. **用户确认**：批准实施计划
2. **项目初始化**：创建目录结构
3. **数据库初始化**：执行 SQL 脚本
4. **GCP 计算任务**：启动数据准备脚本
5. **后端开发**：实现核心 API 端点
6. **前端开发**：构建组合构建器
7. **集成测试**：端到端测试
8. **Docker 构建**：推送镜像到 DockerHub
9. **部署上线**：轻量服务器部署
10. **监控与优化**：性能监控与调优
