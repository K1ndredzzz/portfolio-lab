# GCP 计算任务执行指南 - 权重网格版本

**日期**：2026-02-22
**版本**：v2.0 - 权重网格查找表
**目标**：生成 ~137,000 种权重组合的 Monte Carlo 和 Stress Test 结果

---

## 📋 任务概述

### 数据规模估算

**权重网格**：
- 资产数量：11 个
- 步长：10%（0.0, 0.1, 0.2, ..., 1.0）
- 总组合数：**~137,000**

**Monte Carlo 模拟**：
- 组合数：137,000
- 期限：4 个（12/24/36/60 个月）
- 每组合模拟次数：10,000
- 总模拟次数：**5.48 亿次**
- 预计数据量：**~2-3 GB**

**Stress Test**：
- 组合数：137,000
- 场景：3 个
- 总计算次数：**411,000**
- 预计数据量：**~50 MB**

---

## 🖥️ GCP 资源配置

### 推荐配置

**Monte Carlo 计算**：
- 机器类型：`c2-standard-60` 或 `c2-standard-30`
- vCPU：60 核（或 30 核）
- 内存：240 GB（或 120 GB）
- 预计时间：2-4 小时（60 核）或 4-8 小时（30 核）
- 成本：~$10-20（使用 preemptible 实例）

**Stress Test 计算**：
- 机器类型：`n2-standard-8`
- vCPU：8 核
- 内存：32 GB
- 预计时间：5-10 分钟
- 成本：~$0.50

---

## 🚀 执行步骤

### 1. 准备 GCP 环境

```bash
# 创建 GCP 实例
gcloud compute instances create portfolio-compute \
  --machine-type=c2-standard-60 \
  --zone=us-central1-a \
  --image-family=ubuntu-2004-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=100GB \
  --preemptible

# SSH 登录
gcloud compute ssh portfolio-compute --zone=us-central1-a
```

### 2. 安装依赖

```bash
# 更新系统
sudo apt-get update
sudo apt-get install -y python3-pip git

# 安装 Python 包
pip3 install pandas numpy pyarrow
```

### 3. 上传数据和脚本

```bash
# 在本地执行，上传必要文件
gcloud compute scp data/covariance_matrices.npz portfolio-compute:~/data/ --zone=us-central1-a
gcloud compute scp data/clean_prices.parquet portfolio-compute:~/data/ --zone=us-central1-a
gcloud compute scp jobs/scripts/30_compute_monte_carlo_grid.py portfolio-compute:~/ --zone=us-central1-a
gcloud compute scp jobs/scripts/40_compute_stress_tests_grid.py portfolio-compute:~/ --zone=us-central1-a
```

### 4. 运行 Monte Carlo 计算

```bash
# 在 GCP 实例上执行
cd ~
mkdir -p output

# 运行 Monte Carlo（后台运行，使用 nohup）
nohup python3 30_compute_monte_carlo_grid.py \
  --cov data/covariance_matrices.npz \
  --returns data/clean_prices.parquet \
  --output output/monte_carlo_grid.parquet \
  --n-sims 10000 \
  --step 0.10 \
  > monte_carlo.log 2>&1 &

# 查看进度
tail -f monte_carlo.log

# 或者使用 screen/tmux
screen -S monte_carlo
python3 30_compute_monte_carlo_grid.py \
  --cov data/covariance_matrices.npz \
  --returns data/clean_prices.parquet \
  --output output/monte_carlo_grid.parquet \
  --n-sims 10000 \
  --step 0.10
# Ctrl+A+D 分离会话
```

### 5. 运行 Stress Test 计算

```bash
# 运行 Stress Test
python3 40_compute_stress_tests_grid.py \
  --cov data/covariance_matrices.npz \
  --output output/stress_tests_grid.parquet \
  --step 0.10
```

### 6. 下载结果

```bash
# 在本地执行
gcloud compute scp portfolio-compute:~/output/monte_carlo_grid.parquet data/ --zone=us-central1-a
gcloud compute scp portfolio-compute:~/output/monte_carlo_grid_weights.parquet data/ --zone=us-central1-a
gcloud compute scp portfolio-compute:~/output/stress_tests_grid.parquet data/ --zone=us-central1-a
gcloud compute scp portfolio-compute:~/output/stress_tests_grid_weights.parquet data/ --zone=us-central1-a
```

### 7. 清理资源

```bash
# 删除 GCP 实例
gcloud compute instances delete portfolio-compute --zone=us-central1-a
```

---

## ⚡ 性能优化建议

### 1. 使用并行计算

如果需要更快的速度，可以修改脚本使用多进程：

```python
from multiprocessing import Pool

def compute_combination(args):
    weights, expected_returns, cov_matrix, horizons, n_sims = args
    # ... Monte Carlo 计算
    return results

# 使用进程池
with Pool(processes=60) as pool:
    results = pool.map(compute_combination, combinations)
```

### 2. 分批计算

如果担心 preemptible 实例被中断，可以分批计算：

```bash
# 计算前 50,000 个组合
python3 30_compute_monte_carlo_grid.py --max-combinations 50000 --output output/mc_batch1.parquet

# 计算接下来的 50,000 个
python3 30_compute_monte_carlo_grid.py --skip 50000 --max-combinations 50000 --output output/mc_batch2.parquet

# 最后合并
python3 -c "
import pandas as pd
df1 = pd.read_parquet('output/mc_batch1.parquet')
df2 = pd.read_parquet('output/mc_batch2.parquet')
df3 = pd.read_parquet('output/mc_batch3.parquet')
pd.concat([df1, df2, df3]).to_parquet('output/monte_carlo_grid.parquet')
"
```

### 3. 减少模拟次数（测试）

如果只是测试，可以减少模拟次数：

```bash
# 使用 1000 次模拟（快速测试）
python3 30_compute_monte_carlo_grid.py --n-sims 1000 --max-combinations 1000
```

---

## 📊 预期输出

### Monte Carlo 结果

**文件**：`monte_carlo_grid.parquet`

**结构**：
```
weights_hash | as_of_date | horizon_months | percentile | return_value | stat_type
-------------|------------|----------------|------------|--------------|----------
abc123...    | 2025-12-31 | 12            | 1          | 0.05         | percentile
abc123...    | 2025-12-31 | 12            | 5          | 0.10         | percentile
...
```

**行数**：~6,000,000（137,000 组合 × 4 期限 × 11 统计量）

### 权重映射

**文件**：`monte_carlo_grid_weights.parquet`

**结构**：
```
weights_hash | weight_SPY | weight_QQQ | weight_TLT | ...
-------------|------------|------------|------------|----
abc123...    | 0.1        | 0.2        | 0.3        | ...
```

**行数**：~137,000

### Stress Test 结果

**文件**：`stress_tests_grid.parquet`

**结构**：
```
weights_hash | as_of_date | scenario_name         | scenario_description | portfolio_return
-------------|------------|-----------------------|---------------------|------------------
abc123...    | 2025-12-31 | 2008_financial_crisis | 2008 Financial...   | -0.25
```

**行数**：~411,000（137,000 组合 × 3 场景）

---

## ✅ 验证检查

### 1. 检查数据完整性

```python
import pandas as pd

# 检查 Monte Carlo
mc_df = pd.read_parquet('data/monte_carlo_grid.parquet')
print(f"Monte Carlo rows: {len(mc_df):,}")
print(f"Unique weights_hash: {mc_df['weights_hash'].nunique():,}")
print(f"Unique horizons: {mc_df['horizon_months'].unique()}")

# 检查 Stress Test
st_df = pd.read_parquet('data/stress_tests_grid.parquet')
print(f"Stress Test rows: {len(st_df):,}")
print(f"Unique weights_hash: {st_df['weights_hash'].nunique():,}")
print(f"Unique scenarios: {st_df['scenario_name'].unique()}")

# 检查权重映射
weights_df = pd.read_parquet('data/monte_carlo_grid_weights.parquet')
print(f"Weight combinations: {len(weights_df):,}")
print(f"Sample weights:")
print(weights_df.head())
```

### 2. 检查数据质量

```python
# 检查权重和为 1
weight_cols = [col for col in weights_df.columns if col.startswith('weight_')]
weights_sum = weights_df[weight_cols].sum(axis=1)
print(f"All weights sum to 1.0: {(weights_sum - 1.0).abs().max() < 1e-6}")

# 检查 Monte Carlo 结果合理性
print(f"Mean return range: {mc_df['return_value'].min():.2%} to {mc_df['return_value'].max():.2%}")

# 检查 Stress Test 结果合理性
print(f"Stress return range: {st_df['portfolio_return'].min():.2%} to {st_df['portfolio_return'].max():.2%}")
```

---

## 🎯 成功标准

- ✅ Monte Carlo 数据：~6,000,000 行
- ✅ Stress Test 数据：~411,000 行
- ✅ 权重映射：~137,000 行
- ✅ 所有权重和为 1.0
- ✅ 数据文件大小：2-3 GB（Monte Carlo）+ 50 MB（Stress Test）
- ✅ 无缺失值或异常值

---

## 📞 故障排除

### 问题 1：内存不足

**症状**：`MemoryError` 或进程被 killed

**解决**：
- 使用更大内存的机器（n2-highmem-32）
- 分批计算（使用 --max-combinations）
- 减少模拟次数（--n-sims 5000）

### 问题 2：计算时间过长

**症状**：超过预期时间

**解决**：
- 使用更多 CPU 核心（c2-standard-60）
- 实现多进程并行
- 检查是否有 I/O 瓶颈

### 问题 3：Preemptible 实例被中断

**症状**：计算中途停止

**解决**：
- 使用 checkpoint 机制保存中间结果
- 分批计算，每批独立保存
- 使用非 preemptible 实例（成本更高）

---

**创建时间**：2026-02-22 05:00
**创建者**：Claude Sonnet 4.5
**状态**：📋 准备就绪
