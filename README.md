```markdown
# 📚 MCMOL System - Meteorological Data Processing and Equivalent Rainfall

Automated system for processing meteorological radar data and calculating equivalent rainfall for civil protection decision support.

## 📋 Overview

The system consists of two Python scripts that work in sequence:

1. **MCMOL_cumulate_fixed.py**: Processes MCM radar data, generates cumulative precipitation maps and calculates percentile statistics
2. **Peq0_Automatized.py**: Calculates equivalent rainfall (Peq0) using the SCS-CN method for hydrological modeling

```
MCM Radar Archive (hourly TIF files)
         ↓
MCMOL_cumulate_fixed.py
├── Cumulative PNG maps (3h, 6h, 12h ... 120h)
├── Excel percentile files per zone
└── Quality control report
         ↓
Peq0_Automatized.py
├── Equivalent rainfall calculation
├── Current file Peq0_current.xlsx
└── Historical archive
```

## 🔧 Initial Setup

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/mcmol-system.git
cd mcmol-system
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**requirements.txt**:
```
rasterio>=1.3.0
geopandas>=0.12.0
numpy>=1.21.0
pandas>=1.4.0
matplotlib>=3.5.0
shapely>=2.0.0
openpyxl>=3.0.0
```

### 3. Create Configuration File

Create a `config.ini` file in the project root:

```ini
[PATHS]
# MCM radar data archive
# Structure: ARCHIVIO_MCM/YYYY/MM/DD/MCM_YYYYMMDDHH0000.tif
ARCHIVIO_MCM = /path/to/radar/archive/mergingArchive

# Temporary files directory for intermediate processing
DIR_TEMP = /path/to/temp/maps

# Homogeneous zones shapefile (WGS84, EPSG:4326)
# Must contain 'id' or 'ZONA_IM' attribute
SHAPEFILE_ZONE_IM = /path/to/shapefiles/Zone_IM_WGS84.shp

# Rivers shapefile for map overlay (optional)
SHAPEFILE_CORSI_ACQUA = /path/to/shapefiles/Rivers_WGS84.shp

# Cities shapefile for map overlay (optional)
SHAPEFILE_CAPOLUOGHI = /path/to/shapefiles/Cities_WGS84.shp

# Output directory (shared by both scripts)
# Maps, percentiles and Peq0 files will be saved here
DIR_OUTPUT = /path/to/output

# Curve Number rasters directory (for Peq0)
# Raster filenames must end with zone number (e.g., CN_basin_05.ASC)
DIR_RASTER_CN = /path/to/cn_rasters

# Cache file for CN values (JSON format)
FILE_CACHE_CN = /path/to/cache/cn_cache.json

[MCMOL]
# Cumulative durations to process (hours)
# Comma-separated list
DURATE_CUMULATE = 3,6,12,24,36,48,72,96,120

# Archive control parameters
# Total hours to check for completeness
ORE_CONTROLLO = 120

# Recent hours to exclude from check (potentially incomplete data)
ORE_ESCLUSE_RECENTI = 4

# Map visualization parameters
# Minimum value for color scale (mm)
VMIN = 0

# Maximum value for color scale (mm)
VMAX = 200

# Threshold for white color - values below this are shown as white (mm)
SOGLIA_BIANCO = 0.1

# Matplotlib colormap name
# Options: RdYlBu_r, jet, turbo, Spectral_r, coolwarm
COLORMAP = RdYlBu_r

# Graphic configuration
# Figure size in inches (width, height)
FIGSIZE_WIDTH = 7
FIGSIZE_HEIGHT = 6

# Font sizes
FONTSIZE_TITOLO = 7
FONTSIZE_LEGENDA = 7
FONTSIZE_ETICHETTE = 8

# Border line width for zones
LINEWIDTH_BORDI = 0.5

# Percentiles to calculate (comma-separated)
PERCENTILI = 50,75,95,99

[PEQ0]
# SCS-CN lambda parameter (initial abstraction ratio)
# Standard value for Italian basins: 0.2
LAMBDA = 0.2

# Input duration from MCMOL percentiles (hours)
# This determines which percentiles_X.xlsx file to read
INPUT_DURATION = 120
```

### 4. Verify Configuration

```bash
python verify_setup.py
```

This script verifies:
- Accessibility of configured paths
- Presence of required shapefiles
- Data archive validity
- Write permissions on output directories

## 📁 Required Data Structure

### MCM Radar Archive
```
mergingArchive/
├── YYYY/
│   └── MM/
│       └── DD/
│           └── MCM_YYYYMMDDHH0000.tif
```

### Homogeneous Zones Shapefile
- **Coordinate system**: WGS84 (EPSG:4326)
- **Required attributes**: `id` or `ZONA_IM` (numeric zone identifier)
- **Geometries**: Valid polygons

### Curve Number Rasters
- **Format**: ASCII Grid (.ASC)
- **Naming**: Filename must end with zone number (e.g., `CN_basin_05.ASC` → zone IM-05)
- **Coordinate system**: Consistent with zone IM shapefile

## 🚀 Usage

### Manual Execution

```bash
# 1. MCMOL processing (generates maps and percentiles)
python MCMOL_cumulate_fixed.py

# 2. Equivalent rainfall calculation (uses MCMOL output)
python Peq0_Automatized.py
```

### Automated Execution (Windows Task Scheduler)

**Task 1: MCMOL at 08:00 (daily)**
```
Action: Start a program
Program: C:\Python\python.exe
Arguments: C:\path\to\MCMOL_cumulate_fixed.py
Start in: C:\path\to\scripts
```

**Task 2: Peq0 at 08:45 (daily)**
```
Action: Start a program
Program: C:\Python\python.exe
Arguments: C:\path\to\Peq0_Automatized.py
Start in: C:\path\to\scripts
```

### Automated Execution (Linux Cron)

```bash
# Edit crontab
crontab -e

# Add these lines:
0 8 * * * /usr/bin/python3 /path/to/MCMOL_cumulate_fixed.py >> /path/to/logs/mcmol.log 2>&1
45 8 * * * /usr/bin/python3 /path/to/Peq0_Automatized.py >> /path/to/logs/peq0.log 2>&1
```

## 📊 Generated Output

### MCMOL_cumulate_fixed.py

**1. PNG Maps** (`DIR_OUTPUT/MCMOL_Xh.png`)
- 9 cumulative maps (one per duration: 3h, 6h, 12h, 24h, 36h, 48h, 72h, 96h, 120h)
- 150 DPI resolution
- Color scale: White (0mm) → Blue → Yellow → Red (200mm)
- Zone labels and boundaries overlay

**2. Excel Percentile Files** (`DIR_OUTPUT/percentiles_X.xlsx`)
- 9 Excel files (one per duration)
- Structure: `IM | p50 | p75 | p95 | p99`
- Spatial statistics per homogeneous zone
- Values rounded to 1 decimal place

**3. Notification File** (`DIR_OUTPUT/mail_output.txt`)
- First line: `YES` (send notification) or `NO`
- HTML content for Power Automate integration
- Archive problems report (missing/corrupted files)

### Peq0_Automatized.py

**1. Current File** (`DIR_OUTPUT/Peq0_current.xlsx`)
- Calculated equivalent rainfall per zone
- Structure: `IM | p50 | p75 | p95 | p99` (Peq0 values in mm)
- Overwritten at each execution
- Values rounded to 2 decimal places

**2. Historical Archive** (`DIR_OUTPUT/YYYY/MM/Peq0_YYYYMMDD.xlsx`)
- Daily copy for historicization
- Automatic organization by year/month
- Preserves data for trend analysis

## 🔬 Technical Notes

### Peq0 Formula (Modified SCS-CN)

The equivalent rainfall is calculated using the modified SCS-CN method:

```
S = 25400/CN - 254
M = max(0, √[S × (P + ((1-λ)/2)² × S)] - ((1+λ)/2) × S)
Peq0 = M × (1 + λ × S/(S + M))
```

Where:
- **S**: Maximum potential retention (mm)
- **CN**: Curve Number of the zone (from raster)
- **P**: Cumulative precipitation (from MCMOL percentiles)
- **λ**: Initial abstraction parameter (default 0.2)
- **M**: Intermediate calculation value

> **Reference**: USDA-NRCS National Engineering Handbook, Part 630 Hydrology

### Archive Quality Control

MCMOL automatically verifies data integrity:
- Checks last 120 hours of data (excluding 4 most recent hours)
- Identifies missing, empty or corrupted files
- Generates notification email if problems detected
- Continues processing with available files

### CN Cache System

Peq0 optimizes performance through intelligent caching:
- Calculates average CN per zone only at first execution
- Stores results in JSON cache file
- Automatically invalidates cache if rasters are modified
- Reduces processing time from ~5 minutes to ~30 seconds

### Color Scale Interpretation

Maps use a continuous color scale to represent precipitation:

| Color | Range (mm) | Interpretation |
|-------|------------|----------------|
| White | 0 - 0.1 | No precipitation |
| Light Blue | 0.1 - 10 | Light rain |
| Dark Blue | 10 - 30 | Moderate rain |
| Green-Yellow | 30 - 60 | Heavy rain |
| Orange | 60 - 100 | Very heavy rain |
| Red | 100 - 200 | Intense rain |
| Dark Red | > 200 | Extreme event |

## 🐛 Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| `FileNotFoundError: config.ini` | Create `config.ini` file in project root based on example above |
| `Shapefile CRS error` | Verify shapefile is in WGS84 (EPSG:4326) using QGIS or similar |
| `PermissionError Excel` | Close any open Excel files and pause cloud sync (OneDrive, Dropbox) |
| `MemoryError` | Reduce `DURATE_CUMULATE` list or increase available RAM |
| `CN zone not found` | Verify CN raster naming - must end with zone number (e.g., `_05.ASC`) |
| Missing radar files | Check archive connectivity and MCM acquisition system status |
| Empty or corrupted TIF | Verify radar processing pipeline and disk space |

### Verification Steps

**1. Test configuration:**
```python
python -c "from MCMOL_cumulate_fixed import config; print('Output:', config.PATH_OUTPUT)"
```

**2. Test shapefile reading:**
```python
import geopandas as gpd
gdf = gpd.read_file('/path/to/Zone_IM_WGS84.shp')
print(f"Zones: {len(gdf)}, CRS: {gdf.crs}")
```

**3. Test raster CN:**
```python
import rasterio
with rasterio.open('/path/to/CN_basin_05.ASC') as src:
    print(f"CN mean: {src.read(1).mean():.1f}")
```

**4. Check archive:**
```bash
# Linux/Mac
ls -lh /path/to/mergingArchive/$(date +%Y/%m/%d)/*.tif

# Windows
dir /path/to/mergingArchive\%date:~-4%\%date:~-7,2%\%date:~-10,2%\*.tif
```

## 📝 Maintenance

### Regular Tasks

**Daily:**
- Verify output files are generated
- Check `mail_output.txt` for problems
- Monitor disk space usage

**Weekly:**
- Review processing logs
- Verify archive completeness
- Check cache validity

**Monthly:**
- Archive old log files
- Verify shapefile integrity
- Update CN rasters if land use changed

### Cleanup Script

Remove temporary files after processing:

```python
import os
from pathlib import Path

def cleanup_temp():
    """Remove temporary files"""
    temp_files = [
        Path(config.DIR_MAPPE_TEMP) / "merge_ITALY.tif",
        Path(config.DIR_MAPPE_TEMP) / "merge_immagine.tif"
    ]
    
    for f in temp_files:
        if f.exists():
            f.unlink()
            print(f"✓ Removed: {f.name}")

cleanup_temp()
```

### Updating Shapefiles

When updating homogeneous zones:

1. **Backup** existing shapefile
2. **Verify** new shapefile has:
   - WGS84 (EPSG:4326) projection
   - Required attributes (`id` or `ZONA_IM`)
   - Valid geometries
3. **Update** `config.ini` path if filename changed
4. **Regenerate** all CN rasters for new zones
5. **Delete** CN cache: `rm /path/to/cn_cache.json`
6. **Test** with one duration first

## 🔗 Integration

### Power Automate Integration

The system can integrate with Microsoft Power Automate for automatic email notifications:

**Flow Setup:**
1. **Trigger**: Monitor `mail_output.txt` file
2. **Condition**: Check if first line = "YES"
3. **Action**: Send email with HTML body from file content
4. **Recipients**: Civil protection distribution list

**Example Flow (JSON):**
```json
{
  "trigger": {
    "type": "OnFileModified",
    "path": "DIR_OUTPUT/mail_output.txt"
  },
  "condition": {
    "firstLine": "YES"
  },
  "action": {
    "type": "SendEmail",
    "importance": "High"
  }
}
```

### API Integration

To integrate MCMOL output with other systems, read the generated Excel files:

```python
import pandas as pd

# Read percentiles
df_perc = pd.read_excel('DIR_OUTPUT/percentiles_24.xlsx')

# Read equivalent rainfall
df_peq0 = pd.read_excel('DIR_OUTPUT/Peq0_current.xlsx')

# Access by zone
zone_5_p95 = df_perc[df_perc['IM'] == 5]['p95'].values[0]
print(f"Zone 5 - P95: {zone_5_p95:.1f} mm")
```

## 📄 License

[Specify your license here - e.g., MIT, GPL-3.0, etc.]

## 👥 Authors and Contact

**Developed by:** [Your Name/Organization]

**Contact:** [your.email@domain.com]

**Issues:** Report bugs and request features via [GitHub Issues](https://github.com/yourusername/mcmol-system/issues)

## 🙏 Acknowledgments

- Radar data provided by [Organization]
- Based on SCS-CN methodology (USDA-NRCS)
- Developed for civil protection operational use

## 📚 References

1. USDA-NRCS (2004). National Engineering Handbook, Part 630 Hydrology
2. Chow, V.T., Maidment, D.R., Mays, L.W. (1988). Applied Hydrology
3. [Add other relevant references]

---

**Note**: This system is designed for operational use in civil protection and flood risk management. It requires MCM radar data and area-specific shapefiles. For questions or support, please contact the development team.
```
