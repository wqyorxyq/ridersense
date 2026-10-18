# SPDX-License-Identifier: AGPL-3.0-only
"""Run real inference on an upstream sample; does not activate hardware."""
import argparse
import json
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cv2
import numpy as np
import torch
import ultralytics
from rider.vision import Vision

parser=argparse.ArgumentParser()
parser.add_argument('--mode',choices=['detect','da3'],default='detect')
parser.add_argument('--image', required=True)
args=parser.parse_args()
path=Path(args.image)
image=cv2.imread(str(path))
if image is None:
    raise SystemExit(f'Cannot read {path}')
vision=Vision()
vision.load(args.mode)
times=[]
for i in range(4):
    start=time.perf_counter()
    objects,depth,metric=vision.infer(image,include_people=True)
    if torch.cuda.is_available():torch.cuda.synchronize()
    elapsed=(time.perf_counter()-start)*1000
    if i:times.append(elapsed)
print(json.dumps({'mode':args.mode,'device':vision.device,'warm_ms':times,
    'median_ms':float(np.median(times)),'labels':[o['label'] for o in objects],
    'depth_shape':list(depth.shape) if depth is not None else None,
    'metric':metric,'peak_vram_mb':torch.cuda.max_memory_allocated()/1024**2 if torch.cuda.is_available() else None},indent=2))
