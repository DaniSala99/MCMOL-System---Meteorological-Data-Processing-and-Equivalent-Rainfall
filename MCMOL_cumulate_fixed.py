import rasterio
import rasterio.plot
import rasterio.mask
from rasterio.mask import mask
from rasterio import CRS
import geopandas as gpd
import numpy as np
from datetime import datetime, timedelta
import os
from matplotlib import pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.colors as mcolors
import pandas as pd
from shapely.geometry import mapping
import logging
import configparser
from pathlib import Path

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
        
        # Main paths
        self.RADICE_ARCHIVIO = config.get('PATHS', 'ARCHIVIO_MCM')
        self.DIR_MAPPE_TEMP = config.get('PATHS', 'DIR_TEMP')
        self.PATH_OUTPUT = config.get('PATHS', 'DIR_OUTPUT')
        
        # Shapefiles
        self.SHAPE_ZONE_IM = config.get('PATHS', 'SHAPEFILE_ZONE_IM')
        self.SHAPE_CORSI_ACQUA = config.get('PATHS', 'SHAPEFILE_CORSI_ACQUA')
        self.SHAPE_CAPOLUOGHI = config.get('PATHS', 'SHAPEFILE_CAPOLUOGHI')
        
        # File parameters
        self.PREFISSO_FILE = "MCM_"
        self.MINUTO_CORRENTE = "0000"
        
        # Cumulative durations to process (hours)
        durate_str = config.get('MCMOL', 'DURATE_CUMULATE')
        self.DURATE_CUMULATE = [int(x.strip()) for x in durate_str.split(',')]
        
        # Archive control parameters
        self.ORE_CONTROLLO_ARCHIVIO = config.getint('MCMOL', 'ORE_CONTROLLO')
        self.ORE_ESCLUSE_RECENTI = config.getint('MCMOL', 'ORE_ESCLUSE_RECENTI')
        
        # Map configuration - Color scales
        self.VMIN = config.getfloat('MCMOL', 'VMIN')
        self.VMAX = config.getfloat('MCMOL', 'VMAX')
        self.SOGLIA_BIANCO = config.getfloat('MCMOL', 'SOGLIA_BIANCO')
        self.COLORMAP = config.get('MCMOL', 'COLORMAP')
        
        # Graphic configuration
        width = config.getfloat('MCMOL', 'FIGSIZE_WIDTH')
        height = config.getfloat('MCMOL', 'FIGSIZE_HEIGHT')
        self.FIGSIZE = (width, height)
        self.FONTSIZE_TITOLO = config.getint('MCMOL', 'FONTSIZE_TITOLO')
        self.FONTSIZE_LEGENDA = config.getint('MCMOL', 'FONTSIZE_LEGENDA')
        self.FONTSIZE_ETICHETTE = config.getint('MCMOL', 'FONTSIZE_ETICHETTE')
        self.LINEWIDTH_BORDI = config.getfloat('MCMOL', 'LINEWIDTH_BORDI')
        
        # Percentiles to calculate
        percentili_str = config.get('MCMOL', 'PERCENTILI')
        self.PERCENTILI = [int(x.strip()) for x in percentili_str.split(',')]
        
        # Create output directories if they don't exist
        os.makedirs(self.PATH_OUTPUT, exist_ok=True)
        os.makedirs(self.DIR_MAPPE_TEMP, exist_ok=True)

# Load configuration
config = Config()

# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def verifica_file_tiff(file_path):
    """
    Verify if a TIFF file is readable and not corrupted
    
    Args:
        file_path: Complete file path
        
    Returns:
        True if file is valid, False otherwise
    """
    try:
        with rasterio.open(file_path) as src:
            meta = src.meta
            data_sample = src.read(
                1, 
                window=rasterio.windows.Window(
                    0, 0, 
                    min(100, src.width), 
                    min(100, src.height)
                )
            )
            return True
    except Exception as e:
        logger.warning(f"Corrupted file: {file_path} - Error: {str(e)}")
        return False


def scrivi_file_mail_output(deve_inviare_mail, contenuto_mail=""):
    """
    Write a text file with instructions for Power Automate
    First line: "YES" if should send mail, "NO" otherwise
    Following lines: email content in HTML (if should be sent)
    
    Args:
        deve_inviare_mail: True if should send mail, False otherwise
        contenuto_mail: Email message content (plain text)
        
    Returns:
        True if file was created successfully
    """
    file_output_mail = os.path.join(config.PATH_OUTPUT, "mail_output.txt")
    
    try:
        with open(file_output_mail, 'w', encoding='utf-8') as f:
            if deve_inviare_mail:
                f.write("YES\n")
                # Convert line breaks to HTML <br> to preserve formatting
                contenuto_html = contenuto_mail.replace('\n', '<br>')
                f.write(contenuto_html)
            else:
                f.write("NO\n")
                f.write("No email to send - complete archive")
        
        logger.info(f"Mail output file created: {file_output_mail}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating mail output file: {str(e)}")
        return False

# ============================================================================
# ARCHIVE CONTROL FUNCTIONS
# ============================================================================

def controlla_file_archivio_completo(ora_inizio_processo):
    """
    Check all TIF files in specified interval
    
    Args:
        ora_inizio_processo: Process start timestamp
        
    Returns:
        Tuple (file_mancanti, file_corrotti) - lists of filenames
    """
    print("\n" + "="*70)
    print("ARCHIVE COMPLETENESS CHECK")
    print("="*70)
    
    # Calculate time interval
    ora_limite = ora_inizio_processo - timedelta(hours=config.ORE_ESCLUSE_RECENTI)
    ora_inizio_controllo = ora_limite - timedelta(hours=config.ORE_CONTROLLO_ARCHIVIO)
    
    print(f"Period: {ora_inizio_controllo.strftime('%Y-%m-%d %H:%M')} "
          f"- {ora_limite.strftime('%Y-%m-%d %H:%M')}")
    
    file_mancanti = []
    file_corrotti = []
    file_trovati = 0
    
    # Generate list of hours to check
    ore_da_controllare = []
    ora_corrente = ora_inizio_controllo
    while ora_corrente <= ora_limite:
        ore_da_controllare.append(ora_corrente)
        ora_corrente += timedelta(hours=1)
    
    print(f"Expected files: {len(ore_da_controllare)}")
    
    # Check each file
    for ora_check in ore_da_controllare:
        nome_file = (f"{config.PREFISSO_FILE}"
                    f"{ora_check.strftime('%Y%m%d%H')}"
                    f"{config.MINUTO_CORRENTE}.tif")
        
        path_file = costruisci_path_file(ora_check, nome_file)
        
        if not os.path.isfile(path_file):
            file_mancanti.append(nome_file)
        else:
            file_size = os.path.getsize(path_file)
            if file_size == 0:
                file_corrotti.append(f"{nome_file} (empty file)")
            elif not verifica_file_tiff(path_file):
                file_corrotti.append(f"{nome_file} (corrupted file)")
            else:
                file_trovati += 1
    
    # Report
    print(f"Valid files found: {file_trovati}/{len(ore_da_controllare)}")
    if file_mancanti:
        print(f"Missing files: {len(file_mancanti)}")
    if file_corrotti:
        print(f"Corrupted files: {len(file_corrotti)}")
    
    return file_mancanti, file_corrotti


def costruisci_path_file(ora, nome_file):
    """Build complete path of a file in the archive"""
    anno = ora.strftime('%Y')
    mese = ora.strftime('%m')
    giorno = ora.strftime('%d')
    return os.path.join(config.RADICE_ARCHIVIO, anno, mese, giorno, nome_file)

# ============================================================================
# PERCENTILES CALCULATION
# ============================================================================

def calcolo_percentili(durata, raster_path):
    """
    Calculate percentiles for IM homogeneous zones
    
    Args:
        durata: Cumulative duration in hours
        raster_path: Raster file path
    """
    try:
        print(f">>> PERCENTILES {durata}h - Start")
        
        # Preliminary checks
        if not os.path.isfile(raster_path):
            print(f"✗ PERCENTILES {durata}h - Raster file not found")
            return
        
        if not os.path.isfile(config.SHAPE_ZONE_IM):
            print(f"✗ PERCENTILES {durata}h - Shapefile not found")
            return

        # Read shapefile
        gdf = gpd.read_file(config.SHAPE_ZONE_IM)

        # Calculate percentiles for each zone
        risultati = []
        with rasterio.open(raster_path) as src:
            for idx, row in gdf.iterrows():
                geom = [mapping(row['geometry'])]
                try:
                    out_image, out_transform = mask(
                        src, geom, crop=True, all_touched=True
                    )
                    data = out_image[0]
                    valid = data[data != src.nodata]
                    
                    if valid.size > 0:
                        percs = np.percentile(valid, config.PERCENTILI)
                    else:
                        percs = [np.nan] * len(config.PERCENTILI)
                    
                    risultati.append({
                        'id': row.get('id', idx),
                        **{f'p{p}': v for p, v in zip(config.PERCENTILI, percs)}
                    })
                except Exception:
                    risultati.append({
                        'id': row.get('id', idx),
                        **{f'p{p}': np.nan for p in config.PERCENTILI}
                    })

        # Save Excel
        df_risultati = pd.DataFrame(risultati)
        df_risultati = df_risultati.rename(columns={"id": "IM"})
        df_risultati["IM"] += 1
        
        excel_file_path = os.path.join(
            config.PATH_OUTPUT, 
            f"percentiles_{durata}.xlsx"
        )
        df_risultati.round(1).to_excel(excel_file_path, index=False)
        
        # Verify creation
        if os.path.isfile(excel_file_path):
            file_size = os.path.getsize(excel_file_path)
            print(f"✓ PERCENTILES {durata}h - Excel created ({file_size} bytes)")
            print(df_risultati.round(1))
        else:
            print(f"✗ PERCENTILES {durata}h - Excel NOT created")
            
    except Exception as e:
        print(f"✗ PERCENTILES {durata}h - ERROR: {str(e)}")
        logger.exception("Error in percentiles calculation")

# ============================================================================
# CUMULATIVE CALCULATION AND MAP CREATION
# ============================================================================

def calcolo_cumulata(durata_cumulata):
    """
    Calculate rainfall cumulative for specified duration
    
    Args:
        durata_cumulata: Duration in hours
        
    Returns:
        Tuple (success, problematic_files) where success is bool
    """
    print(f'\n{"="*70}')
    print(f"CUMULATIVE PROCESSING {durata_cumulata}h")
    print("="*70)
    
    lista_file = []
    file_problematici = []
    
    # Determine last available file
    current_dateTime = datetime.now()
    anno = current_dateTime.strftime("%Y")
    mese = current_dateTime.strftime("%m")
    giorno = current_dateTime.strftime("%d")
    path_oggi = os.path.join(config.RADICE_ARCHIVIO, anno, mese, giorno)
    
    try:
        dir_list = os.listdir(path_oggi)
        ultimo_file = dir_list[-1]
        anno = ultimo_file[4:8]
        mese = ultimo_file[8:10]
        giorno = ultimo_file[10:12]
        ora = ultimo_file[12:14]
    except Exception as e:
        logger.error(f"Cannot access directory: {path_oggi}")
        return False, []
    
    # Calculate time range
    ora_ultimo_file = datetime.strptime(
        f"{anno}{mese}{giorno} {ora}", 
        "%Y%m%d %H"
    )
    ora_primo_file = ora_ultimo_file - timedelta(hours=durata_cumulata)
    lista_date = [
        ora_primo_file + timedelta(hours=i+1) 
        for i in range(durata_cumulata)
    ]
    
    print(f"Period: {ora_primo_file.strftime('%Y-%m-%d %H:%M')} "
          f"- {ora_ultimo_file.strftime('%Y-%m-%d %H:%M')}")
    
    # File collection and verification
    for date in lista_date:
        nome_file = (f"{config.PREFISSO_FILE}"
                    f"{date.strftime('%Y%m%d%H')}"
                    f"{config.MINUTO_CORRENTE}.tif")
        
        file_completo = costruisci_path_file(date, nome_file)
        
        if not os.path.isfile(file_completo):
            file_problematici.append(f"{nome_file} (missing)")
            logger.warning(f"Missing file: {nome_file}")
        else:
            file_size = os.path.getsize(file_completo)
            if file_size == 0:
                file_problematici.append(f"{nome_file} (empty)")
                logger.warning(f"Empty file: {nome_file}")
            elif not verifica_file_tiff(file_completo):
                file_problematici.append(f"{nome_file} (corrupted)")
                logger.warning(f"Corrupted file: {nome_file}")
            else:
                lista_file.append(file_completo)
    
    print(f"Valid files: {len(lista_file)}/{durata_cumulata}")
    if file_problematici:
        print(f"Problematic files: {len(file_problematici)}")
        for f in file_problematici[:5]:  # Show only first 5
            print(f"  - {f}")
        if len(file_problematici) > 5:
            print(f"  ... and {len(file_problematici)-5} more")
    
    # Minimum verification of available files
    if len(lista_file) == 0:
        print(f"✗ CUMULATIVE {durata_cumulata}h - NO VALID FILES")
        return False, file_problematici
    
    # Sum TIFs
    print(f"Summing {len(lista_file)} files...")
    try:
        with rasterio.open(lista_file[0], 'r+') as src:
            src.crs = CRS.from_epsg(4326)
            data = src.read(1)
            meta = src.meta.copy()
        
        files_sommati = 1
        for i in range(1, len(lista_file)):
            try:
                with rasterio.open(lista_file[i]) as src_temp:
                    data_temp = src_temp.read(1)
                    data = data + data_temp
                    files_sommati += 1
            except Exception as e:
                nome_file = os.path.basename(lista_file[i])
                logger.warning(f"Skipped file during sum: {nome_file}")
                continue

        print(f"Files summed successfully: {files_sommati}/{durata_cumulata}")
        
    except Exception as e:
        print(f"✗ CUMULATIVE {durata_cumulata}h - SUM ERROR: {str(e)}")
        logger.exception("Error during file summing")
        return False, file_problematici
    
    # Verify valid data
    if data is None or data.size == 0:
        print(f"✗ CUMULATIVE {durata_cumulata}h - INVALID DATA")
        return False, file_problematici

    print(f"Data: shape={data.shape}, min={data.min():.2f}, max={data.max():.2f}")
    
    # Save intermediate file
    merge_italy_path = os.path.join(config.DIR_MAPPE_TEMP, "merge_ITALY.tif")
    with rasterio.open(merge_italy_path, 'w', **meta) as dst:
        dst.write(data, 1)

    # Clip with IM zones shapefile
    shapefile = gpd.read_file(config.SHAPE_ZONE_IM)
    shapes = shapefile.geometry

    with rasterio.open(merge_italy_path) as src:
        out_image, out_transform = rasterio.mask.mask(
            src, shapes, crop=True, all_touched=True, nodata=-9999
        )
        out_meta = src.meta
        
    out_meta.update({
        "driver": "GTiff",
        "height": out_image.shape[1],
        "width": out_image.shape[2],
        "transform": out_transform,
        "nodata": -9999
    })
                    
    # Save clipped merge
    merge_immagine_path = os.path.join(config.DIR_MAPPE_TEMP, "merge_immagine.tif")
    with rasterio.open(merge_immagine_path, 'w', **out_meta) as dst_bacini:
        dst_bacini.write(out_image)
    
    # Verify file created
    if not os.path.isfile(merge_immagine_path):
        print(f"✗ CUMULATIVE {durata_cumulata}h - merge_immagine.tif NOT CREATED")
        return False, file_problematici
    
    file_size = os.path.getsize(merge_immagine_path)
    if file_size == 0:
        print(f"✗ CUMULATIVE {durata_cumulata}h - merge_immagine.tif EMPTY")
        return False, file_problematici
    
    print(f"merge_immagine.tif created: {file_size} bytes")
    
    # Map creation
    successo_mappa = crea_mappa(
        durata_cumulata, 
        merge_immagine_path, 
        shapefile, 
        len(file_problematici)
    )
    
    if not successo_mappa:
        return False, file_problematici
    
    # Percentiles calculation
    calcolo_percentili(durata_cumulata, merge_immagine_path)
    
    print(f"✓ CUMULATIVE {durata_cumulata}h - Completed")
    return True, file_problematici


def crea_mappa(durata, raster_path, shapefile, num_file_problematici):
    """
    Create graphical map of cumulative
    
    Args:
        durata: Duration in hours
        raster_path: Raster file path
        shapefile: GeoDataFrame with zones
        num_file_problematici: Number of problematic files
        
    Returns:
        True if map was created successfully
    """
    try:
        src = rasterio.open(raster_path)
        data = src.read(1)
        
        fig, ax = plt.subplots(figsize=config.FIGSIZE)
        extent = [src.bounds[0], src.bounds[2], src.bounds[1], src.bounds[3]]
        
        # Title
        titolo = f'Cumulative rainfall {durata}h'
        if num_file_problematici > 0:
            titolo += f'\n(Problematic files: {num_file_problematici})'
        plt.title(titolo + '\n', fontsize=config.FONTSIZE_TITOLO)
        plt.axis('off')
        
        # Create custom colormap: white for 0, then blue->red
        cmap_base = plt.colormaps.get_cmap(config.COLORMAP)
        
        # Create new colormap with white for low values
        colors_list = ['white']  # White for 0
        # Add colors from base colormap for values > threshold
        n_colors = 256
        for i in range(n_colors):
            colors_list.append(cmap_base(i / n_colors))
        
        cmap_custom = LinearSegmentedColormap.from_list('custom', colors_list, N=257)
        
        # Mask very low values (0) to render them white
        data_masked = np.ma.masked_where(data < config.SOGLIA_BIANCO, data)
        
        # Custom normalization: 0-0.1 -> white, 0.1-200 -> color scale
        norm = mcolors.Normalize(vmin=config.VMIN, vmax=config.VMAX)
        
        # Plot raster with mask
        im = ax.imshow(
            data_masked,
            extent=extent,
            cmap=cmap_custom,
            norm=norm,
            interpolation='nearest'
        )
        
        # Plot shapefile
        shapefile.plot(
            ax=ax, 
            edgecolor='black', 
            facecolor='None', 
            linewidth=config.LINEWIDTH_BORDI
        )
        
        # IM zone labels
        shapefile['coords'] = shapefile['geometry'].apply(
            lambda x: x.representative_point().coords[:]
        )
        shapefile['coords'] = [coords[0] for coords in shapefile['coords']]
        
        for idx, row in shapefile.iterrows():
            ax.text(
                row.coords[0], row.coords[1], 
                s=row['ZONA_IM'], 
                horizontalalignment='center', 
                bbox={
                    'facecolor': 'None', 
                    'alpha': 0.8, 
                    'pad': 2, 
                    'edgecolor': 'none'
                },
                fontsize=config.FONTSIZE_LEGENDA
            )
        
        # Continuous colorbar (only for values > 0.1)
        cax = fig.add_axes([0.74, 0.38, 0.02, 0.4])
        cbar = plt.colorbar(
            im, 
            cax=cax,
            fraction=0.03, 
            pad=0.02, 
            shrink=0.8
        )
        cbar.ax.tick_params(labelsize=config.FONTSIZE_ETICHETTE)
        cbar.set_label(
            'Cumulative values in [mm]', 
            fontsize=config.FONTSIZE_LEGENDA, 
            labelpad=-1
        )
        
        # Save
        output_path = os.path.join(
            config.PATH_OUTPUT, 
            f"MCMOL_{durata}h.png"
        )
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"Map saved: MCMOL_{durata}h.png")
        return True
        
    except Exception as e:
        print(f"✗ Error creating map: {str(e)}")
        logger.exception("Error in map creation")
        return False

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    """Main orchestration function"""
    
    print("="*70)
    print("MCMOL - CUMULATIVE RAINFALL MAPS")
    print("="*70)
    
    # Start timestamp
    ora_inizio_processo = datetime.now()
    print(f"Process started: {ora_inizio_processo.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Cumulative processing
    risultati_elaborazione = {}
    
    for durata in config.DURATE_CUMULATE:
        try:
            successo, file_problematici = calcolo_cumulata(durata)
            risultati_elaborazione[durata] = {
                'successo': successo,
                'problemi': len(file_problematici),
                'file_problematici': file_problematici
            }
        except Exception as e:
            print(f"✗ CRITICAL ERROR {durata}h: {str(e)}")
            logger.exception(f"Critical error during {durata}h processing")
            risultati_elaborazione[durata] = {
                'successo': False,
                'problemi': -1,
                'file_problematici': []
            }
    
    # Processing summary
    print("\n" + "="*70)
    print("PROCESSING SUMMARY")
    print("="*70)
    
    file_mancanti_elaborazione = []
    
    for durata in config.DURATE_CUMULATE:
        excel_file = os.path.join(config.PATH_OUTPUT, f"percentiles_{durata}.xlsx")
        mappa_file = os.path.join(config.PATH_OUTPUT, f"MCMOL_{durata}h.png")
        
        excel_ok = "✓" if os.path.isfile(excel_file) else "✗"
        mappa_ok = "✓" if os.path.isfile(mappa_file) else "✗"
        
        status = risultati_elaborazione.get(durata, {})
        problemi = status.get('problemi', 0)
        
        print(f"{durata:3}h: Excel {excel_ok} | Map {mappa_ok} | "
              f"Problematic files: {problemi}")
        
        if not os.path.isfile(excel_file):
            file_mancanti_elaborazione.append(durata)
    
    if file_mancanti_elaborazione:
        print(f"\n⚠️ Missing Excel files for: {file_mancanti_elaborazione}")
    else:
        print(f"\n✅ All files completed successfully")
    
    # Archive control
    print("\n" + "="*70)
    print("ARCHIVE CONTROL")
    print("="*70)
    
    file_mancanti_archivio, file_corrotti_archivio = controlla_file_archivio_completo(
        ora_inizio_processo
    )
    
    # Email notification management
    totale_problemi = len(file_mancanti_archivio) + len(file_corrotti_archivio)
    
    if totale_problemi == 0:
        print("\n✅ COMPLETE ARCHIVE - No email to send")
        scrivi_file_mail_output(False)
    else:
        print(f"\n⚠️ PROBLEMS DETECTED ({totale_problemi}) - "
              f"Preparing notification email")
        
        contenuto_mail = genera_contenuto_mail(
            ora_inizio_processo,
            file_mancanti_archivio,
            file_corrotti_archivio,
            file_mancanti_elaborazione
        )
        
        scrivi_file_mail_output(True, contenuto_mail)
    
    print("\n" + "="*70)
    print("PROCESS COMPLETED")
    print("="*70)


def genera_contenuto_mail(ora_inizio, file_mancanti, file_corrotti, mappe_mancanti):
    """
    Generate notification mail content
    
    Returns:
        String with formatted mail content
    """
    totale_problemi = len(file_mancanti) + len(file_corrotti)
    
    ora_limite = ora_inizio - timedelta(hours=config.ORE_ESCLUSE_RECENTI)
    ora_inizio_controllo = ora_limite - timedelta(hours=config.ORE_CONTROLLO_ARCHIVIO)
    
    oggetto = f"MCMOL - ARCHIVE PROBLEMS REPORT ({totale_problemi} files)"
    
    contenuto = f"""Subject: {oggetto}

MCM ARCHIVE CONTROL REPORT - {ora_inizio.strftime('%Y-%m-%d %H:%M:%S')}

CHECKED PERIOD: {ora_inizio_controllo.strftime('%Y-%m-%d %H:%M')} - {ora_limite.strftime('%Y-%m-%d %H:%M')}

SUMMARY:
- Expected files: {config.ORE_CONTROLLO_ARCHIVIO}
- Missing files: {len(file_mancanti)}
- Corrupted files: {len(file_corrotti)}
- Total problems: {totale_problemi}
"""

    if len(file_mancanti) > 0:
        contenuto += f"\n\nMISSING FILES ({len(file_mancanti)}):\n"
        for i, file_name in enumerate(file_mancanti[:20], 1):
            contenuto += f"{i:2}. {file_name}\n"
        if len(file_mancanti) > 20:
            contenuto += f"... and {len(file_mancanti) - 20} more files\n"

    if len(file_corrotti) > 0:
        contenuto += f"\n\nCORRUPTED FILES ({len(file_corrotti)}):\n"
        for i, file_name in enumerate(file_corrotti[:20], 1):
            contenuto += f"{i:2}. {file_name}\n"
        if len(file_corrotti) > 20:
            contenuto += f"... and {len(file_corrotti) - 20} more files\n"

    contenuto += f"""

MAP PROCESSING STATUS:
- Completed maps: {len(config.DURATE_CUMULATE) - len(mappe_mancanti)} of {len(config.DURATE_CUMULATE)}
"""
    
    if len(mappe_mancanti) > 0:
        contenuto += f"- Maps with problems: {mappe_mancanti}\n"
    
    contenuto += """
It is recommended to verify the correct functioning of the MCM acquisition system.

This message is automatically generated by the MCMOL monitoring system.
"""
    
    return contenuto


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception("Critical error in program execution")
        print(f"\n✗ CRITICAL ERROR: {str(e)}")
        
        # In case of critical error, still create output file
        contenuto_errore = f"""Subject: MCMOL - CRITICAL ERROR

CRITICAL ERROR in MCMOL process
Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Error: {str(e)}

The process has been interrupted. Check logs for more details.
"""
        scrivi_file_mail_output(True, contenuto_errore)