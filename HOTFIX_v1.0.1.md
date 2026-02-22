# 紧急修复：v1.0.1 - 服务器部署问题

**日期**：2026-02-22
**版本**：v1.0.1
**严重性**：🔴 高（影响生产部署）

---

## 🐛 问题描述

### 症状
- 在服务器上通过域名访问时，四个图表均无内容
- 在本地 PC 运行 Docker 容器时，一切正常
- 浏览器控制台显示 API 请求失败

### 根本原因
前端代码硬编码了 `localhost` 作为 API 地址：

```typescript
// ❌ 错误的配置（v1.0.0）
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8030/api/v1';
```

这导致：
- **本地开发**：前端访问 `http://localhost:8030` → 正常工作
- **服务器部署**：前端访问 `http://localhost:8030` → 失败（服务器上没有监听 8030 端口）

---

## ✅ 修复方案

### 修改内容

将 API 地址改为**相对路径**，通过 Nginx 反向代理访问后端：

```typescript
// ✅ 正确的配置（v1.0.1）
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';
```

### 工作原理

```
用户浏览器
    ↓
https://your-domain.com/
    ↓
Nginx (前端容器 :80)
    ├─ / → 静态文件
    └─ /api/ → proxy_pass http://backend:8000/
              ↓
         后端容器 (FastAPI :8000)
```

**关键配置**（nginx.conf）：
```nginx
location /api/ {
    proxy_pass http://backend:8000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

---

## 📦 更新的镜像

### v1.0.1
- **镜像**：`fuzhouxing/portfolio-lab-frontend:v1.0.1`
- **Digest**：`sha256:ceb792773432c5013d4749db7f49b6955c69a16a6be40d4c737ae90df46c366d`
- **修复**：API 地址使用相对路径

### latest 标签
- 已更新为 v1.0.1
- 与 v1.0.1 完全相同

---

## 🚀 部署更新

### 方法 1：使用 docker-compose（推荐）

```bash
# 1. 更新 docker-compose.yml
# 将 frontend 镜像版本改为 v1.0.1

# 2. 拉取新镜像
docker-compose pull frontend

# 3. 重启前端服务
docker-compose up -d frontend
```

### 方法 2：手动更新

```bash
# 1. 停止旧容器
docker stop portfolio-lab-frontend
docker rm portfolio-lab-frontend

# 2. 拉取新镜像
docker pull fuzhouxing/portfolio-lab-frontend:v1.0.1

# 3. 启动新容器
docker run -d --name portfolio-lab-frontend \
  --network portfolio_net \
  -p 8032:80 \
  fuzhouxing/portfolio-lab-frontend:v1.0.1
```

### 方法 3：使用 latest 标签

```bash
# 拉取最新镜像
docker pull fuzhouxing/portfolio-lab-frontend:latest

# 重启服务
docker-compose up -d frontend
```

---

## ✅ 验证修复

### 1. 检查前端日志
```bash
docker-compose logs frontend
```

应该看到 Nginx 正常启动，没有错误。

### 2. 测试 API 访问
在浏览器控制台执行：
```javascript
fetch('/api/v1/meta/assets')
  .then(r => r.json())
  .then(console.log)
```

应该返回 11 个资产的列表。

### 3. 检查图表
访问前端页面，四个图表应该正常显示：
- ✅ Risk Metrics（风险指标）
- ✅ Efficient Frontier（有效前沿）
- ✅ Monte Carlo Simulation（蒙特卡洛模拟）
- ✅ Stress Test（压力测试）

---

## 📊 影响范围

### 受影响的版本
- ❌ v1.0.0 - 无法在服务器上正常工作

### 修复的版本
- ✅ v1.0.1 - 可以在任何环境正常工作
- ✅ latest - 已更新为 v1.0.1

### 后端镜像
- ✅ v1.0.0 - 无需更新，后端没有问题

---

## 🔍 为什么本地能工作？

本地开发时，前端和后端都在同一台机器上：
- 前端容器：`localhost:8032`
- 后端容器：`localhost:8030`

所以 `http://localhost:8030` 可以正常访问。

但在服务器上：
- 前端容器内部没有 8030 端口
- `localhost` 指向容器自己，而不是宿主机
- 必须通过 Docker 网络访问后端

---

## 📝 经验教训

### 1. 避免硬编码 localhost
❌ 错误：
```typescript
const API_URL = 'http://localhost:8030/api/v1';
```

✅ 正确：
```typescript
const API_URL = '/api/v1';  // 相对路径
```

### 2. 使用环境变量
```typescript
const API_URL = import.meta.env.VITE_API_URL || '/api/v1';
```

这样可以在不同环境使用不同配置：
- 开发环境：`VITE_API_URL=http://localhost:8030/api/v1`
- 生产环境：使用默认的相对路径

### 3. 测试多种部署场景
- ✅ 本地开发
- ✅ 本地 Docker
- ✅ 服务器部署
- ✅ 域名访问

---

## 🎯 后续改进

### 短期
- [x] 修复 API 地址硬编码问题
- [x] 推送 v1.0.1 镜像
- [x] 更新文档

### 中期
- [ ] 添加健康检查端点测试
- [ ] 添加前端环境变量文档
- [ ] 创建部署检查清单

### 长期
- [ ] 添加自动化测试
- [ ] 添加部署验证脚本
- [ ] 创建 CI/CD 流程

---

## 📞 支持

如果更新后仍有问题：

1. **检查 Nginx 配置**
   ```bash
   docker exec portfolio-lab-frontend cat /etc/nginx/conf.d/default.conf
   ```

2. **检查网络连接**
   ```bash
   docker exec portfolio-lab-frontend wget -O- http://backend:8000/api/v1/health/live
   ```

3. **查看浏览器控制台**
   - 打开开发者工具（F12）
   - 查看 Network 标签
   - 检查 API 请求是否成功

---

**修复时间**：2026-02-22 03:00
**修复者**：Claude Sonnet 4.5
**状态**：✅ 已修复并验证
