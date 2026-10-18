# SPDX-License-Identifier: AGPL-3.0-only
"""Minimal DA3 Metric runner using upstream model and preprocessing unchanged.

Avoids importing unrelated mesh/video/3DGS export dependencies on Windows.
"""
from pathlib import Path
import sys
import torch

ROOT = Path(__file__).resolve().parents[1]


class MetricDepth:
    def __init__(self, device):
        source = ROOT/'vendor/depth-anything-3/src'
        if not source.is_dir():
            raise RuntimeError('Install pinned DA3 source using docs/models.md first.')
        sys.path.insert(0, str(source))
        from depth_anything_3.cfg import create_object, load_config
        from depth_anything_3.utils.io.input_processor import InputProcessor
        from safetensors.torch import load_file
        self.device = device
        config = ROOT/'vendor/depth-anything-3/src/depth_anything_3/configs/da3metric-large.yaml'
        self.model = create_object(load_config(str(config)))
        local = ROOT/'models/da3metric-large.safetensors'
        if not local.is_file():
            raise RuntimeError('DA3 weights are still downloading. Check the progress and load them when ready.')
        checkpoint = str(local)
        weights = load_file(checkpoint)
        weights = {k.removeprefix('model.'): v for k,v in weights.items()}
        self.model.load_state_dict(weights, strict=True)
        self.model.to(device).eval()
        self.processor = InputProcessor()

    @torch.inference_mode()
    def infer(self, rgb):
        tensor, _, _ = self.processor([rgb], process_res=336,
                                       process_res_method='upper_bound_resize', sequential=True)
        tensor = tensor[None].to(self.device)
        kind = 'cuda' if self.device.startswith('cuda') else 'cpu'
        dtype = torch.bfloat16 if kind == 'cuda' and torch.cuda.is_bf16_supported() else torch.float16
        with torch.autocast(kind, dtype=dtype, enabled=kind == 'cuda'):
            output = self.model(tensor)
        return output['depth'].float().squeeze().cpu().numpy()
