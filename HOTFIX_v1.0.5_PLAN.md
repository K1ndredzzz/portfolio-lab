# 修复计划：v1.0.5 - Monte Carlo 和 Stress Test 实时计算

**日期**：2026-02-22
**版本**：v1.0.5
**严重性**：🟡 中（功能不完整）

---

## 🐛 问题描述

### 症状
- Monte Carlo Simulation 和 Stress Test Analysis **不随资产配置变化**
- 无论用户如何调整权重，这两个图表显示的都是预设模型的结果
- Risk Metrics 正常工作（v1.0.4 已修复）

### 根本原因

**设计缺陷**：Monte Carlo 和 Stress Test 端点只使用预计算数据

1. **前端 API 调用不传递 weights**：
   ```typescript
   // ❌ 当前实现
   getMonteCarlo(model, horizon_months)  // 没有 weights
   getStressTest(model)                   // 没有 weights
   ```

2. **后端只查询预计算数据**：
   ```python
   # ❌ 当前实现
   @router.post("/monte-carlo")
   async def get_monte_carlo_simulation(request: MonteCarloRequest):
       # 只根据 model 和 horizon_months 查询预计算数据
       filtered = mc_df[(mc_df['model'] == request.model) &
                        (mc_df['horizon_months'] == request.horizon_months)]
   ```

3. **前端组件依赖不包含 weights**：
   ```typescript
   // ❌ MonteCarloChart.tsx
   useEffect(() => {
     fetchMonteCarlo();
   }, [model, horizon_months]);  // 缺少 weights 依赖

   // ❌ StressTestChart.tsx
   useEffect(() => {
     fetchStressTests();
   }, [model]);  // 缺少 weights 依赖
   ```

---

## ✅ 修复方案

### 方案选择

有两种方案：

#### 方案 A：实时计算（推荐）
- **优点**：用户可以测试任意权重组合
- **缺点**：计算开销较大（Monte Carlo 需要模拟）
- **适用**：Stress Test（计算简单）

#### 方案 B：保持预计算
- **优点**：性能好，无计算开销
- **缺点**：只能显示预设模型的结果
- **适用**：Monte Carlo（计算复杂）

### 最终方案

**混合方案**：
1. **Stress Test**：改为实时计算（简单，只需计算历史场景下的收益）
2. **Monte Carlo**：保持预计算，但**明确告知用户**这是基于预设模型的结果

---

## 📝 实施步骤

### 1. Stress Test 实时计算

#### 1.1 修改后端 Schema

**文件**：`app/schemas/risk.py`

```python
# 添加 weights 参数
class StressTestRequest(BaseModel):
    model: str
    weights: Dict[str, float] = Field(..., min_length=1)  # 新增
```

#### 1.2 修改后端端点

**文件**：`app/api/v1/endpoints/risk.py`

```python
@router.post("/stress", response_model=List[StressTestResponse])
async def get_stress_test_results(
    request: StressTestRequest,
    db: Session = Depends(get_db)
):
    """实时计算压力测试结果"""
    # 1. 加载历史场景数据（价格变化）
    # 2. 根据用户权重计算组合收益
    # 3. 返回结果
```

#### 1.3 修改前端 API

**文件**：`frontend/src/api/index.ts`

```typescript
export const getStressTest = async (
  model: 'risk_parity' | 'max_sharpe' | 'min_variance',
  weights: PortfolioWeights,  // 新增
  signal?: AbortSignal
): Promise<StressTestResult[]> => {
  const response = await api.post('/risk/stress', {
    model,
    weights,  // 新增
  }, { signal });
  return response.data;
};
```

#### 1.4 修改前端组件

**文件**：`frontend/src/components/StressTestChart.tsx`

```typescript
const weights = usePortfolioStore((state) => state.weights);
const weightsKey = JSON.stringify(weights);  // 新增

useEffect(() => {
  fetchStressTests();
}, [model, weightsKey]);  // 添加 weightsKey 依赖
```

### 2. Monte Carlo 说明优化

#### 2.1 添加说明文本

**文件**：`frontend/src/components/MonteCarloChart.tsx`

在图表标题下方添加说明：

```typescript
<div className="chart-note">
  <p>Note: This simulation is based on the {model} model's optimal allocation.</p>
  <p>For custom portfolio simulations, please contact support.</p>
</div>
```

---

## 🔧 技术实现

### Stress Test 实时计算逻辑

```python
def calculate_stress_test(weights: Dict[str, float], scenario_name: str) -> float:
    """
    计算给定权重组合在历史场景下的收益

    Args:
        weights: 资产权重 {ticker: weight}
        scenario_name: 场景名称（如 "2008_financial_crisis"）

    Returns:
        组合收益率
    """
    # 1. 加载场景期间的价格数据
    scenario_prices = load_scenario_prices(scenario_name)

    # 2. 计算每个资产的收益率
    asset_returns = {}
    for ticker in weights.keys():
        start_price = scenario_prices[ticker].iloc[0]
        end_price = scenario_prices[ticker].iloc[-1]
        asset_returns[ticker] = (end_price - start_price) / start_price

    # 3. 计算组合收益率
    portfolio_return = sum(weights[ticker] * asset_returns[ticker]
                          for ticker in weights.keys())

    return portfolio_return
```

### 场景数据结构

需要准备历史场景的价格数据：

```python
# data/stress_scenarios.parquet
# 列：scenario_name, ticker, start_date, end_date, start_price, end_price, return
```

---

## 📦 影响范围

### 后端变更
- ✅ `app/schemas/risk.py` - 添加 weights 参数
- ✅ `app/api/v1/endpoints/risk.py` - 实时计算逻辑
- ✅ 需要准备场景价格数据

### 前端变更
- ✅ `frontend/src/api/index.ts` - 传递 weights
- ✅ `frontend/src/components/StressTestChart.tsx` - 添加 weights 依赖
- ✅ `frontend/src/components/MonteCarloChart.tsx` - 添加说明文本

---

## 🎯 预期效果

### Stress Test（修复后）
1. 用户设置 **100% TLT**
2. Stress Test 显示 TLT 在各场景下的表现
3. 用户修改为 **100% SPY**
4. Stress Test **立即更新**，显示 SPY 的表现

### Monte Carlo（保持现状 + 说明）
1. 显示预设模型的模拟结果
2. 添加说明文字，告知用户这是基于模型的最优配置
3. 未来可以考虑添加实时计算功能

---

## ⚠️ 注意事项

### 性能考虑
- Stress Test 计算简单，实时计算可行
- Monte Carlo 需要大量模拟，实时计算开销大
- 可以考虑为 Monte Carlo 添加缓存机制

### 数据准备
- 需要准备历史场景的价格数据
- 场景定义：
  - 2008 金融危机：2008-09-01 至 2009-03-31
  - 2020 COVID 崩盘：2020-02-01 至 2020-03-31
  - 2022 加息周期：2022-01-01 至 2022-12-31

---

## 📅 实施时间表

1. **准备场景数据**（30分钟）
   - 从 clean_prices.parquet 提取场景期间的价格
   - 生成 stress_scenarios.parquet

2. **后端实现**（1小时）
   - 修改 Schema
   - 实现实时计算逻辑
   - 测试 API

3. **前端实现**（30分钟）
   - 修改 API 调用
   - 修改组件依赖
   - 添加 Monte Carlo 说明

4. **测试验证**（30分钟）
   - 测试不同权重组合
   - 验证结果正确性

**总计**：约 2.5 小时

---

**创建时间**：2026-02-22 04:30
**创建者**：Claude Sonnet 4.5
**状态**：📋 计划中
