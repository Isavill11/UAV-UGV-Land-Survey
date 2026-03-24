# Deployment and Testing Guide

## Phase 1 – Environment Setup

- Install Python 3.8+
- Install dependencies:
  pip install -r requirements_mavlink.txt
- Configure serial port in config.yaml
- Enable Raspberry Pi serial interface if needed

---

## Phase 2 – Hardware Setup

### Wiring (TELEM2 → Raspberry Pi GPIO)

- FC TX → Pi RX (GPIO15)
- FC RX → Pi TX (GPIO14)
- GND → GND

Baud rate: 115200

---

## Phase 3 – MAVLink Connection Test

Create a simple connection test:
- Connect using MAVLinkHandler
- Confirm heartbeat received
- Verify system ID and component ID

Run from project folder directory on terminal: 
```
python3 -c 'from Raspberry_Pi_Agent.mavlink_handler import MAVLinkHandler; MAVLinkHandler("/dev/serial0").connect()'
```

If no heartbeat:
- Check wiring
- Verify baud rate
- Confirm flight controller powered and telemetry connected.

---

## Phase 4 – Camera Test
- Run [[test_image_integration.py](../test_image_integration.py)]
- Verify pathing and folder creation
- Run: 
``` 
python3 -c 'from Raspberry_Pi_Agent.Mission_Controller.capture_controller import CaptureController; CaptureController.start()'

```

Check:
- Camera Connection/status
- Storage permissions

---

## Phase 5 – Dry Run (On Ground)

1. Run mission code on project folder path using: 
```
python -m Raspberry_Pi_Agent.notmain
```

2. Verify:
   - Heartbeat logs appear
   - Battery data updates
3. Arm drone (without takeoff).
4. Switch to AUTO.
5. Disarm and verify shutdown.

---


## Phase 6 – First Flight

Check:

- Fully charged battery
- Open test field
- Manual RTL ready
- Ground station monitoring logs

Post-flight:
- Inspect captured images
- Review logs
- Check metadata accuracy

---

## Troubleshooting

| Problem  | Solution |
|----------|----------|
| No connection | Check serial port |
| No heartbeat | Check wiring |
| Camera error | Check device ID |
| Storage full | Enable cleanup |
| Failsafe immediately | Check thresholds |

---

## Production Deployment
- Tune all config thresholds
- Tune battery thresholds
- Tune thermal thresholds
- Adjust capture rates
- Monitor storage
- Enable auto-cleanup
- Backup SD card regularly


