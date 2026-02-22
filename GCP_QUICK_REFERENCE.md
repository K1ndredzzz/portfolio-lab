# GCP Computation Quick Reference

## 🚀 Quick Start Commands

### 1. Create Package (Windows)
```cmd
create_gcp_package.bat
```

### 2. Create GCP Instance
```bash
gcloud compute instances create portfolio-grid-compute \
  --zone=us-central1-a \
  --machine-type=c2-standard-60 \
  --preemptible \
  --boot-disk-size=100GB \
  --boot-disk-type=pd-ssd \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud
```

### 3. Upload Package
```bash
gcloud compute scp gcp-grid-computation.zip portfolio-grid-compute:~/ --zone=us-central1-a
```

### 4. SSH and Setup
```bash
gcloud compute ssh portfolio-grid-compute --zone=us-central1-a

# On instance:
unzip gcp-grid-computation.zip
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Run Computations
```bash
# Monte Carlo (2-4 hours)
nohup python jobs/scripts/30_compute_monte_carlo_grid.py > mc.log 2>&1 &

# Stress Test (5-10 minutes)
nohup python jobs/scripts/40_compute_stress_tests_grid.py > st.log 2>&1 &

# Monitor
tail -f mc.log
```

### 6. Download Results
```bash
# Exit SSH, then from local:
gcloud compute scp portfolio-grid-compute:~/data/*_grid*.parquet ./data/ --zone=us-central1-a
```

### 7. Cleanup
```bash
gcloud compute instances delete portfolio-grid-compute --zone=us-central1-a --quiet
```

## 📊 Expected Results

| File | Size | Rows |
|------|------|------|
| monte_carlo_grid.parquet | ~12 GB | ~6,023,000 |
| monte_carlo_grid_weights.parquet | ~3 GB | 136,894 |
| stress_tests_grid.parquet | ~400 MB | ~411,000 |
| stress_tests_grid_weights.parquet | ~100 MB | 136,894 |

## 💰 Cost Estimate

- **Total**: ~$15 USD
- **Time**: ~3-4 hours
- **Instance**: c2-standard-60 preemptible

## 🔍 Monitoring Commands

```bash
# Check progress
gcloud compute ssh portfolio-grid-compute --zone=us-central1-a --command="tail -50 ~/mc.log"

# Check disk space
gcloud compute ssh portfolio-grid-compute --zone=us-central1-a --command="df -h"

# Check process
gcloud compute ssh portfolio-grid-compute --zone=us-central1-a --command="ps aux | grep python"
```

## ⚠️ Important Notes

1. **Preemptible instances** can be terminated - use checkpointing if needed
2. **Don't forget to delete** the instance after downloading results
3. **Verify file sizes** before deleting the instance
4. **Backup test data** before replacing with production data

## 📝 Post-Deployment Checklist

- [ ] Download all 4 parquet files
- [ ] Verify file sizes match expected values
- [ ] Delete GCP instance
- [ ] Backup test data files
- [ ] Replace test data with production data
- [ ] Restart backend service
- [ ] Test API with custom weights
- [ ] Monitor API response times

## 🆘 Troubleshooting

**Out of Memory**:
- Reduce batch size in scripts
- Use larger instance (c2-standard-60 → c2-standard-120)

**Disk Full**:
- Increase boot disk size (100GB → 200GB)

**Process Killed**:
- Check logs: `tail -100 mc.log`
- Verify input files exist
- Check system resources: `free -h`, `df -h`

**Slow Progress**:
- Normal for Monte Carlo (137K combinations × 10K simulations)
- Expected: ~30-40 combinations per minute

## 📚 Documentation

- Full guide: `GCP_DEPLOYMENT_GUIDE.md`
- Test report: `WEIGHT_INTERPOLATION_TEST_REPORT.md`
- Scripts: `jobs/scripts/30_compute_monte_carlo_grid.py`, `40_compute_stress_tests_grid.py`
