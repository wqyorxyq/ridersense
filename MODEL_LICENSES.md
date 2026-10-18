# Model weights: separate license review

Verified **2026-10-18** against official sources. No weights, shards, or training data are distributed in this repository. `models.lock.json` is the machine-readable download manifest. Downloads require explicit `--accept-license`; the license label does not supersede upstream terms.

| Artifact | Revision / identity | License and official evidence | Distribution |
| --- | --- | --- | --- |
| YOLO11n pretrained `yolo11n.pt` | Ultralytics assets release `v8.4.0`, asset ID `340060970`; 5,613,764 bytes | AGPL-3.0 default model licensing per [official policy](https://www.ultralytics.com/license); [official asset release](https://github.com/ultralytics/assets/releases/tag/v8.4.0) | User downloads from official GitHub release; no modified weights |
| DA3 Metric-Large `model.safetensors` | `4010e39f3634a45bc60553321fb49fb760bd594e`; 1,336,734,448 bytes | Apache-2.0 explicitly stated in [this exact model card](https://huggingface.co/depth-anything/DA3METRIC-LARGE/blob/4010e39f3634a45bc60553321fb49fb760bd594e/README.md) | User downloads from official Hugging Face organization |

YOLO SHA-256: `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1`. The local development weight matched the official release digest. This pins content even if a release tag changes.

DA3 SHA-256: `bbea5b0b3ee389849cffa7ddae89de064a90abd2b055fc5aa99aac68db324776`. This comes from the official revision's LFS metadata and is enforced by the downloader. Metric-Large's license was checked separately from the DA3 source and from other DA3 variants; no license inference is made for other weights.

Ultralytics software version is `8.4.61` (AGPL-3.0); DA3 source checkout is `3d835ec1a5802d64a8b8b15f817a1ab54809bfe4` (Apache-2.0). See [third-party notices](THIRD_PARTY_NOTICES.md) for code and dependency attribution. The complete original training code is maintained upstream; RiderSense does not retrain or modify either weight. Our application, adapters, setup, tests, and frontend are published in full under AGPL-3.0-only.

Do not assume this grants unrestricted commercial use or covers proprietary SDK combinations. Review the individual licenses and any use-specific obligations. If redistributing an assembled application, retain upstream license/copyright notices and provide required corresponding source, including any changes. A UI source link is included for network users.
