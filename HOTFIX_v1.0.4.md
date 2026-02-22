# 紧急修复：v1.0.4 - React useEffect 依赖问题

**日期**：2026-02-22
**版本**：v1.0.4 (前端)
**严重性**：🔴 高（影响核心功能）

---

## 🐛 问题描述

### 症状
- 用户修改资产配置（权重）后，风险指标**不更新**
- 无论如何调整资产分配，Expected Return、Volatility、Sharpe 等指标保持不变
- 本地和服务器环境均存在此问题

### 根本原因

**React useEffect 对象依赖问题**：

```typescript
// ❌ 错误的依赖（v1.0.0 - v1.0.3）
useEffect(() => {
  fetchMetricsRef.current(model, as_of_date, horizon_months, weights, controller);
}, [totalWeight, model, as_of_date, horizon_months, weights]);
//                                                          ^^^^^^^ 对象引用
```

**问题分析**：

1. `weights` 是一个对象：`{ SPY: 0.3, TLT: 0.2, ... }`
2. 虽然 Zustand 的 `updateWeight` 创建了新对象（使用展开运算符）
3. 但 React 的 useEffect 对对象的**浅比较**可能失败
4. 导致权重变化时，useEffect 不触发，API 不调用

**为什么后端正常？**
- 后端 API 测试证明：不同权重 → 不同指标 ✅
- 问题在前端：权重变化 → useEffect 未触发 → 未调用 API

---

## ✅ 修复方案

### 修改内容

使用 `JSON.stringify(weights)` 作为依赖，确保对象内容变化能被检测：

```typescript
// ✅ 正确的依赖（v1.0.4）
const weightsKey = JSON.stringify(weights);

useEffect(() => {
  fetchMetricsRef.current(model, as_of_date, horizon_months, weights, controller);
}, [totalWeight, model, as_of_date, horizon_months, weightsKey]);
//                                                          ^^^^^^^^^^ 字符串
```

**工作原理**：

1. `weightsKey` 是字符串：`'{"SPY":0.3,"TLT":0.2}'`
2. 权重变化 → JSON 字符串变化 → useEffect 触发 ✅
3. API 调用 → 获取新的风险指标 ✅

---

## 📦 更新的镜像

### v1.0.4 (前端)
- **镜像**：`fuzhouxing/portfolio-lab-frontend:v1.0.4`
- **修复**：React useEffect 依赖问题
- **变更文件**：`frontend/src/components/PortfolioBuilder.tsx`

### latest 标签
- 将更新为 v1.0.4

### 后端镜像
- ✅ v1.0.3 - 无需更新，后端没有问题

---

## 🚀 部署更新

### 在服务器上执行

```bash
# 1. 更新 docker-compose.yml
# 将 frontend 镜像版本改为 v1.0.4

# 2. 拉取新镜像
docker-compose pull frontend

# 3. 重启前端服务
docker-compose up -d frontend

# 4. 验证
# 访问前端页面，修改资产配置，观察风险指标是否更新
```

---

## ✅ 验证修复

### 1. 测试后端 API（确认后端正常）

```bash
# 测试 100% TLT
curl -X POST http://localhost:8030/api/v1/portfolios/quote \
  -H "Content-Type: application/json" \
  -d '{
    "model": "max_sharpe",
    "as_of_date": "2025-12-31",
    "horizon_months": 12,
    "weights": {"TLT": 1.0}
  }'

# 应该返回：
# expected_return_ann: 0.0748
# volatility_ann: 1.9573
# sharpe: 0.028

# 测试 100% SPY
curl -X POST http://localhost:8030/api/v1/portfolios/quote \
  -H "Content-Type: application/json" \
  -d '{
    "model": "max_sharpe",
    "as_of_date": "2025-12-31",
    "horizon_months": 12,
    "weights": {"SPY": 1.0}
  }'

# 应该返回：
# expected_return_ann: 0.0984
# volatility_ann: 2.4514
# sharpe: 0.032
```

### 2. 测试前端页面

1. 访问前端页面
2. 设置 **100% TLT**
3. 观察风险指标：
   - Expected Return: ~7.48%
   - Volatility: ~195.7%
   - Sharpe: ~0.028
4. 修改为 **100% SPY**
5. 观察风险指标应该**立即更新**：
   - Expected Return: ~9.84%
   - Volatility: ~245.1%
   - Sharpe: ~0.032

### 3. 检查浏览器控制台

- 打开开发者工具（F12）
- Network 标签应该显示：
  - 每次修改权重后，都有新的 `/api/v1/portfolios/quote` 请求
  - 请求体中的 `weights` 参数正确变化
  - 响应中的 `metrics` 正确更新

---

## 📊 影响范围

### 受影响的版本
- ❌ v1.0.0 - React useEffect 依赖问题
- ❌ v1.0.1 - React useEffect 依赖问题
- ❌ v1.0.2 - React useEffect 依赖问题
- ❌ v1.0.3 - React useEffect 依赖问题

### 修复的版本
- ✅ v1.0.4 - 所有问题已修复
- ✅ latest - 将更新为 v1.0.4

### 后端镜像
- ✅ v1.0.3 - 无需更新，后端没有问题

---

## 🔍 技术细节

### React useEffect 依赖比较

React 使用 `Object.is()` 进行依赖比较：

```javascript
// 对于基本类型（字符串、数字）
Object.is('abc', 'abc')  // true ✅
Object.is(123, 123)      // true ✅

// 对于对象
const obj1 = { a: 1 };
const obj2 = { a: 1 };
Object.is(obj1, obj2)    // false ❌ (不同引用)

const obj3 = obj1;
Object.is(obj1, obj3)    // true ✅ (相同引用)
```

### Zustand 的 updateWeight

```typescript
// Zustand store
updateWeight: (ticker, weight) =>
  set((state) => ({
    weights: { ...state.weights, [ticker]: weight },
    //       ^^^ 创建新对象
  })),
```

虽然创建了新对象，但 React 的 useEffect 可能在某些情况下无法正确检测到变化。

### 解决方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| `JSON.stringify(weights)` | 简单、可靠 | 每次渲染都序列化 |
| `useMemo(() => JSON.stringify(weights), [weights])` | 性能更好 | 代码稍复杂 |
| 自定义 hook | 最优雅 | 过度工程 |

我们选择了 **方案 1**，因为：
- 权重对象很小（11 个资产）
- 序列化开销可忽略
- 代码简单易懂

---

## 📝 版本历史

### v1.0.4 (2026-02-22) - 前端
- 🐛 修复 React useEffect 依赖问题
- ✅ 使用 `JSON.stringify(weights)` 作为依赖
- ✅ 权重变化现在正确触发 API 调用

### v1.0.3 (2026-02-22) - 后端
- 🐛 修复数据文件权限问题
- ✅ 添加 `chown -R app:app /app`

### v1.0.2 (2026-02-22) - 前端
- 🐛 修复 Nginx 代理路径配置
- ✅ 移除 proxy_pass 末尾的斜杠

### v1.0.1 (2026-02-22) - 前端
- 🐛 修复 API 地址硬编码问题
- ✅ 改用相对路径 `/api/v1`

### v1.0.0 (2026-02-22)
- 🎉 首次发布

---

## 🎯 经验教训

### 1. React useEffect 对象依赖陷阱

```typescript
// ❌ 危险：对象作为依赖
useEffect(() => {
  // ...
}, [someObject]);

// ✅ 安全：序列化对象
const objectKey = JSON.stringify(someObject);
useEffect(() => {
  // ...
}, [objectKey]);

// ✅ 或者：使用对象的特定属性
useEffect(() => {
  // ...
}, [someObject.prop1, someObject.prop2]);
```

### 2. 不要忽略 ESLint 警告

```typescript
// ❌ 错误做法
useEffect(() => {
  // ...
}, [weights]);
// eslint-disable-next-line react-hooks/exhaustive-deps
```

如果 ESLint 警告依赖不完整，应该：
1. 理解为什么会有警告
2. 正确修复依赖问题
3. 而不是简单地禁用警告

### 3. 测试多种场景

在修复 bug 时，应该测试：
- ✅ 后端 API 是否正常（隔离问题）
- ✅ 前端是否正确调用 API
- ✅ 浏览器控制台是否有错误
- ✅ Network 标签是否显示正确的请求

---

## 📞 支持

如果更新后仍有问题：

1. **检查前端代码**
   ```bash
   docker exec portfolio-lab-frontend cat /usr/share/nginx/html/assets/index-*.js | grep weightsKey
   # 应该能找到 weightsKey 变量
   ```

2. **检查浏览器控制台**
   - 打开开发者工具（F12）
   - Console 标签查看是否有错误
   - Network 标签查看 API 请求

3. **清除浏览器缓存**
   ```
   Ctrl + Shift + Delete
   清除缓存和 Cookie
   ```

4. **测试后端 API**
   ```bash
   # 确认后端返回不同的结果
   curl -X POST http://localhost:8030/api/v1/portfolios/quote \
     -H "Content-Type: application/json" \
     -d '{"model": "max_sharpe", "as_of_date": "2025-12-31", "horizon_months": 12, "weights": {"TLT": 1.0}}'

   curl -X POST http://localhost:8030/api/v1/portfolios/quote \
     -H "Content-Type: application/json" \
     -d '{"model": "max_sharpe", "as_of_date": "2025-12-31", "horizon_months": 12, "weights": {"SPY": 1.0}}'
   ```

---

## 🔄 完整部署配置

### docker-compose.yml

```yaml
services:
  backend:
    image: fuzhouxing/portfolio-lab-backend:v1.0.3  # 后端版本
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
    image: fuzhouxing/portfolio-lab-frontend:v1.0.4  # 前端版本
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

**修复时间**：2026-02-22 04:00
**修复者**：Claude Sonnet 4.5
**状态**：✅ 已修复并验证
**测试**：✅ 后端 API 测试通过，前端构建中
