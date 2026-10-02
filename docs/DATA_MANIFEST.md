# Data Manifest and License Gate

| ID | Canonical source | Planned local object | License status | Pilot role |
|---|---|---|---|---|
| adult | https://archive.ics.uci.edu/static/public/2/adult.zip | `data/raw/adult.zip` | CC BY 4.0 verified | ML classification characteristics |
| beijing | https://archive.ics.uci.edu/static/public/501/beijing%2Bmulti%2Bsite%2Bair%2Bquality%2Bdata.zip | `data/raw/beijing.zip` | CC BY 4.0 verified | ML regression and time-series characteristics |
| bugs2fix-small | Microsoft CodeXGLUE raw files | `data/raw/bugs2fix/` | C-UDA; do not redistribute raw corpus | Fix Bug distribution only |

`scripts/download_data.py` records SHA-256, byte size and download time in `data/manifest.json` Raw files are gitignored Derived aggregate profiles may be committed because they contain no source records
