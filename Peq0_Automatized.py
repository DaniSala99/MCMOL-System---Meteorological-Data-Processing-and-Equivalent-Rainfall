from __future__ import annotations

import json
import os
import re
import shutil
import datetime
import configparser
from pathlib import Path
from typing import Dict, Any

import numpy as np
import pandas as pd
import rasterio

# ============================================================================
# CONFIGURATION LOADING
# ============================================================================

class Config:
    """Centralized system configuration from config.ini file"""
    
    def __init__(self, config_file='config.ini'):
        if not os.path.exists(config_file):
            raise FileNotFoundError(
                f"Configuration file '{config_file}' not found. "
                "Please create it based on config.ini.example"
            )
        
        config = configparser.ConfigParser()
        config.read(config_file)
        
        # Paths
        self.OUTPUT_DIR = Path(config.get('PATHS', 'DIR_OUTPUT'))
        self.RASTER_FOLDER = Path(config.get('PATHS', 'DIR_RASTER_CN'))
        self.CACHE_PATH = Path(config.get('PATHS', 'FILE_CACHE_CN'))
        
        # Input/Output files
        input_duration = config.getint('PEQ0', 'INPUT_DURATION')
        self.INPUT_XLSX = self.OUTPUT_DIR / f"percentiles_{input_duration}.xlsx"
        self.OUTPUT_FILE_CORRENTE = self.OUTPUT_DIR / "Peq0_current.xlsx"
        self.ARCHIVE_ROOT = self.OUTPUT_DIR
        
        # Parameters
        self.LAMBDA = config.getfloat('PEQ0', 'LAMBDA')
        
        # Create directories if they don't exist
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

# Load configuration
config = Config()

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def calcola_peq0(p5: float | np.ndarray, cn: float | np.ndarray, lam: float = None):
    """
    Calculate Peq0 using modified SCS-CN method
    
    Args:
        p5: Precipitation (mm)
        cn: Curve Number
        lam: Lambda parameter (initial abstraction ratio)
        
    Returns:
        Equivalent rainfall Peq0 (mm)
    """
    if lam is None:
        lam = config.LAMBDA
        
    s = 25400 / cn - 254
    sqrt_term = s * (p5 + ((1 - lam) / 2) ** 2 * s)
    m = np.maximum(np.sqrt(sqrt_term) - ((1 + lam) / 2) * s, 0)
    return m * (1 + lam * s / (s + m))


def calcola_cn_per_zone(folder: Path, cache: Path) -> Dict[str, float]:
    """
    Calculate average Curve Number for each zone from rasters
    Uses cache to optimize performance
    
    Args:
        folder: Directory containing CN raster files (.ASC)
        cache: Cache file path (JSON)
        
    Returns:
        Dictionary {zone: average_CN}
    """
    if cache.exists():
        try:
            data = json.loads(cache.read_text())
            if all(os.path.getmtime(p) == data["mtimes"].get(p) for p in data["mtimes"]):
                print("✓ Average CNs loaded from cache.")
                return {k: float(v) for k, v in data["zone_cn"].items()}
        except Exception as exc:
            print("⚠️  Cache damaged or obsolete:", exc)

    print("→ Calculating average Curve Numbers…")
    zone_cn, mtimes = {}, {}
    for asc in sorted(folder.glob("*.ASC")):
        m = re.search(r"(\d{1,2})$", asc.stem)
        if not m:
            print("  › Raster", asc.name, ": missing zone number – skipping.")
            continue
        key = f"IM-{int(m.group()):02d}"
        with rasterio.open(asc) as src:
            zone_cn[key] = float(np.ma.mean(src.read(1, masked=True)))
        mtimes[str(asc)] = os.path.getmtime(asc)
        print(f"  • Average CN {key}: {zone_cn[key]:6.1f}")

    cache.write_text(json.dumps({"zone_cn": zone_cn, "mtimes": mtimes}, indent=2))
    print("→ Cache saved at", cache)
    return zone_cn


def normalizza_zona(z: Any) -> str | None:
    """
    Normalize zone identifier to canonical format "IM-05"
    
    Args:
        z: Zone identifier (can be int, float, string in various formats)
        
    Returns:
        Normalized zone string "IM-XX" or None if not recognized
    """
    if z is None or (isinstance(z, float) and np.isnan(z)):
        return None

    # Try numeric (int or float like 1.0)
    try:
        num = float(z)
        if num.is_integer() and 0 < num < 100:
            return f"IM-{int(num):02d}"
    except Exception:
        pass

    z_str = str(z).strip().upper().replace(" ", "")
    if re.fullmatch(r"IM\d{1,2}", z_str):
        return f"IM-{int(z_str[2:]):02d}"
    if re.fullmatch(r"IM-\d{1,2}", z_str):
        return f"IM-{int(z_str[3:]):02d}"
    return None


def process_sheet(df: pd.DataFrame, zone_cn: Dict[str, float]) -> pd.DataFrame:
    """
    Process Excel sheet: calculate Peq0 for each zone and percentile
    
    Args:
        df: Input DataFrame with percentiles
        zone_cn: Dictionary with average CN per zone
        
    Returns:
        DataFrame with Peq0 values
    """
    out = df.copy(deep=True)
    zone_col = out.columns[0]
    val_cols = out.columns[1:]

    for idx, row in out.iterrows():
        key = normalizza_zona(row[zone_col])
        if not key:
            print(f"⚠️  Row {idx}: zone '{row[zone_col]}' ignored (format not recognized)")
            continue
        if key not in zone_cn:
            print(f"⚠️  Row {idx}: zone {key} not present in rasters – skipping")
            continue
        cn = zone_cn[key]
        p5 = row[val_cols].to_numpy(dtype=float)
        out.loc[idx, val_cols] = np.round(calcola_peq0(p5, cn), 2)
    return out

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    """Main execution function"""
    
    print("="*70)
    print("PEQ0 - EQUIVALENT RAINFALL CALCULATION")
    print("="*70)
    
    # Verify input file exists
    if not config.INPUT_XLSX.exists():
        raise FileNotFoundError(
            f"Input file not found: {config.INPUT_XLSX}\n"
            f"Make sure MCMOL_cumulate_fixed.py has been executed first."
        )
    
    if not config.RASTER_FOLDER.is_dir():
        raise NotADirectoryError(
            f"CN rasters directory not found: {config.RASTER_FOLDER}"
        )

    # Calculate average CNs
    print("\nStep 1: Loading Curve Numbers")
    print("-" * 70)
    zones = calcola_cn_per_zone(config.RASTER_FOLDER, config.CACHE_PATH)
    
    # Prepare paths for archiving
    oggi = datetime.date.today()
    cartella_mese = config.ARCHIVE_ROOT / f"{oggi.year}" / f"{oggi.month:02d}"
    cartella_mese.mkdir(parents=True, exist_ok=True)
    output_archivio = cartella_mese / f"Peq0_{oggi.strftime('%Y%m%d')}.xlsx"
    
    # Process data
    print("\nStep 2: Processing percentiles")
    print("-" * 70)
    xls = pd.ExcelFile(config.INPUT_XLSX)
    
    # Write current output
    with pd.ExcelWriter(config.OUTPUT_FILE_CORRENTE, engine="openpyxl") as writer_corrente:
        for sheet in xls.sheet_names:
            print(f"→ Converting sheet '{sheet}' for current output...")
            df = process_sheet(xls.parse(sheet), zones)
            df.to_excel(writer_corrente, sheet_name=sheet, index=False)
    
    print(f"\n✓ Current output saved at {config.OUTPUT_FILE_CORRENTE}")
    
    # Write historical archive (copy of current file)
    shutil.copy2(config.OUTPUT_FILE_CORRENTE, output_archivio)
    print(f"✓ Historical archive saved at {output_archivio}")
    
    print("\n" + "="*70)
    print("PROCESS COMPLETED SUCCESSFULLY")
    print("="*70)

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)