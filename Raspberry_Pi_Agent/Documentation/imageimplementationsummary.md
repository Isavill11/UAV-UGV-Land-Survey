# Image Storage and Transmission System - Implementation Summary

## Completed Tasks

### 1. ✅ ImageManager Core Implementation
- **File**: `Raspberry_Pi_Agent/image_manager.py` (600+ lines)
- **Components**:
  - `StorageManager`: Local filesystem image storage with metadata persistence
  - `ImageTransmitter`: UDP/TCP transmission with RSSI-based adaptive batching
  - `ImageManager`: High-level orchestration API
- **Features**:
  - Automatic metadata generation (timestamp, altitude, profile, MD5)
  - Thread-safe image transmission queue
  - Storage space management with automatic cleanup
  - Recovery from system restarts via JSON metadata index

### 2. ✅ CaptureController Integration
- **File**: `Raspberry_Pi_Agent/Mission_Controller/capture_controller.py`
- **Changes**:
  - Added `image_manager` parameter to constructor
  - Added `current_altitude` tracking for image metadata
  - Updated `_capture_frame()` to use ImageManager.save_captured_image()
  - Added `set_altitude()` method for updating drone altitude
- **Result**: Images now automatically captured with metadata and stored via ImageManager

### 3. ✅ Main Mission Loop Integration
- **File**: `Raspberry_Pi_Agent/notmain.py`
- **Changes**:
  - Imported ImageManager class
  - Instantiate ImageManager in `__init__`
  - Pass ImageManager to CaptureController
  - Start transmission thread after MAVLink setup
  - Update altitude in main loop from DroneHealth
  - Trigger adaptive image transmission based on RSSI link quality
  - Stop transmission gracefully on shutdown with statistics logging
- **Result**: Complete end-to-end workflow from capture → storage → transmission

### 4. ✅ Configuration Updates
- **File**: `Raspberry_Pi_Agent/config.yaml`
- **Additions**:
  - `image_storage`: Directories, storage limits, cleanup thresholds
  - `batching`: Batch size and transmission timing
  - `communication`: Ground station IP/port, protocol, RSSI thresholds
  - Updated camera profiles to use `mission_data/images`
  - Auto-cleanup configuration
- **Features**:
  - All settings configurable via YAML
  - Placeholder IP addresses ready for deployment customization
  - RSSI thresholds: -50dBm (excellent), -70dBm (good), -85dBm (degraded), -100dBm (critical)

### 5. ✅ Ground Station Receiver
- **File**: `ground_station_receiver.py` (400+ lines)
- **Features**:
  - UDP and TCP protocol support
  - Receives custom image transmission packets
  - Verifies MD5 checksums
  - Organizes images by date and verification status
  - Saves associated metadata JSON files
  - Comprehensive logging and statistics
  - Command-line interface for configuration
- **Result**: Reference implementation for receiving and storing transmitted images

### 6. ✅ Documentation
- **File**: `IMAGE_STORAGE_AND_TRANSMISSION.md` (350+ lines)
- **Sections**:
  - Architecture overview with data flow diagrams
  - Configuration reference with all settings explained
  - Workflow documentation for each stage
  - Altitude integration explanation
  - Link quality-based transmission logic
  - Packet protocol specification
  - Storage management and cleanup strategy
  - Ground station setup instructions
  - Integration points for developers
  - Deployment checklist
  - Troubleshooting guide
  - Performance tuning recommendations
  - API reference

### 7. ✅ Integration Test Suite
- **File**: `test_image_integration.py`
- **Tests**:
  - Configuration completeness check
  - ImageManager import verification
  - CaptureController integration validation
  - notmain.py integration validation
  - Required files existence check
  - Directory structure creation
- **Usage**: `python test_image_integration.py`

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    UAV Raspberry Pi Agent                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────┐      ┌──────────────────┐                  │
│  │  CaptureFrame   │─────→│  ImageManager    │                  │
│  │   JPEG Bytes    │      │  (Orchestrator)  │                  │
│  └─────────────────┘      └────────┬─────────┘                  │
│                                    │                             │
│         ┌──────────────────────────┼──────────────────────────┐  │
│         │                          │                          │  │
│    ┌────▼─────────┐          ┌────▼──────────┐      ┌────────▼─┐│
│    │StorageManager│          │ImageTransmitter       │ Altitude ││
│    │              │          │                       │ Tracking ││
│    │ • images/    │          │ • UDP/TCP sender     │          ││
│    │ • metadata/  │          │ • RSSI-based batching│ From     ││
│    │ • tx_queue/  │          │ • MD5 checksums      │ Drone    ││
│    │ • sent/      │          │ • Thread-based       │ Health   ││
│    └──────────────┘          └────────────────────┘ └──────────┘│
│         │                            │                          │
│         └────────────────┬───────────┘                          │
│                          │                                      │
│                   Mission Data Stored                           │
│                   (2GB default limit)                           │
│                                                                   │
│    WiFi Link Quality                                            │
│    (RSSI -50 to -100 dBm)                                       │
│         │                                                        │
│         │  Adaptive Batching                                    │
│         │  • RSSI < -50:  10 images/batch                       │
│         │  • RSSI < -70:  10 images/batch                       │
│         │  • RSSI < -85:  5 images/batch                        │
│         │  • RSSI < -100: 0 images/batch (wait)               │
│         │                                                        │
└─────────┼────────────────────────────────────────────────────────┘
          │
          │ UDP/TCP Port 9999
          │
┌─────────▼───────────────────────────────────────────────────────┐
│              Ground Station (Windows/Linux)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │         ground_station_receiver.py                       │   │
│  │                                                          │   │
│  │  • Listens on 0.0.0.0:9999                              │   │
│  │  • Receives image packets                               │   │
│  │  • Verifies MD5 checksums                               │   │
│  │  • Organizes by date and status                         │   │
│  │  • Saves metadata JSON files                            │   │
│  └────────────┬──────────────────────────────────────────┘   │
│               │                                               │
│    ┌──────────┴────────────────────┐                         │
│    │   received_images/            │                         │
│    │   ├─ verified/                │                         │
│    │   │  ├─ 2026-02-17/          │                         │
│    │    │  │  ├─ IMG_*.jpg        │                         │
│    │    │  │  └─ IMG_*.jpg        │                         │
│    │    │  └─ 2026-02-18/         │                         │
│    │    ├─ unverified/            │                         │
│    │    ├─ failed/                │                         │
│    │    └─ metadata/              │                         │
│    │       ├─ IMG_*.jpg.json      │                         │
│    │       └─ IMG_*.jpg.json      │                         │
│    └──────────────────────────────┘                         │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

## Data Flow

### Image Capture
```
Drone Battery/Sensors (MAVLink)
    ↓ GPS_RAW_INT (altitude)
DroneHealth.altitude = 45.7m
    ↓
Mission Loop (10Hz)
    ↓
capture_controller.set_altitude(45.7)
    ↓
_capture_frame() captured JPEG
    ↓
image_manager.save_captured_image(bytes, profile, altitude)
    ├─ Generate MD5 hash
    ├─ Create metadata JSON
    ├─ Save image to mission_data/images/
    ├─ Update metadata index
    └─ Return filename
```

### Image Storage
```
mission_data/
├─ images/
│  ├─ IMG_20260217_134522_123.jpg  (captured image)
│  └─ IMG_20260217_134523_456.jpg
├─ metadata/
│  ├─ index.json                    (all images metadata)
│  ├─ IMG_20260217_134522_123.json  (per-image metadata)
│  └─ IMG_20260217_134523_456.json
├─ tx_queue/
│  └─ (images pending transmission)
└─ sent/
   └─ (successfully transmitted images - archive)
```

### Image Transmission
```
Mission Loop (10Hz)
    ↓
get RSSI from LinkHealth
    ↓
image_manager.transmit_batch(rssi)
    ├─ ImageTransmitter._calculate_batch_size(rssi)
    │  ├─ RSSI -50 → batch_size = 10
    │  ├─ RSSI -70 → batch_size = 10
    │  ├─ RSSI -85 → batch_size = 5
    │  └─ RSSI -100 → batch_size = 0
    ├─ Get pending images (max = batch_size)
    ├─ For each image:
    │  ├─ Create transmission packet:
    │  │  [Header|Filename|Metadata|Image|MD5]
    │  ├─ Send via UDP/TCP to ground_station_ip:9999
    │  ├─ Mark as transmitted on success
    │  └─ Retry on failure
    └─ Update transmission statistics
```

## Configuration Changes

### Before:
```yaml
camera:
  capture_profiles:
    CAPTURING:
      save_dir: captured_images/full

storage:
  local_path: ""
  
batching:
  batch_size: 0
  
communication:
  ground_station_ip: "0.0.0.0"
```

### After:
```yaml
camera:
  capture_profiles:
    CAPTURING:
      save_dir: mission_data/images

image_storage:
  base_path: "mission_data"
  max_storage_mb: 2000
  min_storage_mb_critical: 100

batching:
  batch_size: 10
  time_threshold_sec: 30

communication:
  protocol: "udp"
  ground_station_ip: "192.168.1.100"  # UPDATE THIS
  ground_station_port: 9999           # UPDATE THIS
  rssi_thresholds:
    excellent: -50
    good: -70
    degraded: -85
    critical: -100
```

## Deployment Checklist

- [ ] **Configure Network**
  - [ ] Raspberry Pi and Ground Station on same WiFi network
  - [ ] Note Ground Station IP address
  - [ ] Update `config.yaml`: `ground_station_ip`

- [ ] **Start Ground Station**
  - [ ] Run: `python ground_station_receiver.py --port 9999 --protocol udp`
  - [ ] Verify: "UDP listening on 0.0.0.0:9999"

- [ ] **Verify Integration**
  - [ ] Run: `python test_image_integration.py`
  - [ ] All tests should PASS

- [ ] **Start Mission**
  - [ ] Arm drone in AUTO mode
  - [ ] Observe images in `mission_data/images/`
  - [ ] Observe images in ground station `received_images/verified/`

- [ ] **Monitor Status**
  - [ ] Check storage: `image_manager.get_status()`
  - [ ] Check transmission: Ground station receiver output
  - [ ] Check metadata: `received_images/metadata/*.json`

## Files Created/Modified

### New Files (3)
1. `Raspberry_Pi_Agent/image_manager.py` (600+ lines)
   - ImageManager, StorageManager, ImageTransmitter classes
   
2. `ground_station_receiver.py` (400+ lines)
   - Ground station reference implementation
   
3. `IMAGE_STORAGE_AND_TRANSMISSION.md` (350+ lines)
   - Comprehensive documentation

4. `test_image_integration.py` (300+ lines)
   - Integration test suite

### Modified Files (3)
1. `Raspberry_Pi_Agent/notmain.py`
   - Import ImageManager
   - Instantiate ImageManager
   - Integrate altitude updates
   - Trigger batch transmission

2. `Raspberry_Pi_Agent/Mission_Controller/capture_controller.py`
   - Accept ImageManager parameter
   - Track altitude
   - Save images via ImageManager
   - Add set_altitude() method

3. `Raspberry_Pi_Agent/config.yaml`
   - Added image_storage section
   - Updated batching section
   - Enhanced communication section
   - Updated camera save directories

## Feature Highlights

### 1. Link-Quality Aware Transmission
- Automatically scales batch size based on RSSI signal strength
- Full batches on excellent link (-50 dBm)
- Half batches on degraded link (-85 dBm)
- No transmission on critical link (-100 dBm)

### 2. Automatic Storage Management
- Tracks available disk space
- Cleanup triggered at configured thresholds
- Prioritizes deletion of old/already-sent images
- Prevents data loss due to storage limits

### 3. Data Integrity
- MD5 checksums on every image
- Verified on ground station
- Images organized as verified/unverified
- Failed transmissions retry automatically

### 4. Metadata Tracking
- Image captured with: timestamp, altitude, profile, coordinates
- JSON persistence for mission replay
- Searchable metadata on ground station
- Recovery from system crashes

### 5. Thread-Safe Operation
- Background transmission thread
- Queue-based image handling
- Safe concurrent access to metadata
- Graceful shutdown procedures

## Testing

### Run Integration Tests
```bash
cd "c:\Users\isav3\VSCode Projects\UAV-UGV-Land-Survey"
python test_image_integration.py
```

Expected output:
```
✓ PASS: Files Exist
✓ PASS: Configuration
✓ PASS: ImageManager Import
✓ PASS: CaptureController Integration
✓ PASS: notmain.py Integration
✓ PASS: Directory Structure

✓ ALL TESTS PASSED
```

### Manual Testing

1. **Start receiver on ground station**:
   ```bash
   python ground_station_receiver.py --port 9999 --protocol udp
   ```

2. **Start UAV mission** (in Raspberry Pi simulator or real hardware):
   ```bash
   python -m Raspberry_Pi_Agent.notmain
   ```

3. **Monitor**:
   - Check `mission_data/images/` for captured images
   - Check `mission_data/metadata/index.json` for metadata
   - Check ground station `received_images/verified/` for received images
   - Check `received_images/metadata/*.json` for metadata

## Troubleshooting

**Problem**: Images not captured
- Check: `image_manager.get_status()['storage_status']`
- Verify: Camera is working (test with `test_picam2.py`)

**Problem**: Images not transmitting
- Check: Ground station IP in `config.yaml`
- Check: Ground station receiver is running
- Check: Ping ground station from Raspberry Pi
- Check: RSSI > -100 dBm (link not critical)

**Problem**: Storage full
- Check: Auto-cleanup enabled in config
- Check: `min_storage_mb_critical` threshold
- Manual cleanup: Delete images from `mission_data/sent/`

**Problem**: MD5 verification failed
- Indicates transmission corruption
- Try TCP instead of UDP: `protocol: "tcp"`
- Increase retry threshold

## Next Steps (Optional Enhancements)

1. **Image Compression**
   - Reduce JPEG quality at lower RSSI
   - Enable lossy compression on critical link

2. **Selective Transmission**
   - Only transmit images containing detected features
   - Use edge detection or object detection

3. **Ground Station Web UI**
   - Real-time image display
   - Mission statistics dashboard
   - Download received images

4. **Automatic Replay**
   - Post-mission image georeferencing
   - 3D point cloud generation from images
   - SLAM integration

## Support

For issues or questions:
1. Check troubleshooting section in `IMAGE_STORAGE_AND_TRANSMISSION.md`
2. Review logs in `mission_data/logs/`
3. Run integration tests: `python test_image_integration.py`
4. Enable DEBUG logging for detailed output
