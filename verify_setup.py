"""
Verify MCMOL system configuration
"""

import os
import configparser
from pathlib import Path

def verify_setup():
    """Verify all required paths and files exist"""
    
    print("="*70)
    print("MCMOL SYSTEM CONFIGURATION VERIFICATION")
    print("="*70)
    
    # Check config file
    if not os.path.exists('config.ini'):
        print("\n✗ ERROR: config.ini not found")
        print("  Please create config.ini based on config.ini.example")
        return False
    
    print("\n✓ config.ini found")
    
    # Load config
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    errors = []
    warnings = []
    
    # Check paths
    print("\nChecking paths...")
    print("-" * 70)
    
    paths_to_check = {
        'ARCHIVIO_MCM': ('PATHS', 'ARCHIVIO_MCM', True),
        'DIR_TEMP': ('PATHS', 'DIR_TEMP', False),
        'SHAPEFILE_ZONE_IM': ('PATHS', 'SHAPEFILE_ZONE_IM', True),
        'DIR_OUTPUT': ('PATHS', 'DIR_OUTPUT', False),
        'DIR_RASTER_CN': ('PATHS', 'DIR_RASTER_CN', True),
    }
    
    for name, (section, key, must_exist) in paths_to_check.items():
        path = Path(config.get(section, key))
        
        if path.exists():
            print(f"  ✓ {name}: {path}")
        elif must_exist:
            print(f"  ✗ {name}: {path} (NOT FOUND)")
            errors.append(f"{name} not found: {path}")
        else:
            print(f"  ⚠ {name}: {path} (will be created)")
            warnings.append(f"{name} will be created: {path}")
    
    # Check write permissions on output
    try:
        output_dir = Path(config.get('PATHS', 'DIR_OUTPUT'))
        output_dir.mkdir(parents=True, exist_ok=True)
        test_file = output_dir / '.write_test'
        test_file.write_text('test')
        test_file.unlink()
        print(f"\n✓ Write permissions OK on output directory")
    except Exception as e:
        print(f"\n✗ Cannot write to output directory: {e}")
        errors.append(f"Write permission error: {e}")
    
    # Summary
    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)
    
    if errors:
        print(f"\n✗ {len(errors)} ERROR(S) found:")
        for err in errors:
            print(f"  - {err}")
    
    if warnings:
        print(f"\n⚠ {len(warnings)} WARNING(S):")
        for warn in warnings:
            print(f"  - {warn}")
    
    if not errors:
        print("\n✅ Configuration is valid!")
        print("   You can now run MCMOL_cumulate_fixed.py")
        return True
    else:
        print("\n❌ Please fix errors before running the system")
        return False

if __name__ == "__main__":
    verify_setup()