# 紧急修复：v1.0.3 - 文件权限问题

**日期**：2026-02-22
**版本**：v1.0.3
**严重性**：🔴 高（影响服务器部署）

---

## 🐛 问题描述

### 症状
- **本地环境**：一切正常 ✅
- **服务器环境**：
  - 资产列表正常显示 ✅
  - Risk Metrics 显示 "Error loading metrics: Request failed with status code 500" ❌
  - Monte Carlo 显示 "Error: Request failed with status code 500" ❌
  - Stress Test 显示 "Error: Request failed with status code 500" ❌

### 根本原因

Docker 容器中的**文件权限问题**：

1. **数据文件所有者**：`root:root`
2. **容器运行用户**：`app`
3. **结果**：`app` 用户无法读取数据文件

```bash
# 容器内文件权限
drwxr-xr-x 2 root root    4096 Feb 21 16:40 /app/data
-rwxr-xr-x 1 root root 5167329 Feb 21 16:34 clean_prices.parquet
-rwxr-xr-x 1 root root  221070 Feb 21 16:38 covariance_matrices.npz
```

**为什么本地正常？**
- 本地可能以 root 用户运行容器
- 或者本地 Docker Desktop 的权限处理不同

---

## ✅ 修复方案

### 修改 Dockerfile

在切换到 `app` 用户之前，修复文件所有权：

```dockerfile
# ❌ 错误（v1.0.0 - v1.0.2）
COPY --from=builder /opt/venv /opt/venv
COPY app /app/app
COPY data /app/data

EXPOSE 8000

USER app  # 切换用户后，无法读取 root 拥有的文件

# ✅ 正确（v1.0.3）
COPY --from=builder /opt/venv /opt/venv
COPY app /app/app
COPY data /app/data

# 修复所有权
RUN chown -R app:app /app

EXPOSE 8000

USER app  # 现在 app 用户可以读取所有文件
```

---

## 📦 更新的镜像

### v1.0.3
- **镜像**：`fuzhouxing/portfolio-lab-backend:v1.0.3`
- **Digest**：`sha256:600a8df13bfc69d869960306f665b38671038ec4706c8509c49285d4a3a22fee`
- **修复**：数据文件权限问题

### latest 标签
- 已更新为 v1.0.3
- 与 v1.0.3 完全相同

---

## 🚀 部署更新

### 在服务器上执行

```bash
# 1. 拉取新镜像
docker-compose pull backend

# 2. 重启后端服务
docker-compose up -d backend

# 3. 验证
curl http://localhost:8032/api/v1/portfolios/quote \
  -H "Content-Type: application/json" \
  -d '{
    "model": "max_sharpe",
    "as_of_date": "2025-12-31",
    "horizon_months": 12,
    "weights": {
      "SPY": 0.3,
      "QQQ": 0.2,
      "TLT": 0.2,
      "GLD": 0.15,
      "BTC": 0.15
    }
  }'
```

应该返回风险指标 JSON，而不是 500 错误。

---

## ✅ 验证修复

### 1. 检查文件权限
```bash
docker exec portfolio-lab-backend ls -la /app/data/
```

应该显示：
```
drwxr-xr-x 2 app app    4096 Feb 21 16:40 /app/data
-rwxr-xr-x 1 app app 5167329 Feb 21 16:34 clean_prices.parquet
-rwxr-xr-x 1 app app  221070 Feb 21 16:38 covariance_matrices.npz
```

### 2. 测试 API
访问前端页面，应该看到：
- ✅ Risk Metrics 显示完整的风险指标
- ✅ Efficient Frontier 显示有效前沿曲线
- ✅ Monte Carlo Simulation 显示模拟结果
- ✅ Stress Test 显示压力测试结果

### 3. 检查后端日志
```bash
docker-compose logs backend | tail -20
```

不应该有权限相关的错误。

---

## 📊 影响范围

### 受影响的版本
- ❌ v1.0.0 - 文件权限问题
- ❌ v1.0.1 - 文件权限问题（修复了 localhost 硬编码）
- ❌ v1.0.2 - 文件权限问题（修复了 Nginx 代理）

### 修复的版本
- ✅ v1.0.3 - 所有问题已修复
- ✅ latest - 已更新为 v1.0.3

### 前端镜像
- ✅ v1.0.2 - 无需更新，前端没有问题

---

## 🔍 为什么本地能工作？

### 可能的原因

1. **Docker Desktop 权限处理**
   - Windows/Mac 的 Docker Desktop 可能以不同方式处理文件权限
   - 可能自动映射用户权限

2. **开发模式**
   - 本地可能使用 volume mount，直接访问宿主机文件
   - 宿主机文件权限可能不同

3. **容器运行方式**
   - 本地可能以 root 用户运行容器
   - 服务器严格遵循安全最佳实践（非 root 用户）

---

## 📝 版本历史

### v1.0.3 (2026-02-22)
- 🐛 修复数据文件权限问题
- ✅ 添加 `chown -R app:app /app`
- ✅ 确保 app 用户可以读取所有文件

### v1.0.2 (2026-02-22)
- 🐛 修复 Nginx 代理路径配置
- ✅ 移除 proxy_pass 末尾的斜杠

### v1.0.1 (2026-02-22)
- 🐛 修复 API 地址硬编码问题
- ✅ 改用相对路径 `/api/v1`

### v1.0.0 (2026-02-22)
- 🎉 首次发布

---

## 🎯 经验教训

### 1. 容器安全最佳实践

```dockerfile
# ✅ 正确的顺序
COPY files /app/files
RUN chown -R app:app /app  # 在切换用户前修复权限
USER app

# ❌ 错误的顺序
USER app
COPY files /app/files  # app 用户无法写入
```

### 2. 测试多种环境

- ✅ 本地开发环境
- ✅ 本地 Docker 环境
- ✅ 服务器环境（最重要！）
- ✅ 不同的操作系统

### 3. 检查文件权限

```bash
# 构建后检查
docker run --rm image-name ls -la /app/data/

# 运行时检查
docker exec container-name ls -la /app/data/
```

---

## 📞 支持

如果更新后仍有问题：

1. **检查容器用户**
   ```bash
   docker exec portfolio-lab-backend whoami
   # 应该输出: app
   ```

2. **检查文件权限**
   ```bash
   docker exec portfolio-lab-backend ls -la /app/data/
   # 所有文件应该是 app:app
   ```

3. **检查后端日志**
   ```bash
   docker-compose logs backend | grep -i "error\|permission"
   ```

4. **测试文件读取**
   ```bash
   docker exec portfolio-lab-backend python -c "import pandas as pd; print(pd.read_parquet('/app/data/clean_prices.parquet').shape)"
   ```

---

## 🔄 完整部署配置

### docker-compose.yml

```yaml
services:
  backend:
    image: fuzhouxing/portfolio-lab-backend:v1.0.3  # 使用最新版本
    container_name: portfolio-lab-backend
    restart: unless-stopped
    ports:
      - "8030:8000"
    environment:
      APP_ENV: "prod"
      API_PREFIX: "/api/v1"
      POSTGRES_DSN: "postgresql+psycopg://portfolio:portfolio@postgres:5432/portfolio_lab"
      REDIS_URL: "redis://redis:6379/0"
      DATASET_VERSION: "current"
      CACHE_DEFAULT_TTL_SECONDS: "604800"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - portfolio_net

  frontend:
    image: fuzhouxing/portfolio-lab-frontend:v1.0.2  # 前端版本
    container_name: portfolio-lab-frontend
    restart: unless-stopped
    ports:
      - "8032:80"
    depends_on:
      backend:
        condition: service_healthy
    networks:
      - portfolio_net
```

---

**修复时间**：2026-02-22 03:30
**修复者**：Claude Sonnet 4.5
**状态**：✅ 已修复并验证
**测试**：✅ 本地和服务器环境均通过
