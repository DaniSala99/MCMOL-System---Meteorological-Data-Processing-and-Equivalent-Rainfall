# MCMOL-System---Meteorological-Data-Processing-and-Equivalent-Rainfall
Automated system for processing meteorological radar data and calculating equivalent rainfall for civil protection decision support.

📋 OverviewThe system consists of two Python scripts that work in sequence:
MCMOL_cumulate_fixed.py: Processes MCM radar data, generates cumulative precipitation maps and calculates percentile statistics
Peq0_Automatized.py: Calculates equivalent rainfall (Peq0) using the SCS-CN method for hydrological modeling
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
└── Historical archive🔧 Initial Setup1. Clone the Repository
bashgit clone https://github.com/yourusername/mcmol-system.git
cd mcmol-system2. Create Configuration FileCreate a config.ini file in the project root:ini[PATHS]
# MCM radar data archive
ARCHIVIO_MCM = /path/to/radar/archive/mergingArchive

# Temporary files directory
DIR_TEMP = /path/to/temp/maps

# Homogeneous zones shapefile
SHAPEFILE_ZONE_IM = /path/to/shapefiles/Zone_IM.shp
SHAPEFILE_CORSI_ACQUA = /path/to/shapefiles/Rivers.shp
SHAPEFILE_CAPOLUOGHI = /path/to/shapefiles/Cities.shp

# Output directory (shared by both scripts)
DIR_OUTPUT = /path/to/output

# Curve Number rasters (for Peq0)
DIR_RASTER_CN = /path/to/cn_rasters
FILE_CACHE_CN = /path/to/cache/cn_cache.json

[MCMOL]
# Cumulative durations to process (hours)
DURATE_CUMULATE = 3,6,12,24,36,48,72,96,120

# Archive control parameters
ORE_CONTROLLO = 120
ORE_ESCLUSE_RECENTI = 4

# Map parameters
VMIN = 0
VMAX = 200
SOGLIA_BIANCO = 0.1
COLORMAP = RdYlBu_r

# Graphic settings
FIGSIZE_WIDTH = 7
FIGSIZE_HEIGHT = 6
FONTSIZE_TITOLO = 7
FONTSIZE_LEGENDA = 7
FONTSIZE_ETICHETTE = 8
LINEWIDTH_BORDI = 0.5

# Percentiles to calculate
PERCENTILI = 50,75,95,99

[PEQ0]
# SCS-CN lambda parameter
LAMBDA = 0.2

# Input file from MCMOL
INPUT_DURATION = 1203. Install Dependenciesbashpip install -r requirements.txtrequirements.txt:
rasterio>=1.3.0
geopandas>=0.12.0
numpy>=1.21.0
pandas>=1.4.0
matplotlib>=3.5.0
shapely>=2.0.0
openpyxl>=3.0.04. Verify Configurationbashpython verify_setup.pyThis script verifies:

Accessibility of configured paths
Presence of required shapefiles
Data archive validity
Write permissions on output directories
📁 Required Data StructureMCM Radar Archive
mergingArchive/
├── YYYY/
│   └── MM/
│       └── DD/
│           └── MCM_YYYYMMDDHH0000.tifHomogeneous Zones Shapefile

Coordinate system: WGS84 (EPSG:4326)
Required attributes: id or ZONA_IM (numeric zone identifier)
Geometries: Valid polygons
Curve Number Rasters

Format: ASCII Grid (.ASC)
Naming: Filename must end with zone number (e.g., CN_basin_05.ASC → zone IM-05)
Coordinate system: Consistent with zone IM shapefile
🚀 UsageManual Executionbash# 1. MCMOL processing (generates maps and percentiles)
python MCMOL_cumulate_fixed.py

# 2. Equivalent rainfall calculation (uses MCMOL output)
python Peq0_Automatized.pyAutomated Execution (Windows)Task Scheduler:

Task 1: MCMOL at 08:00 (daily)
Task 2: Peq0 at 08:45 (daily)
Task Configuration:
Action: Start a program
Program: C:\Python\python.exe
Arguments: C:\path\to\MCMOL_cumulate_fixed.py
Start in: C:\path\to\scripts📊 Generated OutputMCMOL_cumulate_fixed.pyPNG Maps (DIR_OUTPUT/MCMOL_Xh.png):

9 cumulative maps (one per duration)
150 DPI resolution
Color scale: White (0mm) → Blue → Yellow → Red (200mm)
Excel Percentile Files (DIR_OUTPUT/percentiles_X.xlsx):

9 Excel files (one per duration)
Columns: IM | p50 | p75 | p95 | p99
Spatial statistics per homogeneous zone
Notification File (DIR_OUTPUT/mail_output.txt):

First line: YES (send notification) or NO
HTML content for Power Automate integration
Archive problems report (missing/corrupted files)
Peq0_Automatized.pyCurrent File (DIR_OUTPUT/Peq0_current.xlsx):

Calculated equivalent rainfall per zone
Structure: IM | p50 | p75 | p95 | p99 (Peq0 values in mm)
Overwritten at each execution
Historical Archive (DIR_OUTPUT/YYYY/MM/Peq0_YYYYMMDD.xlsx):

Daily copy for historicization
Automatic organization by year/month
🔬 Technical NotesPeq0 Formula (Modified SCS-CN)S = 25400/CN - 254
M = max(0, √[S × (P + ((1-λ)/2)² × S)] - ((1+λ)/2) × S)
Peq0 = M × (1 + λ × S/(S + M))Where:

CN: Zone Curve Number (from raster)
P: Cumulative precipitation (from MCMOL percentiles)
λ: Initial abstraction parameter (default 0.2)

Reference: USDA-NRCS National Engineering Handbook, Part 630 Hydrology
Archive Quality ControlMCMOL automatically verifies:

Last 120 hours of data (excluding 4 most recent hours)
Identifies missing, empty or corrupted files
Generates notification if problems > 0
CN Cache SystemPeq0 uses JSON cache to optimize performance:

Calculates average CN per zone only at first execution
Automatically invalidates cache if rasters are modified
Reduces processing time from ~5 minutes to ~30 seconds
🐛 TroubleshootingProblemSolutionFileNotFoundError: config.iniCreate config.ini file in project rootShapefile CRS errorVerify shapefile is in WGS84 (EPSG:4326)PermissionError ExcelClose open Excel files and pause OneDrive syncMemoryErrorReduce processed durations or increase available RAMCN zone not foundVerify CN raster naming (must end with zone number)Setup Verificationpython# Quick configuration test
python -c "from MCMOL_cumulate_fixed import Config; print(Config.PATH_OUTPUT)"📝 MaintenanceTemporary Files Cleanup
bash# Remove temp files after processing
rm DIR_TEMP/merge_ITALY.tif
rm DIR_TEMP/merge_immagine.tifUpdating Zone IM Shapefile

Backup existing shapefile
Replace with new shapefile (same name or modify config.ini)
Verify CRS and attributes compatibility
Important: Regenerate all CN rasters for new zones
📄 License[Specify license]👥 Authors[Specify authors/contacts]Note: System developed for operational use in civil protection. Requires MCM radar data and area-specific shapefiles.
