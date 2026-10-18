# Third-party notices and release audit

Review date: **2026-10-18**. Code, weights, and media were reviewed separately. The public repository was assembled from an allowlist in an independent directory; original local files were not deleted. No original root Git repository or root AGENTS.md was present. Vendor source had its own Git checkout and is excluded from the new history.

## Application license choice

RiderSense imports Ultralytics in the same Python process. We choose **AGPL-3.0-only** for the complete application rather than apply MIT to that integration. All application source, web assets, tests, and setup instructions are provided. The dashboard links to the corresponding public source. Apache-2.0 DA3 source/model licensing is recorded independently. Optional DataFeel code is not included or relicensed; no permission is inferred from an unlicensed public repository.

| Component | Exact version / revision inspected | Official license evidence | Included in repository? |
| --- | --- | --- | --- |
| Ultralytics software | 8.4.61, commit `e42c3b3d7dfb8a112b36e97a136f84f85c13ba3d` (tag `v8.4.61`) | [AGPL-3.0 text at tag](https://github.com/ultralytics/ultralytics/blob/v8.4.61/LICENSE), [official licensing](https://www.ultralytics.com/license) | No package/source copy; pip requirement only. License text retained in `licenses/AGPL-3.0.txt` |
| YOLO11n weights | Exact official release asset and hash in `models.lock.json` | [Weight-specific review](MODEL_LICENSES.md) | No |
| Depth Anything 3 source | `3d835ec1a5802d64a8b8b15f817a1ab54809bfe4`, local checkout clean | [Apache-2.0 at exact commit](https://github.com/ByteDance-Seed/Depth-Anything-3/blob/3d835ec1a5802d64a8b8b15f817a1ab54809bfe4/LICENSE) | No; user clones exact upstream commit. License text retained in `licenses/DA3-Apache-2.0.txt` |
| DA3 Metric-Large weights | `4010e39f3634a45bc60553321fb49fb760bd594e` | [Model card](https://huggingface.co/depth-anything/DA3METRIC-LARGE/blob/4010e39f3634a45bc60553321fb49fb760bd594e/README.md), Apache-2.0 | No |
| DataFeel Python SDK and samples | Python `setup.py` version 1.0.0; supplied archive has no Git revision; official repository inspected at `ec25afa62b82043c99529ced9285b9c6f91337e1` | [Official repository](https://github.com/DataFeel/devkit-samples/tree/ec25afa62b82043c99529ced9285b9c6f91337e1); `Python/setup.py` declares MIT, but no full LICENSE/copyright grant was found, and API license is null. Scope and attribution terms for the supplied bundle remain unresolved | **No**; optional runtime adapter only. Obtain permission/copy from vendor |
| DataFeel Unity SDK | Supplied archive named version 1.0.3; not used by Python app | No confirmed redistribution terms in supplied package | No |
| DataFeel manual and tester | User Guide 1.0.0; tester archive named 24_11_13; not imported | No confirmed redistribution permission | No |
| CP210x driver bundle | Supplied Universal Windows driver archive, exact version not established | Vendor license file found; [official driver source](https://www.silabs.com/developer-tools/usb-to-uart-bridge-vcp-drivers) | No; use official download under vendor terms |
| `bus.jpg` benchmark image | Previously read from installed Ultralytics package assets, not copied into application source | Standalone image rights not established by the code license | **No**; benchmark now requires a user-supplied authorized image |

## Dependencies and embedded upstream components

`requirements*.txt` pin the direct installation inputs; `requirements-tested-windows.txt` records the minimal environment's full resolution. [Dependency inventory](docs/dependency-licenses.md) records versions, official project links and package metadata license declarations. Packages are fetched by users, not vendored here. Their installed wheels retain their own licenses and notices. Metadata is evidence for package identity, not a replacement for bundled component licenses.

The DA3 checkout includes code derived from projects such as DINOv2 and depth-processing components with their own copyright headers. The reduced adapter does not copy or alter these files; users obtain the entire original checkout including notices. The Apache-2.0 top-level license is not represented as granting rights to every unrelated model, dataset, or export extra. Optional upstream 3D/streaming/application extras are not part of RiderSense's installation. PyTorch wheels, OpenCV builds (including codec libraries), NumPy, Pillow and their binary dependencies retain their distribution-specific notices; consult those when redistributing a built environment. No binary environment is shipped here.

## Media, fonts, and excluded local material

The dashboard uses CSS, canvas drawings, Unicode symbols, and system fonts. No downloaded icon pack, font binary, logo asset, private video, or third-party demo image is included. `docs/images/simulation.png` is an actual screenshot of this application's generated simulation, licensed with the application. It contains no camera imagery or hardware-execution claim.

Excluded categories include all vendor archives/source, model weights/shards, virtual environments, cache/log/runtime state, private video, personal screenshots, certificates/private keys/profiles, account artifacts, and fixed private LAN addresses. Generated local TLS keys were never copied or printed. No old history is pushed; the release starts with a new reviewed Git history. Download/configuration tools use official sources and explicit user configuration.

Supplied DataFeel sample archive SHA-256: `c16f00e1e660d5482062bc21634605a764ac7cbdc1f3762d6ee1055e01d01e96`. Python setup metadata says version 1.0.0 and “MIT license”; this is recorded as evidence, not extended to the driver, Unity SDK, manual, tester, or whole archive. Full grant/notice and scope confirmation from the vendor would be needed before reconsidering redistribution.
