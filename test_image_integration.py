#!/usr/bin/env python3
"""
Integration test for image storage and transmission system
Verifies all components are properly configured and functional
"""

import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_config(config_path: str) -> bool:
    """Test that config has all required image storage settings"""
    logger.info("Testing config.yaml...")
    
    try:
        import yaml
        with open(config_path) as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return False
    
    # Check required sections
    required_sections = [
        ('image_storage', 'Image storage configuration'),
        ('batching', 'Batch transmission settings'),
        ('communication', 'Communication settings'),
    ]
    
    all_ok = True
    for section, desc in required_sections:
        if section in config:
            logger.info(f"✓ {section}: {desc}")
        else:
            logger.error(f"✗ {section}: MISSING")
            all_ok = False
    
    # Check critical settings
    if config.get('communication', {}).get('ground_station_ip') == '0.0.0.0':
        logger.warning("⚠ ground_station_ip is still 0.0.0.0 - MUST UPDATE")
        all_ok = False
    else:
        logger.info(f"✓ ground_station_ip: {config['communication']['ground_station_ip']}")
    
    logger.info(f"✓ ground_station_port: {config['communication'].get('ground_station_port', 'NOT SET')}")
    logger.info(f"✓ protocol: {config['communication'].get('protocol', 'NOT SET')}")
    logger.info(f"✓ batch_size: {config['batching'].get('batch_size', 'NOT SET')}")
    
    return all_ok


def test_image_manager_import() -> bool:
    """Test that ImageManager can be imported"""
    logger.info("\nTesting ImageManager import...")
    
    try:
        from Raspberry_Pi_Agent.image_manager import ImageManager, StorageManager, ImageTransmitter
        logger.info("✓ ImageManager imported successfully")
        logger.info("✓ StorageManager imported successfully")
        logger.info("✓ ImageTransmitter imported successfully")
        return True
    except ImportError as e:
        logger.error(f"✗ Import failed: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}")
        return False


def test_capture_controller_integration() -> bool:
    """Test that CaptureController has ImageManager integration"""
    logger.info("\nTesting CaptureController integration...")
    
    try:
        with open('Raspberry_Pi_Agent/Mission_Controller/capture_controller.py') as f:
            content = f.read()
        
        checks = [
            ('self.image_manager', 'ImageManager parameter'),
            ('self.current_altitude', 'Altitude tracking'),
            ('image_manager.save_captured_image', 'Image saving integration'),
            ('set_altitude', 'Altitude setter method'),
        ]
        
        all_ok = True
        for check_str, desc in checks:
            if check_str in content:
                logger.info(f"✓ {desc}")
            else:
                logger.error(f"✗ {desc}: NOT FOUND")
                all_ok = False
        
        return all_ok
    
    except Exception as e:
        logger.error(f"✗ Error checking capture_controller.py: {e}")
        return False


def test_notmain_integration() -> bool:
    """Test that notmain.py has ImageManager integration"""
    logger.info("\nTesting notmain.py integration...")
    
    try:
        with open('Raspberry_Pi_Agent/notmain.py') as f:
            content = f.read()
        
        checks = [
            ('from Raspberry_Pi_Agent.image_manager import ImageManager', 'ImageManager import'),
            ('self.image_manager = ImageManager', 'ImageManager instantiation'),
            ('image_manager.start_transmission', 'Transmission start'),
            ('image_manager.stop_transmission', 'Transmission stop'),
            ('capture_controller.set_altitude', 'Altitude update'),
            ('transmit_batch', 'Batch transmission call'),
        ]
        
        all_ok = True
        for check_str, desc in checks:
            if check_str in content:
                logger.info(f"✓ {desc}")
            else:
                logger.error(f"✗ {desc}: NOT FOUND")
                all_ok = False
        
        return all_ok
    
    except Exception as e:
        logger.error(f"✗ Error checking notmain.py: {e}")
        return False


def test_files_exist() -> bool:
    """Test that required files exist"""
    logger.info("\nTesting required files...")
    
    files = [
        ('Raspberry_Pi_Agent/image_manager.py', 'ImageManager implementation'),
        ('ground_station_receiver.py', 'Ground station receiver'),
        ('IMAGE_STORAGE_AND_TRANSMISSION.md', 'Documentation'),
        ('Raspberry_Pi_Agent/config.yaml', 'Configuration'),
    ]
    
    all_ok = True
    for filepath, desc in files:
        if Path(filepath).exists():
            size_kb = Path(filepath).stat().st_size / 1024
            logger.info(f"✓ {desc} ({size_kb:.1f} KB)")
        else:
            logger.error(f"✗ {desc}: FILE NOT FOUND")
            all_ok = False
    
    return all_ok


def test_directory_structure() -> bool:
    """Test that directory structure can be created"""
    logger.info("\nTesting directory structure...")
    
    try:
        dirs = [
            'mission_data',
            'mission_data/images',
            'mission_data/metadata',
            'mission_data/tx_queue',
            'mission_data/sent',
        ]
        
        for dirname in dirs:
            Path(dirname).mkdir(parents=True, exist_ok=True)
            logger.info(f"✓ {dirname}")
        
        return True
    
    except Exception as e:
        logger.error(f"✗ Error creating directories: {e}")
        return False


def main():
    """Run all integration tests"""
    logger.info("="*60)
    logger.info("Image Storage & Transmission Integration Tests")
    logger.info("="*60)
    
    config_path = 'Raspberry_Pi_Agent/config.yaml'
    
    results = {
        'Files Exist': test_files_exist(),
        'Configuration': test_config(config_path),
        'ImageManager Import': test_image_manager_import(),
        'CaptureController Integration': test_capture_controller_integration(),
        'notmain.py Integration': test_notmain_integration(),
        'Directory Structure': test_directory_structure(),
    }
    
    logger.info("\n" + "="*60)
    logger.info("Test Summary")
    logger.info("="*60)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    
    logger.info("="*60)
    if all_passed:
        logger.info("✓ ALL TESTS PASSED")
        logger.info("\nNext steps:")
        logger.info("1. Update ground_station_ip in config.yaml to your ground station IP")
        logger.info("2. Start ground station receiver: python ground_station_receiver.py")
        logger.info("3. Run mission: python -m Raspberry_Pi_Agent.notmain")
        return 0
    else:
        logger.error("✗ SOME TESTS FAILED - Review errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
