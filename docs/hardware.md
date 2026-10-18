# Optional DataFeel adapter

Simulation and video analysis work without an SDK or controller. Physical control is opt-in. This release does not redistribute or relicense DataFeel's SDK, driver, manual, examples, or tester. The supplied Python SDK had no confirmed redistribution grant; public availability alone is not permission. Obtain an authorized copy from [DataFeel](https://github.com/DataFeel/devkit-samples) or your vendor contact and confirm its terms for your intended use.

1. Install the official CP210x driver if required, from [Silicon Labs](https://www.silabs.com/developer-tools/usb-to-uart-bridge-vcp-drivers). Do not use the archived driver bundle from the development machine.
2. Obtain the DataFeel Python SDK compatible with your controller. The expected folder contains `datafeel/device.py`. Its setup metadata declares version 1.0.0 and MIT, but the supplied bundle lacks a confirmed full grant and notice; see THIRD_PARTY_NOTICES.md. The supplied Unity SDK 1.0.3 is a different artifact and is not used.
3. Install only the adapter dependencies and opt in before launch:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-hardware.txt
$env:DATAFEEL_SDK_PATH = (Resolve-Path 'path/to/authorized-sdk/Python').Path
$env:RIDER_HARDWARE = 'datafeel'
.venv\Scripts\python.exe scripts/run_site.py
```

Connect one USB controller and four dots at addresses 1–4. Scan, verify each wearing location with a short test pulse, and then enable automatic feedback with fresh analyzed frames. No scan or physical output runs on startup. The adapter checks CP210x VID/PID and refuses ambiguous multiple-controller discovery. Python callers can use `Haptics.scan(port=...)` to select a detected controller explicitly.

The narrow adapter requires `Dot`, `VibrationMode`, and `VibrationWaveforms` from `datafeel.device`. It calls documented-style LED, thermal, register, and finite-sequence operations; no vendor implementation is copied. Tests inject independent fake symbols and devices, never the real SDK.

Finite vibration sequences end with `END_SEQUENCE`. Requested medium intensity is rounded to SDK nominal 20/40/60/80% effects; it is not a measured amplitude. Serial calls returning do not confirm physical execution. Four-dot synchronization, physical strength, thermal behavior, and the controller watchdog are **unverified for this release**.

Heating/cooling is limited to 30 seconds, cannot be extended in-place, and disables automatic vibration. Host checks require contact temperature between 15 and 40°C and heatsink below 45°C. Read failures attempt OFF. A crash, sleeping computer, or disconnected USB can defeat host timers: use controller power to stop. Do not run public CI with hardware enabled.

To return to default operation, close the server and remove `RIDER_HARDWARE` and `DATAFEEL_SDK_PATH` from that shell. Do not publish a combined SDK bundle without confirming its separate terms and compatibility.
