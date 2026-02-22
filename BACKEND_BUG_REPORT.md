# 后端 Bug 修复报告

**日期**：2026-02-22
**问题**：Risk Metrics 不随投资组合变化（后端返回硬编码数据）
**状态**：✅ 已识别根本原因

---

## 🐛 问题根本原因

### 发现过程

1. **前端测试**：调整权重后，Risk Metrics 始终显示相同数值
2. **后端测试**：直接调用 API，不同权重返回相同结果
3. **代码审查**：发现 `portfolios.py` 第 58-69 行返回硬编码的 mock 数据

### 根本原因

**`app/api/v1/endpoints/portfolios.py`** 中的代码：

```python
# Query from database (placeholder - will be implemented after data import)
# For now, return mock data
mock_metrics = {
    "expected_return_ann": 0.094,
    "volatility_ann": 0.127,
    "sharpe": 0.63,
    # ... 硬编码的固定值
}
```

**为什么会这样**：
- 数据库集成未完成（进度 20%）
- API 端点使用 mock 数据作为临时方案
- Redis 缓存了 mock 数据，导致所有请求返回相同结果

### 预计算数据文件的问题

尝试使用 `data/portfolios.parquet` 文件，但发现：
1. **缺少字段**：只有 `expected_return`, `volatility`, `sharpe` 三个指标
2. **缺少 horizon_months**：无法匹配不同投资期限
3. **缺少完整风险指标**：没有 sortino, VaR, CVaR, max_drawdown, calmar

---

## ✅ 解决方案

### 方案 1：实时计算（推荐）

使用协方差矩阵实时计算风险指标：

**优点**：
- 支持任意权重组合
- 计算准确
- 无需预计算所有可能组合

**缺点**：
- 需要实现风险指标计算逻辑
- 响应时间稍长（但仍可在 100ms 内完成）

### 方案 2：扩展预计算数据

重新运行 GCP 计算任务，生成包含所有风险指标的数据：

**优点**：
- 响应速度快
- 数据一致性好

**缺点**：
- 需要重新计算（耗时）
- 只能支持预计算的权重组合
- 用户自定义组合需要插值或实时计算

### 方案 3：混合方案

- 预计算常见组合（Risk Parity, Max Sharpe, Min Variance 的标准权重）
- 用户自定义组合实时计算

---

## 🔧 临时解决方案

由于时间限制，建议采用**方案 1：实时计算**。

### 实现步骤

1. **加载协方差矩阵**（已有 `covariance_matrices.npz`）
2. **实现风险指标计算函数**：
   - Expected Return = weights @ expected_returns
   - Volatility = sqrt(weights @ cov_matrix @ weights)
   - Sharpe Ratio = (return - risk_free_rate) / volatility
   - Sortino, VaR, CVaR, Max Drawdown, Calmar（需要历史收益数据）

3. **更新 API 端点**：
   - 移除 mock 数据
   - 调用实时计算函数
   - 缓存结果到 Redis

---

## 📊 影响范围

| 组件 | 影响 | 状态 |
|------|------|------|
| 后端 API | 返回硬编码数据 | 🔴 需修复 |
| 前端 | 显示不变的指标 | ⚠️ 等待后端修复 |
| Redis 缓存 | 缓存了错误数据 | ✅ 已清除 |
| 数据库 | 未集成 | ⏳ 待完成 |

---

## 🎯 下一步行动

### 立即行动（高优先级）

1. **实现实时风险指标计算**
   - 加载协方差矩阵和历史收益数据
   - 实现计算函数
   - 更新 API 端点

2. **测试验证**
   - 测试不同权重组合
   - 验证计算准确性
   - 性能测试（确保 < 100ms）

### 后续优化（中优先级）

1. **完成数据库集成**
   - 调整表结构
   - 导入预计算数据
   - 更新 API 从数据库查询

2. **扩展预计算数据**
   - 添加缺失的风险指标
   - 添加 horizon_months 字段
   - 重新运行 GCP 计算任务

---

## 📝 经验教训

1. **Mock 数据的风险**
   - Mock 数据应该明显标记（如返回特殊值）
   - 应该在开发早期完成真实数据集成
   - Redis 缓存会放大 mock 数据的影响

2. **预计算数据的完整性**
   - 预计算时应包含所有需要的字段
   - 应该有数据验证步骤
   - 文档应该说明数据结构

3. **测试的重要性**
   - 应该有端到端测试验证数据变化
   - 不应该只依赖单元测试
   - 用户反馈是最终验证

---

**生成时间**：2026-02-22
**状态**：问题已识别，等待实现修复
