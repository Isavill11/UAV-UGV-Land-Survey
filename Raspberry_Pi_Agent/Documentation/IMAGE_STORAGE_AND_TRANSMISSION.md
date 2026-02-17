# Image Storage and Transmission System

## Overview

The UAV-UGV Land Survey system now includes a complete image storage and transmission layer that:

- **Captures images** with drone metadata (altitude, timestamp, profile)
- **Stores images locally** with automatic cleanup and space management
- **Transmits images adaptively** based on WiFi link quality (RSSI)
- **Verifies integrity** using MD5 checksums
- **Persists state** for recovery after system restarts
- **Organizes data** for easy ground station retrieval

## Architecture

```
CaptureController
    ↓ (saves images)
ImageManager
    ├─ StorageManager (local filesystem)
    │   ├─ images/          (captured images)
    │   ├─ metadata/        (JSON metadata index)
    │   ├─ tx_queue/        (pending transmission)
    │   └─ sent/            (archive)
    │
    └─ ImageTransmitter (UDP/TCP thread)
        ├─ Link quality detection (RSSI)
        ├─ Adaptive batching
        └─ Checksum verification
            ↓ (sends to)
Ground Station Receiver
    ├─ verified/           (MD5 passed)
    ├─ unverified/         (MD5 failed)
    └─ metadata/           (JSON files)
```

## Configuration

### config.yaml - Image Storage Settings

```yaml
image_storage:
  base_path: "mission_data"                   # Base directory
  images_dir: "mission_data/images"           # Captured images
  metadata_dir: "mission_data/metadata"       # Image metadata JSON
  tx_queue_dir: "mission_data/tx_queue"       # Pending transmission
  sent_dir: "mission_data/sent"               # Archive
  max_storage_mb: 2000                        # Total storage limit
  min_storage_mb_warn: 500                    # Warning threshold
  min_storage_mb_critical: 100                # Critical threshold
```

### config.yaml - Image Transmission Settings

```yaml
batching:
  batch_size: 10                              # Images per batch
  time_threshold_sec: 30                      # Max time before forcing send
  transmission_interval_sec: 5                # Check interval

communication:
  protocol: "udp"                             # or "tcp"
  ground_station_ip: "192.168.1.100"          # UPDATE FOR YOUR NETWORK
  ground_station_port: 9999                   # UPDATE FOR YOUR NETWORK
  
  rssi_thresholds:
    excellent: -50          # Full batch
    good: -70               # Full batch
    degraded: -85           # Half batch
    critical: -100          # No transmission
```

## Workflow

### 1. Image Capture and Storage

```python
# In mission loop, images are captured:
capture_controller.update()  # Captures image based on profile interval

# ImageManager automatically saves with metadata:
# - Filename: IMG_20260217_134522_123.jpg
# - Metadata: timestamp, altitude, profile, size, MD5
```

**Saved Structure:**
```
mission_data/
├─ images/
│  ├─ IMG_20260217_134522_123.jpg
│  ├─ IMG_20260217_134523_456.jpg
│  └─ ...
├─ metadata/
│  ├─ index.json            (all images metadata)
│  └─ IMG_*.jpg.json        (per-image metadata)
├─ tx_queue/                (pending transmission)
└─ sent/                    (successfully sent)
```

### 2. Altitude Integration

The drone's altitude is updated in the main loop and included in image metadata:

```python
# In notmain.py main loop:
self.capture_controller.set_altitude(self.system_health.drone.altitude)

# Each captured image now includes:
{
  "timestamp": "2026-02-17T13:45:22.123",
  "altitude": 45.7,                           # meters
  "profile": "CAPTURING",
  "drone_lat": -35.12345,
  "drone_lon": 149.98765
}
```

### 3. Link Quality-Based Transmission

Images are transmitted adaptively based on WiFi RSSI (Received Signal Strength Indicator):

```
RSSI > -50 dBm (Excellent)  → Send full batch (10 images)
RSSI > -70 dBm (Good)       → Send full batch (10 images)
RSSI > -85 dBm (Degraded)   → Send half batch (5 images)
RSSI > -100 dBm (Critical)  → Don't transmit, wait for link recovery
```

**Batch Transmission Logic:**
```python
# Called every 5 seconds in main loop
rssi = self.system_health.radio.rssi  # RSSI in dBm (-50 to -100)
self.image_manager.transmit_batch(rssi)

# ImageTransmitter calculates batch size:
if rssi < -50:     batch_size = 10   # Full
elif rssi < -70:   batch_size = 10   # Full
elif rssi < -85:   batch_size = 5    # Half
elif rssi < -100:  batch_size = 0    # None
```

### 4. Transmission Packet Protocol

Each image is sent as a single packet containing:

```
[Header (7B: "IMG_PKT")]
[Filename Length (2B: uint16 BE)]
[Filename (var: UTF-8 string)]
[Metadata Length (2B: uint16 BE)]
[Metadata (var: JSON)]
[Image Length (4B: uint32 BE)]
[Image Data (var: JPEG bytes)]
[MD5 Checksum (32B: hex string)]
```

**Example Metadata JSON:**
```json
{
  "filename": "IMG_20260217_134522_123.jpg",
  "timestamp": "2026-02-17T13:45:22.123",
  "altitude": 45.7,
  "profile": "CAPTURING",
  "size_bytes": 12345,
  "drone_latitude": -35.12345,
  "drone_longitude": 149.98765,
  "transmission_attempts": 1
}
```

### 5. Storage Management

Automatic cleanup occurs when storage exceeds threshold:

```yaml
auto_cleanup:
  enabled: true
  threshold_mb: 1500        # Cleanup when storage exceeds this
  cleanup_amount_mb: 500    # Delete oldest images until freed
```

**Cleanup Priority:**
1. Delete sent images first (lowest priority)
2. Delete failed transmission images
3. Delete oldest pending images (highest priority)

**Status Monitoring:**
```python
status = image_manager.get_status()
# Returns:
# {
#   "storage_status": {
#     "pending_count": 15,
#     "sent_count": 42,
#     "failed_count": 2,
#     "available_mb": 450,
#     "health_status": "WARNING"  # OK, WARNING, CRITICAL
#   },
#   "transmission_stats": {
#     "images_sent": 42,
#     "bytes_sent": 5242880,
#     "transmission_failures": 2
#   }
# }
```

## Ground Station Setup

### 1. Run Ground Station Receiver

```bash
# Start receiving images on port 9999
python ground_station_receiver.py --port 9999 --protocol udp

# Or with custom settings:
python ground_station_receiver.py \
  --ip 0.0.0.0 \
  --port 9999 \
  --protocol udp \
  --save-dir ./mission_images
```

### 2. Directory Structure

Received images are organized:

```
received_images/
├─ verified/
│  ├─ 2026-02-17/
│  │  ├─ IMG_20260217_134522_123.jpg
│  │  └─ IMG_20260217_134523_456.jpg
│  └─ 2026-02-18/
├─ unverified/               (MD5 failed)
├─ failed/                   (reception errors)
└─ metadata/
   ├─ IMG_20260217_134522_123.jpg.json
   └─ IMG_20260217_134523_456.jpg.json
```

### 3. Metadata Files

Each image has an associated JSON metadata file:

```json
{
  "filename": "IMG_20260217_134522_123.jpg",
  "timestamp": "2026-02-17T13:45:22.123",
  "altitude": 45.7,
  "profile": "CAPTURING",
  "size_bytes": 12345,
  "md5_hash": "a1b2c3d4e5f6...",
  "drone_latitude": -35.12345,
  "drone_longitude": 149.98765,
  "transmission_attempts": 1
}
```

## Integration Points

### 1. CaptureController

- **Receives ImageManager** in constructor
- **Calls `image_manager.save_captured_image()`** when image captured
- **Updates altitude** via `set_altitude()` method

```python
# In capture_controller.py
def __init__(self, config, image_manager=None):
    self.image_manager = image_manager
    self.current_altitude = 0.0

def _capture_frame(self):
    # ... capture image to bytes ...
    if self.image_manager:
        self.image_manager.save_captured_image(
            image_bytes,
            profile=self.active_profile,
            altitude=self.current_altitude
        )
```

### 2. Mission Controller (notmain.py)

- **Instantiates ImageManager** in `__init__`
- **Starts transmission thread** after MAVLink setup
- **Updates altitude** in main loop
- **Triggers transmission** based on link quality
- **Stops transmission** gracefully on shutdown

```python
# In notmain.py
self.image_manager = ImageManager(self.config)
self.image_manager.start_transmission()

# In main loop:
self.capture_controller.set_altitude(self.system_health.drone.altitude)
rssi = self.system_health.radio.rssi
self.image_manager.transmit_batch(rssi)

# On shutdown:
self.image_manager.stop_transmission()
```

### 3. Configuration (config.yaml)

All settings in one place:
- Storage directories and limits
- Transmission protocol and destination
- Batch size and timing
- Link quality thresholds

## Deployment Checklist

- [ ] **Update config.yaml**:
  - [ ] Set `communication.ground_station_ip` to your ground station IP
  - [ ] Set `communication.ground_station_port` for reception
  - [ ] Verify storage paths and limits
  - [ ] Configure batch size for your use case

- [ ] **Network Setup**:
  - [ ] Ensure Raspberry Pi and Ground Station are on same WiFi network
  - [ ] Note Ground Station IP address
  - [ ] Test connectivity: `ping <ground_station_ip>`

- [ ] **Ground Station**:
  - [ ] Start receiver: `python ground_station_receiver.py --port 9999`
  - [ ] Verify listening: Check receiver output shows "UDP listening on 0.0.0.0:9999"
  - [ ] Monitor received images in `received_images/` directory

- [ ] **Mission Execution**:
  - [ ] Arm drone and switch to AUTO mode
  - [ ] Monitor captured images in `mission_data/images/`
  - [ ] Check transmission in ground station receiver
  - [ ] Verify metadata files are created

- [ ] **Testing**:
  - [ ] Capture a test flight with short distance
  - [ ] Verify images appear in `received_images/verified/`
  - [ ] Check MD5 validation (should show "✓ Received")
  - [ ] Review metadata JSON files

## Troubleshooting

### Images not being transmitted

**Check 1: ImageManager running?**
```python
status = image_manager.get_status()
print(status['transmission_stats'])  # Should show activity
```

**Check 2: Ground station reachable?**
```bash
# From Raspberry Pi:
ping 192.168.1.100
# Should respond
```

**Check 3: RSSI below threshold?**
```python
rssi = system_health.radio.rssi
print(f"RSSI: {rssi}")  # Should be > -100 for transmission
```

### MD5 verification failed

- Indicates packet corruption during transmission
- Try TCP protocol for more reliable transmission: `protocol: "tcp"`
- Increase batch size delay: `time_threshold_sec: 60`

### Storage full

- Check: `image_manager.get_status()['storage_status']`
- If `health_status` is CRITICAL, auto-cleanup should trigger
- Verify: `auto_cleanup.enabled: true` in config.yaml
- Manual cleanup: Delete old images from `mission_data/sent/`

### Altitude showing 0.0 in metadata

- Verify drone has GPS lock (altitude from GPS_RAW_INT)
- Check: `system_health.drone.altitude` in main loop
- May need to wait for GPS fix before takeoff

## Performance Tuning

### For Good WiFi Link (RSSI > -50 dBm)

```yaml
batching:
  batch_size: 20              # Larger batches
  time_threshold_sec: 10      # Transmit faster
```

### For Poor WiFi Link (RSSI -85 to -70 dBm)

```yaml
batching:
  batch_size: 5               # Smaller batches
  time_threshold_sec: 60      # Transmit less frequently
```

### For Limited Storage (< 500MB available)

```yaml
image_storage:
  max_storage_mb: 500         # Lower limit
  min_storage_mb_critical: 50 # Trigger cleanup earlier

auto_cleanup:
  threshold_mb: 300           # Cleanup at lower threshold
  cleanup_amount_mb: 200      # More aggressive cleanup
```

## API Reference

### ImageManager

```python
image_manager = ImageManager(config)

# Lifecycle
image_manager.start_transmission()   # Start background thread
image_manager.stop_transmission()    # Graceful shutdown

# Capture interface
image_manager.save_captured_image(
    image_bytes,           # Raw JPEG bytes
    profile="CAPTURING",   # Capture profile
    altitude=45.7          # Drone altitude in meters
) → filename or None

# Transmission control
image_manager.transmit_batch(rssi=-65)  # Trigger adaptive transmission

# Status monitoring
status = image_manager.get_status() → dict with storage and transmission stats
```

### ImageTransmitter

```python
transmitter = ImageTransmitter(
    config,
    ground_station_ip="192.168.1.100",
    ground_station_port=9999,
    protocol="udp"
)

transmitter.start()                  # Start background thread
transmitter.stop()                   # Stop gracefully
transmitter.transmit_images(rssi)    # Trigger transmission
stats = transmitter.get_transmission_stats()  # Get stats
```

### StorageManager

```python
storage = StorageManager(
    base_path="mission_data",
    max_storage_mb=2000
)

filename = storage.save_image(
    image_bytes,           # Raw JPEG bytes
    profile="CAPTURING",
    altitude=45.7
) → filename

images = storage.get_pending_images(max_count=10)  # Get images to send
storage.mark_transmitted(filename)   # Mark as successfully sent
storage.mark_transmission_failed(filename)  # Mark as failed

status = storage.get_storage_status()  # Get storage info
```

## Related Documentation

- [MAVLink Integration](Raspberry_Pi_Agent/Documentation/MAVLINK_REFERENCE.md)
- [Health Monitoring](Raspberry_Pi_Agent/Documentation/HEALTH_MONITORING.md)
- [Mission Architecture](Raspberry_Pi_Agent/Documentation/ARCHITECTURE_REFERENCE.md)
- [Capture Controller](Raspberry_Pi_Agent/Documentation/CAPTURE_CONTROLLER_GUIDE.md)
