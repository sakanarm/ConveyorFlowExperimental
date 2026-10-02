$ErrorActionPreference = "Stop"

python -m pip install -r requirements.txt
python -m pytest tests -q
python scripts/download_data.py
python scripts/prepare_data.py
python scripts/run_main.py --check-design

Write-Host "Preflight complete. To execute all 22,500 runs, run:"
Write-Host "python scripts/run_main.py --workers 8"
Write-Host "python scripts/analyze_main.py"
Write-Host "python scripts/analyze_secondary_extensions.py --workers 8"
Write-Host "python scripts/verify_artifacts.py --output results/main"
