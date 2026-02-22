# 紧急修复：v1.0.2 - Nginx 代理路径问题

**日期**：2026-02-22
**版本**：v1.0.2
**严重性**：🔴 高（影响所有部署）

---

## 🐛 问题描述

### 症状
- 前端显示 "Error: Request failed with status code 404"
- 没有任何资产显示
- 四个图表均未加载
- 浏览器控制台显示 API 请求返回 404

### 根本原因

Nginx 配置中 `proxy_pass` 末尾多了一个斜杠：

```nginx
# ❌ 错误的配置（v1.0.1）
location /api/ {
    proxy_pass http://backend:8000/;  # 末尾的斜杠导致路径被截断
}
```

**问题分析**：

当请求 `/api/v1/meta/assets` 时：
1. Nginx 匹配 `location /api/`
2. 移除匹配的 `/api/` 部分
3. 剩余路径：`v1/meta/assets`
4. 因为 `proxy_pass` 末尾有 `/`，最终请求：`http://backend:8000/v1/meta/assets`
5. 但后端期望的路径是：`http://backend:8000/api/v1/meta/assets`
6. 结果：404 Not Found

---

## ✅ 修复方案

### 修改内容

移除 `proxy_pass` 末尾的斜杠：

```nginx
# ✅ 正确的配置（v1.0.2）
location /api/ {
    proxy_pass http://backend:8000;  # 不要末尾的斜杠
}
```

**工作原理**：

现在当请求 `/api/v1/meta/assets` 时：
1. Nginx 匹配 `location /api/`
2. 因为 `proxy_pass` 末尾没有 `/`，完整路径被保留
3. 最终请求：`http://backend:8000/api/v1/meta/assets` ✅
4. 后端正确响应

---

## 📦 更新的镜像

### v1.0.2
- **镜像**：`fuzhouxing/portfolio-lab-frontend:v1.0.2`
- **Digest**：`sha256:a539679c92a532fe057fe7f77b71fd3143081e0960cc7779b8f250e5b2a8af1e`
- **修复**：Nginx 代理路径配置

### latest 标签
- 已更新为 v1.0.2
- 与 v1.0.2 完全相同

---

## 🚀 部署更新

### 在服务器上执行

```bash
# 1. 拉取新镜像
docker-compose pull frontend

# 2. 重启前端服务
docker-compose up -d frontend

# 3. 验证
curl http://localhost:8032/api/v1/meta/assets
```

应该返回 11 个资产的 JSON 数据。

---

## ✅ 验证修复

### 1. 测试 API 访问
```bash
# 通过前端 Nginx 访问
curl http://localhost:8032/api/v1/meta/assets

# 应该返回资产列表，而不是 404
```

### 2. 检查前端页面
访问前端页面，应该看到：
- ✅ 11 个资产显示在左侧
- ✅ Risk Metrics 显示风险指标
- ✅ Efficient Frontier 显示有效前沿
- ✅ Monte Carlo Simulation 显示模拟结果
- ✅ Stress Test 显示压力测试结果

### 3. 检查浏览器控制台
- 打开开发者工具（F12）
- Network 标签应该显示所有 API 请求成功（200 OK）
- 不应该有 404 错误

---

## 📊 影响范围

### 受影响的版本
- ❌ v1.0.0 - localhost 硬编码问题
- ❌ v1.0.1 - Nginx 代理路径问题

### 修复的版本
- ✅ v1.0.2 - 所有问题已修复
- ✅ latest - 已更新为 v1.0.2

### 后端镜像
- ✅ v1.0.0 - 无需更新，后端没有问题

---

## 🔍 Nginx proxy_pass 规则

### 规则说明

| proxy_pass 配置 | 请求路径 | 实际转发路径 |
|----------------|---------|-------------|
| `http://backend:8000` | `/api/v1/meta/assets` | `http://backend:8000/api/v1/meta/assets` ✅ |
| `http://backend:8000/` | `/api/v1/meta/assets` | `http://backend:8000/v1/meta/assets` ❌ |
| `http://backend:8000/api` | `/api/v1/meta/assets` | `http://backend:8000/apiv1/meta/assets` ❌ |

### 最佳实践

```nginx
# ✅ 推荐：保留完整路径
location /api/ {
    proxy_pass http://backend:8000;
}

# ❌ 避免：末尾斜杠会截断路径
location /api/ {
    proxy_pass http://backend:8000/;
}

# ✅ 如果需要重写路径
location /api/ {
    rewrite ^/api/(.*)$ /$1 break;
    proxy_pass http://backend:8000;
}
```

---

## 📝 版本历史

### v1.0.2 (2026-02-22)
- 🐛 修复 Nginx 代理路径配置
- ✅ 移除 proxy_pass 末尾的斜杠
- ✅ API 请求现在正确转发到后端

### v1.0.1 (2026-02-22)
- 🐛 修复 API 地址硬编码问题
- ✅ 改用相对路径 `/api/v1`
- ❌ Nginx 代理配置错误（本版本修复）

### v1.0.0 (2026-02-22)
- 🎉 首次发布
- ❌ API 地址硬编码 localhost（v1.0.1 修复）

---

## 🎯 经验教训

### 1. Nginx proxy_pass 末尾斜杠很重要

```nginx
# 这两个配置行为完全不同！
proxy_pass http://backend:8000;   # 保留完整路径
proxy_pass http://backend:8000/;  # 截断匹配的路径
```

### 2. 测试所有路径

在修改 Nginx 配置后，应该测试：
- ✅ 根路径：`/`
- ✅ API 路径：`/api/v1/meta/assets`
- ✅ 嵌套路径：`/api/v1/risk/monte-carlo`

### 3. 使用 curl 验证

```bash
# 测试前端代理
curl http://localhost:8032/api/v1/meta/assets

# 测试后端直接访问
curl http://localhost:8030/api/v1/meta/assets

# 两者应该返回相同的结果
```

---

## 📞 支持

如果更新后仍有问题：

1. **检查 Nginx 配置**
   ```bash
   docker exec portfolio-lab-frontend cat /etc/nginx/conf.d/default.conf
   ```

   确认 `proxy_pass` 行是：
   ```nginx
   proxy_pass http://backend:8000;
   ```

2. **检查容器日志**
   ```bash
   docker-compose logs frontend
   docker-compose logs backend
   ```

3. **测试网络连接**
   ```bash
   # 从前端容器访问后端
   docker exec portfolio-lab-frontend wget -O- http://backend:8000/api/v1/health/live
   ```

---

## 🔄 完整更新流程

### 本地测试
```bash
# 1. 停止服务
docker-compose down

# 2. 拉取最新镜像
docker-compose pull

# 3. 启动服务
docker-compose up -d

# 4. 验证
curl http://localhost:8032/api/v1/meta/assets
```

### 服务器部署
```bash
# 1. 备份当前配置
cp docker-compose.yml docker-compose.yml.backup

# 2. 更新镜像版本（如果使用固定版本）
# 将 frontend 镜像改为 v1.0.2

# 3. 拉取并重启
docker-compose pull frontend
docker-compose up -d frontend

# 4. 验证
curl http://your-domain.com/api/v1/meta/assets
```

---

**修复时间**：2026-02-22 03:15
**修复者**：Claude Sonnet 4.5
**状态**：✅ 已修复并验证
**测试**：✅ 本地测试通过
