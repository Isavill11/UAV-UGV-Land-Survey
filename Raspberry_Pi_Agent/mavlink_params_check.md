


## Analyze these features received from flight controller using rapsberry pi agent


### These features are the battery and overall system sensor health
SYS_STATUS: 

    battery_remaining    ->     > 40% = normal
    voltage_battery    ->      20-40% = reduce camera capture rate
    current_battery    ->      < 15% or when the state of the drone is critical = stop the capture rate completely and flush the buffers.
    onboard_control_sensors_health
    onboard_control_sensors_enabled

### this feature is the temperature health
SCALED_IMU2 or RAW_IMU:
    
    temperature (cdeg)


### These features are the link quality
RADIO_STATUS: 

    rssi
    - Signal strength of local radio
    - Use to decide image transmit rate

    remrssi
    - Remote (GCS) signal strength
    - Confirms downlink health

    rxerrors
    - Packet corruption indicator
    - Rising trend = back off bandwidth

    fixed
    - How many errors were corrected
    - High value = link struggling but alive

### note to self :
    Good link:
    rssi > -70
    rxerrors stable

    Degraded:
    rssi -70 to -85
    rxerrors rising

    Bad:
    rssi < -85
    rxerrors rapidly increasing




### These features are the flight state
HEARTBEAT:

    base_mode    ->     armed vs disarmed vs rtl vs land, lets you know what mode the drone is in. stop capturing images when rtl or landing. 
    custom_mode    ->   auto mission, manual mission. start full image capture on auto missions
    system_status    ->     LOITER, HOVER, etc, reduce capture rate. 

---

In addition to monitoring the packets received from the vehicle, we need to monitor the raspberry pi itself. 

Things to monitor include: 

- CPU temp
- GPU temp / SoC throttling
