# Release validation — 2026-10-18

## Environment actually exercised

- Windows 11, build 10.0.26200, x86-64; Python 3.12.9.
- Independent virtual environments created without system site packages. Minimal dependency resolution is in `requirements-tested-windows.txt`; optional vision resolution is in `requirements-tested-vision-windows.txt`.
- Optional GPU: NVIDIA GeForce RTX 4060 Laptop, 8,188 MiB reported memory; driver 592.82; PyTorch 2.11.0+cu128, torchvision 0.26.0+cu128; Ultralytics 8.4.61.
- Local Chrome, automated in an isolated headless browser context. No existing personal browser profile was used.

## Passed locally

- Clean minimal install, `pip check`, server startup, and actual HTTP/browser simulation without DataFeel SDK or GPU packages. The first startup was also performed before weights were installed.
- **44 Python tests**, including four-dot mapping, coordinate transforms, hysteresis, stale-input stopping, simulation/live isolation, replay reset, finite sequence ordering, thermal deadline/no extension/30-second maximum, and temperature limit behavior.
- New regressions for no-SDK clear/stop, explicit hardware opt-in, missing-model download prevention, checksum rejection for existing files, and iPhone session endpoint blocking across normal/encoded/normalized paths.
- Generated gateway certificates in a temporary directory; verified server signature against the generated CA and the configured IP SAN, then cleaned temporary certificate material. This does not verify physical iPhone trust installation.
- JavaScript syntax check and strict DOM behavior test, including replay pause/resume and inactive-output explanations.
- Actual browser simulation at rear-left/80: displayed Dot 1 20%, Dot 2 80%, with hardware requests all zero; stop and exit succeeded. English visible text, no page errors, 390px mobile width without horizontal overflow. README image is an actual 1440×1100 screenshot.
- Optional vision installation and `pip check`; official YOLO download plus size/SHA-256 verification; existing local DA3 weight matched the pinned official LFS digest. DA3 source was separately cloned at the documented commit, with no modifications.
- Actual GPU inference using the public adapter and synthetic input, described below.
- Release allowlist, tracked-file inspection, sensitive-pattern checks, and reachable-history audit. Excluded local TLS key was identified by filename only; no value was printed or copied. Original source folder, local assets, and existing demonstration server were preserved.

The tests emit one upstream Starlette/AnyIO deprecation warning. It does not fail the checks. CI uses default hardware-disabled mode and no models, camera, or real SDK. Passing CI does not validate physical devices or platform-specific camera behavior.

## Performance measurements and their limits

Current release smoke benchmark: 640×480 synthetic black image containing a colored rectangle, detection at 640 input size plus DA3 processing resolution 336, output depth 252×336, no detections, no metric calibration. One warm-up followed by three timed `Vision.infer` calls produced **75.47, 116.43, 62.67 ms**; median **75.47 ms**. Torch peak allocated memory was **1,419.23 MiB**. Hardware/software are listed above. Other workloads were not controlled; this short synthetic run is an installation/inference check, not a representative vehicle benchmark. It does not establish detection accuracy or sustained throughput.

Historical development notes reported ~79.8 ms warm inference on an upstream `bus.jpg` and a separate camera observation of 16 samples with median 63 ms analysis / 78 ms backend processing. Those observations used a different global environment; the original image's separate rights and full experimental conditions were not established. They are **not release acceptance measurements**, their media are not redistributed, and they are not presented as current end-to-end performance.

Inference timing excludes camera acquisition, browser upload/rendering, USB actuation, and human perception. Torch allocated memory excludes other GPU processes and driver allocations. Backend `pipeline_ms` has a wider but still incomplete scope; see [architecture](architecture.md). No camera-to-skin latency was measured.

## Not verified

- Physical DataFeel execution, four-dot simultaneous timing, wearing layout, perceived intensity, thermal performance, or hardware watchdog behavior.
- Real camera/video vehicle accuracy in this release environment, calibrated metric distance/speed accuracy, outdoor road behavior, or safety outcomes.
- iPhone profile installation, Safari camera capture and device-specific permissions on a physical phone.
- macOS, Linux camera/GUI/GPU operation, other Python versions, CPU inference performance, and other GPUs. Linux CI covers only hardware-free unit/API logic.
- Quest-native capture, a persistent 3D map, calibrated collision prediction, or full end-to-end latency; these are not implemented claims.
