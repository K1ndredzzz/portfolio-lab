#!/bin/bash
# GCP Deployment Package Creator
# Creates a tarball with all necessary files for grid computation

set -e

echo "Creating GCP deployment package..."

# Create temporary directory
TEMP_DIR="gcp_deployment_temp"
mkdir -p $TEMP_DIR

# Copy scripts
echo "Copying computation scripts..."
mkdir -p $TEMP_DIR/jobs/scripts
cp jobs/scripts/30_compute_monte_carlo_grid.py $TEMP_DIR/jobs/scripts/
cp jobs/scripts/40_compute_stress_tests_grid.py $TEMP_DIR/jobs/scripts/

# Copy data files
echo "Copying data files..."
mkdir -p $TEMP_DIR/data
cp data/covariance_matrices.npz $TEMP_DIR/data/
cp data/clean_prices.parquet $TEMP_DIR/data/

# Create requirements.txt
echo "Creating requirements.txt..."
cat > $TEMP_DIR/requirements.txt << EOF
numpy==1.26.4
pandas==2.2.0
pyarrow==15.0.0
tqdm==4.66.1
EOF

# Create README
echo "Creating README..."
cat > $TEMP_DIR/README.md << EOF
# Portfolio Grid Computation Package

This package contains scripts and data for generating portfolio weight grid lookup tables.

## Contents

- \`jobs/scripts/30_compute_monte_carlo_grid.py\` - Monte Carlo grid generator
- \`jobs/scripts/40_compute_stress_tests_grid.py\` - Stress Test grid generator
- \`data/covariance_matrices.npz\` - Covariance matrices
- \`data/clean_prices.parquet\` - Historical price data
- \`requirements.txt\` - Python dependencies

## Quick Start

1. Setup environment:
   \`\`\`bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   \`\`\`

2. Run Monte Carlo computation (2-4 hours):
   \`\`\`bash
   python jobs/scripts/30_compute_monte_carlo_grid.py
   \`\`\`

3. Run Stress Test computation (5-10 minutes):
   \`\`\`bash
   python jobs/scripts/40_compute_stress_tests_grid.py
   \`\`\`

## Output Files

- \`data/monte_carlo_grid.parquet\` (~12 GB)
- \`data/monte_carlo_grid_weights.parquet\` (~3 GB)
- \`data/stress_tests_grid.parquet\` (~400 MB)
- \`data/stress_tests_grid_weights.parquet\` (~100 MB)

## System Requirements

- Python 3.10+
- 60+ CPU cores (recommended for Monte Carlo)
- 240+ GB RAM (recommended for Monte Carlo)
- 50+ GB disk space

See GCP_DEPLOYMENT_GUIDE.md for detailed instructions.
EOF

# Create tarball
echo "Creating tarball..."
tar -czf gcp-grid-computation.tar.gz -C $TEMP_DIR .

# Cleanup
echo "Cleaning up..."
rm -rf $TEMP_DIR

# Show result
echo ""
echo "✓ Deployment package created: gcp-grid-computation.tar.gz"
echo ""
ls -lh gcp-grid-computation.tar.gz
echo ""
echo "Next steps:"
echo "1. Upload to GCP: gcloud compute scp gcp-grid-computation.tar.gz INSTANCE_NAME:~/"
echo "2. Extract on GCP: tar -xzf gcp-grid-computation.tar.gz"
echo "3. Follow instructions in GCP_DEPLOYMENT_GUIDE.md"
