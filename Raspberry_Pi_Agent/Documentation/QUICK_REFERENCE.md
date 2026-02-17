# Quick Reference: Image Storage & Transmission

## 🚀 Quick Start

### 1. Update Configuration (REQUIRED)
```yaml
# Raspberry_Pi_Agent/config.yaml
communication:
  ground_station_ip: "YOUR.GROUND.STATION.IP"  # UPDATE THIS
  ground_station_port: 9999
  protocol: "udp"  # or "tcp"
```

### 2. Start Ground Station Receiver
```bash
python ground_station_receiver.py --port 9999 --protocol udp
```

Expected output:
```
UDP listening on 0.0.0.0:9999
```

### 3. Start UAV Mission
```bash
# On Raspberry Pi
python -m Raspberry_Pi_Agent.notmain
```

## 📊 Monitor Status

### Check Image Storage
```python
status = image_manager.get_status()
print(f"Pending: {status['storage_status']['pending_count']}")
print(f"Sent: {status['storage_status']['sent_count']}")
print(f"Available: {status['storage_status']['available_mb']} MB")
```

### Check Transmission Stats
```python
stats = image_manager.get_transmission_stats()
print(f"Images sent: {stats['images_sent']}")
print(f"Bytes sent: {stats['bytes_sent'] / 1024 / 1024:.1f} MB")
```

### Check File System
```bash
# On Raspberry Pi
ls -lh mission_data/images/        # Captured images
ls -lh mission_data/sent/          # Successfully sent
cat mission_data/metadata/index.json  # All metadata
```

## 📡 Link Quality Thresholds

| RSSI (dBm) | Signal | Batch Size | Notes |
|------------|--------|-----------|-------|
| > -50 | Excellent | 10 | Full speed transmission |
| -50 to -70 | Good | 10 | Full speed |
| -70 to -85 | Degraded | 5 | Half batch |
| -85 to -100 | Weak | Single | One at a time |
| < -100 | Critical | None | Wait for link recovery |

## 📁 Directory Structure

```
mission_data/
├─ images/              # Captured JPEG images
├─ metadata/            # JSON metadata files
│  └─ index.json        # All images metadata
├─ tx_queue/            # Pending transmission
├─ sent/                # Successfully transmitted (archive)
└─ logs/                # Mission logs

received_images/ (Ground Station)
├─ verified/            # MD5 checksum passed
│  └─ 2026-02-17/       # Organized by date
├─ unverified/          # MD5 checksum failed
├─ failed/              # Reception errors
└─ metadata/            # JSON metadata copies
```

## 🔧 Common Troubleshooting

### Problem: No images captured
```bash
# Check camera is working
python -m Raspberry_Pi_Agent.live_detect_picam2

# Check image manager enabled
grep -A5 "capture_controller = CaptureController" notmain.py
# Should show: image_manager parameter passed
```

### Problem: Images not transmitting
```python
# Check ground station reachable
import socket
sock = socket.socket()
sock.connect(("192.168.1.100", 9999))  # Replace IP
sock.close()
print("✓ Connection OK")

# Check RSSI
print(f"RSSI: {system_health.radio.rssi}")  # Must be > -100
```

### Problem: Storage full
```bash
# Check available space
df -h | grep mission_data

# Manual cleanup (if auto-cleanup disabled)
rm -rf mission_data/sent/*
```

### Problem: MD5 verification failed
- Switch to TCP (more reliable): `protocol: "tcp"`
- Or increase timeout: `time_threshold_sec: 60`

## 🔑 Key Files

| File | Purpose |
|------|---------|
| `image_manager.py` | Image storage & transmission (600+ lines) |
| `ground_station_receiver.py` | Receive images on ground station |
| `IMAGE_STORAGE_AND_TRANSMISSION.md` | Full documentation |
| `IMPLEMENTATION_SUMMARY.md` | Implementation details |
| `test_image_integration.py` | Integration test suite |
| `config.yaml` | Configuration file |

## 📋 Configuration Reference

### Storage Settings
```yaml
image_storage:
  max_storage_mb: 2000            # Total limit
  min_storage_mb_critical: 100    # Critical alert threshold
  
auto_cleanup:
  enabled: true
  threshold_mb: 1500              # Trigger at this level
  cleanup_amount_mb: 500          # Clean this much
```

### Transmission Settings
```yaml
communication:
  protocol: "udp"                 # or "tcp"
  ground_station_ip: "192.168.1.100"
  ground_station_port: 9999

batching:
  batch_size: 10                  # Images per batch
  time_threshold_sec: 30          # Max wait time
  transmission_interval_sec: 5    # Check interval
```

## 🧪 Test Integration

```bash
# Run all integration tests
python test_image_integration.py

# Expected output:
# ✓ PASS: Files Exist
# ✓ PASS: Configuration
# ✓ PASS: ImageManager Import
# ✓ PASS: CaptureController Integration
# ✓ PASS: notmain.py Integration
# ✓ PASS: Directory Structure
# ✓ ALL TESTS PASSED
```

## 📊 Image Metadata Example

```json
{
  "filename": "IMG_20260217_134522_123.jpg",
  "timestamp": "2026-02-17T13:45:22.123",
  "altitude": 45.7,
  "profile": "CAPTURING",
  "size_bytes": 12345,
  "md5_hash": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "drone_latitude": -35.12345,
  "drone_longitude": 149.98765,
  "transmission_attempts": 1
}
```

## 🚨 Critical Errors to Watch For

```
ERROR: ImageManager failed to start transmission
→ Check: Is config.yaml loaded correctly?

ERROR: Ground station not reachable
→ Check: ground_station_ip in config.yaml
→ Check: Network connectivity (ping)

ERROR: Storage health CRITICAL
→ Action: Auto-cleanup should trigger
→ Check: auto_cleanup enabled in config

ERROR: MD5 mismatch for image
→ Indicates: Transmission packet corruption
→ Solution: Try TCP protocol or reduce batch size
```

## 📞 API Reference

### ImageManager
```python
from Raspberry_Pi_Agent.image_manager import ImageManager

manager = ImageManager(config)

# Lifecycle
manager.start_transmission()
manager.stop_transmission()

# Capture
manager.save_captured_image(image_bytes, profile, altitude)

# Transmission
manager.transmit_batch(rssi)

# Status
status = manager.get_status()  # Dict with all info
```

### StorageManager
```python
from Raspberry_Pi_Agent.image_manager import StorageManager

storage = StorageManager(base_path="mission_data", max_storage_mb=2000)

filename = storage.save_image(image_bytes, profile, altitude)
images = storage.get_pending_images(max_count=10)
storage.mark_transmitted(filename)
status = storage.get_storage_status()
```

### ImageTransmitter
```python
from Raspberry_Pi_Agent.image_manager import ImageTransmitter

transmitter = ImageTransmitter(
    config,
    ground_station_ip="192.168.1.100",
    ground_station_port=9999,
    protocol="udp"
)

transmitter.start()
transmitter.transmit_images(rssi=-65)
stats = transmitter.get_transmission_stats()
transmitter.stop()
```

## 🎯 Performance Tips

### For Excellent Link (RSSI > -50)
- Increase batch size: `batch_size: 20`
- Transmit faster: `time_threshold_sec: 10`
- Higher quality: `jpeg_quality: 95`

### For Poor Link (RSSI < -85)
- Use TCP (more reliable): `protocol: "tcp"`
- Reduce batch: `batch_size: 3`
- Transmit slower: `time_threshold_sec: 60`
- Lower quality: `jpeg_quality: 50`

### For Limited Storage
- Smaller batch: `batch_size: 5`
- Lower quality: `jpeg_quality: 60`
- Aggressive cleanup: `threshold_mb: 800`

## ✅ Deployment Checklist

- [ ] Update `ground_station_ip` in config.yaml
- [ ] Start ground station receiver
- [ ] Run `test_image_integration.py` → all pass
- [ ] Verify network connectivity
- [ ] Start mission
- [ ] Check images in `mission_data/images/`
- [ ] Check received images on ground station
- [ ] Monitor storage with `get_status()`
- [ ] Review metadata in `received_images/metadata/`

---

**Need Help?**
- Full docs: See `IMAGE_STORAGE_AND_TRANSMISSION.md`
- Implementation: See `IMPLEMENTATION_SUMMARY.md`
- Ground station: See `ground_station_receiver.py`
