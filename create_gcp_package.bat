@echo off
REM GCP Deployment Package Creator (Windows)
REM Creates a zip file with all necessary files for grid computation

echo Creating GCP deployment package...

REM Create temporary directory
set TEMP_DIR=gcp_deployment_temp
if exist %TEMP_DIR% rmdir /s /q %TEMP_DIR%
mkdir %TEMP_DIR%

REM Copy scripts
echo Copying computation scripts...
mkdir %TEMP_DIR%\jobs\scripts
copy jobs\scripts\30_compute_monte_carlo_grid.py %TEMP_DIR%\jobs\scripts\
copy jobs\scripts\40_compute_stress_tests_grid.py %TEMP_DIR%\jobs\scripts\

REM Copy data files
echo Copying data files...
mkdir %TEMP_DIR%\data
copy data\covariance_matrices.npz %TEMP_DIR%\data\
copy data\clean_prices.parquet %TEMP_DIR%\data\

REM Create requirements.txt
echo Creating requirements.txt...
(
echo numpy==1.26.4
echo pandas==2.2.0
echo pyarrow==15.0.0
echo tqdm==4.66.1
) > %TEMP_DIR%\requirements.txt

REM Create README
echo Creating README...
(
echo # Portfolio Grid Computation Package
echo.
echo This package contains scripts and data for generating portfolio weight grid lookup tables.
echo.
echo ## Contents
echo.
echo - `jobs/scripts/30_compute_monte_carlo_grid.py` - Monte Carlo grid generator
echo - `jobs/scripts/40_compute_stress_tests_grid.py` - Stress Test grid generator
echo - `data/covariance_matrices.npz` - Covariance matrices
echo - `data/clean_prices.parquet` - Historical price data
echo - `requirements.txt` - Python dependencies
echo.
echo ## Quick Start
echo.
echo 1. Setup environment:
echo    ```bash
echo    python3 -m venv venv
echo    source venv/bin/activate
echo    pip install -r requirements.txt
echo    ```
echo.
echo 2. Run Monte Carlo computation (2-4 hours^):
echo    ```bash
echo    python jobs/scripts/30_compute_monte_carlo_grid.py
echo    ```
echo.
echo 3. Run Stress Test computation (5-10 minutes^):
echo    ```bash
echo    python jobs/scripts/40_compute_stress_tests_grid.py
echo    ```
echo.
echo ## Output Files
echo.
echo - `data/monte_carlo_grid.parquet` (~12 GB^)
echo - `data/monte_carlo_grid_weights.parquet` (~3 GB^)
echo - `data/stress_tests_grid.parquet` (~400 MB^)
echo - `data/stress_tests_grid_weights.parquet` (~100 MB^)
echo.
echo ## System Requirements
echo.
echo - Python 3.10+
echo - 60+ CPU cores (recommended for Monte Carlo^)
echo - 240+ GB RAM (recommended for Monte Carlo^)
echo - 50+ GB disk space
echo.
echo See GCP_DEPLOYMENT_GUIDE.md for detailed instructions.
) > %TEMP_DIR%\README.md

REM Create zip file using PowerShell
echo Creating zip file...
powershell -command "Compress-Archive -Path '%TEMP_DIR%\*' -DestinationPath 'gcp-grid-computation.zip' -Force"

REM Cleanup
echo Cleaning up...
rmdir /s /q %TEMP_DIR%

REM Show result
echo.
echo ✓ Deployment package created: gcp-grid-computation.zip
echo.
dir gcp-grid-computation.zip
echo.
echo Next steps:
echo 1. Upload to GCP: gcloud compute scp gcp-grid-computation.zip INSTANCE_NAME:~/
echo 2. Extract on GCP: unzip gcp-grid-computation.zip
echo 3. Follow instructions in GCP_DEPLOYMENT_GUIDE.md
echo.
pause
