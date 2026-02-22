
---
## 🤖 claude-opus-4-6-thinking | ocoolAI

看完这些提案，我给你整合一个最优的"投资组合实验室"方案，充分利用GCP的算力优势，最终部署到你的轻量服务器。

## 📊 Portfolio Lab - 最优整合方案

### 核心策略
**GCP阶段（重计算）→ 导出预计算结果 → 轻量服务器部署（轻查询）**

---

## 一、功能模块设计（各取所长）

### 1. 投资组合优化引擎
- **均值方差优化**（Markowitz有效前沿）
- **Black-Litterman模型**（结合主观观点）
- **风险平价组合**（Risk Parity）
- **最小方差/最大Sharpe组合**

### 2. 风险度量体系
- **VaR / CVaR**（95%、99%置信度）
- **最大回撤 (Max Drawdown)**
- **Sharpe / Sortino / Calmar Ratio**
- **Beta / 波动率分解**
- **Fama-French三因子暴露**（市场、规模、价值）

### 3. 压力测试模块（核心亮点）
预计算历史危机场景：
- 2008金融危机（-50%股市冲击）
- 2020 COVID崩盘（高波动+快速反弹）
- 2022加息周期（债券暴跌）
- 自定义极端场景（如"股债同跌"）

### 4. 蒙特卡洛模拟引擎
- 预计算**100万+路径**的组合净值分布
- 生成**查找表**：覆盖常见资产配比（每5%一档）
- 用户输入任意配比 → 后端插值查询，秒级响应

---

## 二、GCP资源使用计划（10天冲刺）

### Day 1-2: 数据准备
```python
# 使用BigQuery Public Datasets或yfinance
资产池：
- 美股ETF: SPY, QQQ, IWM, TLT, GLD, BTC
- 国际: EEM, EFA, FXI
- 商品: USO, DBA
- 时间跨度: 2000-2025 (25年日线数据)
```

### Day 3-5: 高性能计算（烧钱重点）
**开启Compute Engine高配实例**：
- 机型：`c2-standard-60`（60核）或`n2-highmem-32`（32核）
- 任务1：跑**500万次蒙特卡洛模拟**
 - 覆盖1000+种资产配比组合
 - 每种组合模拟5000条路径
 - 计算未来1年/3年/5年的收益分布

- 任务2：**协方差矩阵滚动估计**
 - 用5年滚动窗口估计
 - 生成2000-2025每个月的协方差矩阵快照

- 任务3：**压力测试批量计算**
 - 对每种组合应用5种历史危机情景
 - 记录最大回撤、恢复时间

### Day 6-7: 因子分析（可选，增加专业性）
- 用Fama-French公开数据
- 计算每个资产的因子载荷
- 生成组合的因子暴露报告

### Day 8: 数据导出与压缩
```bash
# 预计算结果打包
- portfolio_lookup_table.parquet  # 查找表（压缩后约50MB）
- covariance_matrices.npz         # 协方差矩阵（约20MB）
- stress_test_results.json        # 压力测试结果
- factor_loadings.csv             # 因子数据
```

---

## 三、轻量服务器部署架构

### 技术栈
```yaml
后端: FastAPI (Python)
  - 端口: 8030
  - 功能: 查询预计算结果、简单插值计算
  
数据库: PostgreSQL
  - 端口: 8031
  - 存储: 预计算的风险指标、历史数据
  
前端: React + Plotly.js
  - 端口: 8032
  - 可视化: 有效前沿、蒙特卡洛路径图、压力测试雷达图
  
缓存: Redis (可选)
  - 端口: 8033
  - 加速高频查询
```

### Docker Compose结构
```yaml
services:
  backend:
    image: fuzhouxing/portfolio-lab-backend:latest
    ports: ["8030:8000"]
    
  frontend:
    image: fuzhouxing/portfolio-lab-frontend:latest
    ports: ["8032:80"]
    
  postgres:
    image: postgres:15-alpine
    ports: ["8031:5432"]
    volumes: ["./data:/var/lib/postgresql/data"]
```

---

## 四、用户交互流程

### 前端界面
1. **组合构建器**
 - 拖拽式资产选择
 - 权重滑块（自动归一化）

2. **实时风险仪表盘**
 - 输入组合 → 0.5秒内返回：
 - 预期收益/波动率
 - VaR/CVaR
 - 有效前沿位置
 - Sharpe比率

3. **压力测试模拟器**
 - 选择危机场景 → 展示：
 - 净值曲线对比
 - 最大回撤热力图
 - 恢复时间柱状图

4. **蒙特卡洛可视化**
 - 展示1000条模拟路径的扇形图
 - 标注5%/50%/95%分位数

---
