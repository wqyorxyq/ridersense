# Optional vision setup

The dashboard and simulation do not need these packages. Use Python 3.12. Install a CPU build of PyTorch, or choose the CUDA build compatible with your system from [official PyTorch instructions](https://pytorch.org/get-started/locally/). GPU installation is several GB and is explicitly optional.

```powershell
.venv\Scripts\python.exe -m pip install torch==2.11.0 torchvision==0.26.0 --index-url https://download.pytorch.org/whl/cu128
.venv\Scripts\python.exe -m pip install -r requirements-vision.txt
.venv\Scripts\python.exe scripts/download_models.py yolo11n --accept-license
```

For CPU, substitute `https://download.pytorch.org/whl/cpu` in the first command. CPU vision throughput is unverified. Stop the running server before changing dependencies: Windows locks loaded binary modules. The minimal and vision configurations use the same pinned OpenCV distribution to avoid overlapping wheels.

Detection-only mode uses YOLO11n and image-area scoring. Read [model licenses](../MODEL_LICENSES.md) before accepting a download. The downloader prints size, upstream URL, revision, and license; it checks both size and SHA-256, including existing files. It does not silently accept a preexisting file. Model loading never downloads missing weights.

For optional DA3 depth, obtain the unmodified upstream source separately:

```powershell
git clone https://github.com/ByteDance-Seed/Depth-Anything-3.git vendor/depth-anything-3
git -C vendor/depth-anything-3 checkout --detach 3d835ec1a5802d64a8b8b15f817a1ab54809bfe4
.venv\Scripts\python.exe scripts/download_models.py da3metric-large --accept-license
```

The adapter imports upstream model construction and input processing directly from that checkout. It does not install upstream's unrelated 3D export, app, or streaming extras. Upstream `pyproject.toml` advertises a different NumPy constraint and many optional-to-this-path libraries; our reduced inference path must be validated separately, not presented as testing all upstream features. Preserve the upstream checkout's licenses and notices locally.

YOLO11n: 5,613,764 bytes (~5.35 MiB). DA3 Metric-Large: 1,336,734,448 bytes (~1.245 GiB). URLs, exact revisions, and hashes are in `models.lock.json`. Neither weights nor third-party source are included in Git. Only download models from trusted official sources; PyTorch checkpoint formats can execute code during loading.

Benchmark your own authorized image with `python scripts/benchmark.py --mode da3 --image path/to/your-image.jpg`. This measures the adapter's inference call after one warm-up, not acquisition, network, rendering, device actuation, or perception. It never activates hardware.
