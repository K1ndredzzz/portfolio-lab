# GCP Computation Deployment Guide

**Version**: v1.1.0
**Date**: 2026-02-22
**Purpose**: Generate complete weight grid lookup tables (137,000 combinations)

## Overview

This guide walks through deploying and running the weight grid computation on Google Cloud Platform (GCP). The computation generates Monte Carlo simulations and Stress Test results for all possible portfolio weight combinations.

## Prerequisites

- GCP account with billing enabled
- `gcloud` CLI installed and configured
- Project files ready for upload

## Resource Requirements

### Monte Carlo Grid Computation
- **Instance Type**: `c2-standard-60` (60 vCPUs, 240 GB RAM)
- **Estimated Time**: 2-4 hours
- **Estimated Cost**: $10-15 (using preemptible instance)
- **Output Size**: ~15 GB (parquet files)

### Stress Test Grid Computation
- **Instance Type**: `n2-standard-8` (8 vCPUs, 32 GB RAM)
- **Estimated Time**: 5-10 minutes
- **Estimated Cost**: $0.50-1.00 (using preemptible instance)
- **Output Size**: ~500 MB (parquet files)

## Step-by-Step Instructions

### 1. Create GCP Compute Instance

```bash
# Set project and zone
export PROJECT_ID="your-project-id"
export ZONE="us-central1-a"
export INSTANCE_NAME="portfolio-grid-compute"

gcloud config set project $PROJECT_ID

# Create compute instance for Monte Carlo (high CPU)
gcloud compute instances create $INSTANCE_NAME \
  --zone=$ZONE \
  --machine-type=c2-standard-60 \
  --preemptible \
  --boot-disk-size=100GB \
  --boot-disk-type=pd-ssd \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --metadata=startup-script='#!/bin/bash
    apt-get update
    apt-get install -y python3-pip python3-venv
    '
```

### 2. Upload Project Files

```bash
# Create archive of necessary files
cd /d/Code_new/portfolio-lab

# Create a deployment package
tar -czf grid-computation.tar.gz \
  jobs/scripts/30_compute_monte_carlo_grid.py \
  jobs/scripts/40_compute_stress_tests_grid.py \
  data/covariance_matrices.npz \
  data/clean_prices.parquet \
  requirements.txt

# Upload to GCP instance
gcloud compute scp grid-computation.tar.gz \
  $INSTANCE_NAME:~/ \
  --zone=$ZONE
```

### 3. SSH into Instance and Setup Environment

```bash
# SSH into the instance
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE

# On the instance:
cd ~
tar -xzf grid-computation.tar.gz

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install numpy pandas pyarrow tqdm
```

### 4. Run Monte Carlo Grid Computation

```bash
# Create output directory
mkdir -p data

# Run Monte Carlo grid generation (2-4 hours)
nohup python jobs/scripts/30_compute_monte_carlo_grid.py > monte_carlo_grid.log 2>&1 &

# Monitor progress
tail -f monte_carlo_grid.log

# Check process
ps aux | grep python
```

**Expected Output Files**:
- `data/monte_carlo_grid.parquet` (~12 GB)
- `data/monte_carlo_grid_weights.parquet` (~3 GB)

### 5. Run Stress Test Grid Computation

```bash
# Run Stress Test grid generation (5-10 minutes)
nohup python jobs/scripts/40_compute_stress_tests_grid.py > stress_tests_grid.log 2>&1 &

# Monitor progress
tail -f stress_tests_grid.log
```

**Expected Output Files**:
- `data/stress_tests_grid.parquet` (~400 MB)
- `data/stress_tests_grid_weights.parquet` (~100 MB)

### 6. Download Results

```bash
# Exit SSH session
exit

# Download generated files from local machine
gcloud compute scp \
  $INSTANCE_NAME:~/data/monte_carlo_grid.parquet \
  $INSTANCE_NAME:~/data/monte_carlo_grid_weights.parquet \
  $INSTANCE_NAME:~/data/stress_tests_grid.parquet \
  $INSTANCE_NAME:~/data/stress_tests_grid_weights.parquet \
  ./data/ \
  --zone=$ZONE
```

### 7. Verify Downloaded Files

```bash
# Check file sizes
ls -lh data/*_grid*.parquet

# Verify data integrity (optional)
python -c "
import pandas as pd
mc = pd.read_parquet('data/monte_carlo_grid.parquet')
print(f'Monte Carlo rows: {len(mc):,}')
print(f'Expected: ~6,023,000 rows (137,000 × 4 horizons × 11 stats)')

st = pd.read_parquet('data/stress_tests_grid.parquet')
print(f'Stress Test rows: {len(st):,}')
print(f'Expected: ~411,000 rows (137,000 × 3 scenarios)')
"
```

### 8. Cleanup GCP Resources

```bash
# Delete the compute instance to stop charges
gcloud compute instances delete $INSTANCE_NAME \
  --zone=$ZONE \
  --quiet
```

## Alternative: Using Smaller Instance for Testing

If you want to test with a smaller dataset first:

```bash
# Use smaller instance
gcloud compute instances create portfolio-grid-test \
  --zone=$ZONE \
  --machine-type=n2-standard-16 \
  --preemptible \
  --boot-disk-size=50GB

# Modify scripts to limit combinations
# Edit 30_compute_monte_carlo_grid.py line 120:
# Change: for i, weights in enumerate(weight_grid):
# To:     for i, weights in enumerate(weight_grid[:5000]):
```

## Monitoring and Troubleshooting

### Check Instance Status
```bash
gcloud compute instances list --filter="name=$INSTANCE_NAME"
```

### View Logs
```bash
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="tail -100 ~/monte_carlo_grid.log"
```

### Check Disk Space
```bash
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="df -h"
```

### Restart Failed Job
```bash
# If job fails, check logs first
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE

# On instance:
tail -100 monte_carlo_grid.log

# Restart if needed
source venv/bin/activate
python jobs/scripts/30_compute_monte_carlo_grid.py
```

## Cost Optimization Tips

1. **Use Preemptible Instances**: 80% cheaper, but can be terminated
2. **Use Spot VMs**: Similar to preemptible but more flexible
3. **Right-size Instance**: Start with smaller instance for testing
4. **Delete When Done**: Don't forget to delete instance after downloading results
5. **Use Regional Storage**: Store intermediate results in Cloud Storage if needed

## Expected Costs Breakdown

| Resource | Type | Duration | Cost |
|----------|------|----------|------|
| c2-standard-60 | Preemptible | 3 hours | ~$12 |
| n2-standard-8 | Preemptible | 10 minutes | ~$0.50 |
| Disk (100GB SSD) | pd-ssd | 4 hours | ~$0.70 |
| Network Egress | Download | 15 GB | ~$1.50 |
| **Total** | | | **~$15** |

## Post-Deployment

After downloading the files:

1. **Replace Test Data**:
   ```bash
   # Backup test data
   mv data/monte_carlo_grid_test.parquet data/backup/
   mv data/stress_tests_grid_test.parquet data/backup/

   # Production data is already named correctly
   # monte_carlo_grid.parquet
   # stress_tests_grid.parquet
   ```

2. **Restart Backend**:
   ```bash
   # Docker
   docker-compose restart backend

   # Or local
   python -m uvicorn app.main:app --reload
   ```

3. **Test API**:
   ```bash
   curl -X POST http://localhost:8030/api/v1/risk/monte-carlo \
     -H "Content-Type: application/json" \
     -d '{"weights": {"SPY": 0.5, "TLT": 0.5}, "horizon_months": 36}'
   ```

## Support

If you encounter issues:
1. Check logs: `monte_carlo_grid.log` and `stress_tests_grid.log`
2. Verify input files exist: `covariance_matrices.npz` and `clean_prices.parquet`
3. Check disk space: `df -h`
4. Monitor memory: `free -h`
5. Check process: `top` or `htop`

## Next Steps

After successful computation:
1. Update production backend with new data files
2. Test frontend with full dataset
3. Monitor API response times
4. Consider caching strategies for frequently requested weights
5. Document any performance optimizations needed
