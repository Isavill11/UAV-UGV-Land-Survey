
Need help finding something?

| Question                    | Answer                        |
|-----------------------------|-------------------------------|
| What's included?            | IMPLEMENTATION_SUMMARY.md     |
| How do I setup?             | MAVLINK_INTEGRATION_GUIDE.md  |
| Show me code examples       | MISSION_EXAMPLES.py           |
| How do I test?              | TESTING_CHECKLIST.md          |
| How does it work?           | ARCHITECTURE_REFERENCE.md     |
| Where is file X?            | PROJECT_STRUCTURE.md          |
| What if something's wrong?  | Troubleshooting in guides     |
| Navigation help             | DOCUMENTATION_INDEX.md        |




╔════════════════════════════════════════════════════════════════════════════╗
║                        TROUBLESHOOTING GUIDE                               ║
╠════════════════════════════════════════════════════════════════════════════╣
║            PROBLEM         │         CAUSES           │    SOLUTIONS       ║
╠────────────────────────────┼──────────────────────────┼────────────────────╣
║ Can't connect              │ - Wrong serial port      │ Check /dev/tty*    ║
║                            │ - Wrong baud rate        │ Verify 115200      ║
║                            │ - Cable disconnected     │ Check cable        ║
║                            │ - FC not powered         │ Power on FC        ║
╠────────────────────────────┼──────────────────────────┼────────────────────╣
║ No heartbeat received      │ - Link quality bad       │ Move closer/       ║
║                            │ - Message rate too low   │ different cable    ║
║                            │ - Buffer overflow        │ Reduce loop rate   ║
╠────────────────────────────┼──────────────────────────┼────────────────────╣
║ Camera won't open          │ - Wrong camera ID        │ Check /dev/vid*    ║
║                            │ - Camera not enabled     │ raspi-config       ║
║                            │ - USB camera unplugged   │ Check connection   ║
╠────────────────────────────┼──────────────────────────┼────────────────────╣
║ Images not saving          │ - Wrong save directory   │ Create dir first   ║
║                            │ - No storage space       │ Check df -h        ║
║                            │ - Permission denied      │ Check ownership    ║
╠────────────────────────────┼──────────────────────────┼────────────────────╣
║ System goes to FAILSAFE    │ - Battery too low        │ Charge battery     ║
║ immediately                │ - Temperature too high   │ Cool Pi down       ║
║                            │ - Storage full           │ Delete old data    ║
║                            │ - Link quality bad       │ Check antenna      ║
╠────────────────────────────┼──────────────────────────┼────────────────────╣
║ Capture rate very slow     │ - I/O bottleneck         │ Use faster SD      ║
║                            │ - CPU maxed out          │ Lower resolution   ║
║                            │ - Storage full           │ Clean up drive     ║
╠────────────────────────────┼──────────────────────────┼────────────────────╣
║ Weird health readings      │ - Sensor noise           │ Add hardware filt  ║
║                            │ - Stale data             │ Check data age     ║
║                            │ - Integration issue      │ Restart service    ║
╚════════════════════════════════════════════════════════════════════════════╝
