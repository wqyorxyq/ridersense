# Scoring, coordinates, and timing

`rider/server.py` owns the authenticated local API and latest-frame worker. `vision.py` detects/tracks vehicles; `da3_metric.py` optionally estimates depth. `risk.py` computes temporal features; `alert_config.py` defines thresholds and channel rules. `haptics.py` adapts those requests to the optional SDK. `static/` is the complete browser frontend.

## Coordinates

Without verified intrinsics, normalized horizontal boundaries 0.18, 0.40, 0.60, 0.82 map screen left-to-right to rider right, rear-right, rear, rear-left, left. Boundary hysteresis is 0.025 plus positional smoothing. A rear camera reverses screen/rider left and right. Input mirroring is normalized once; preview mirroring does not change decisions.

With independently verified normalized fx and cx, angle = atan((x-cx)/fx). Boundaries are -55, -15, 15, 55 degrees, with 3-degree hysteresis. A single-point depth fit cannot verify physical intrinsics. Edge bands only approximate side directions; the lens may not see true lateral traffic.

## Risk score

All clip operations clamp to [0,1]. A = clip(box area / frame area / 0.35); G = clip(positive area-fraction growth per second / 0.15). When scaled depth is valid: D = clip((12-distance_m)/11), V = clip(relative closing_mps/6).

- No verified depth, or forced area mode: raw score = 100 × (0.85A + 0.15G).
- Verified scaled depth: raw score = 100 × (0.30A + 0.15G + 0.40D + 0.15V).
- Score smoothing: 0.45 new + 0.55 previous. Entry thresholds: >40 medium, >70 high. High exits at ≤65; medium exits at ≤35.
- Medium intensity = 0.20 + 0.30 × clip((score-40)/30), routed by the README table.

This is a demonstration rule, not a collision probability. Track gaps ≥0.8 seconds reset history. Implausible distance changes (>20 m/s), area jumps (>0.2), horizontal jumps (>0.25), and some global camera shifts discard temporal evidence. This is not complete ego-motion compensation. Highest-risk targets take priority; a visible replacement needs a 10-point margin. Relative closing speed is not absolute vehicle speed.

DA3 Metric output uses a canonical focal normalization. The adapter scales depth by `(fx / original_width) × depth_output_width / 300` only after scale configuration. Unknown metric values remain absent. The one-point fit is a demonstration calibration, not a full camera model.

## Output bounds

Only the latest pending frame is retained. Data older than 1.5 seconds cannot initiate feedback; expiry clears output. Source changes, pause/end, simulation entry, target loss, and total stop clear applicable outputs. High/medium pulses are requested approximately every 0.35/0.8 seconds using finite SDK sequences. All sequences are prepared before sequential start writes; this is not hardware synchronization.

Thermal pulses are 0.1–30 seconds, with no extension of a running pulse. Temperature is checked about every 0.5 seconds. Timers run on the host; physical shutdown after host failure is unverified. Total stop requests vibration OFF, thermal OFF, and LED OFF.

## Latency fields

`inference_ms` surrounds vision and risk processing. `pipeline_ms` runs from native capture-read start (or browser frame reception) through result encoding, including queue time. Frame age shows elapsed time since that origin. None includes unknown sensor buffering, all browser rendering, actuator response, or human perception. Serial write timing measures calls returning, not tactile execution.
