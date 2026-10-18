# SPDX-License-Identifier: AGPL-3.0-only
from pathlib import Path
import os
import sys
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('YOLO_AUTOINSTALL', 'false')
os.environ.setdefault('YOLO_CONFIG_DIR', str(ROOT/'.runtime/ultralytics'))


class Vision:
    def __init__(self):
        self.detector = None
        self.depth_model = None
        self.device = 'cpu'
        self.mode = 'none'
        self.previous_gray = None
        self.motion_unstable = False

    def load(self, mode='da3'):
        if not (ROOT/'models/yolo11n.pt').is_file():
            raise RuntimeError('YOLO weights missing. Run: python scripts/download_models.py yolo11n --accept-license')
        try:
            import torch
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError('Install requirements-vision.txt first; see docs/models.md') from exc
        self.device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
        os.makedirs(ROOT/'models', exist_ok=True)
        self.depth_model = None
        if torch.cuda.is_available(): torch.cuda.empty_cache()
        self.detector = YOLO(str(ROOT/'models/yolo11n.pt'))
        self.mode = 'detect'
        if mode == 'da3':
            from rider.da3_metric import MetricDepth
            self.depth_model = MetricDepth(self.device)
            self.mode = 'da3'

    def reset(self):
        self.previous_gray = None
        self.motion_unstable = False
        if self.detector and getattr(self.detector, 'predictor', None):
            for tracker in getattr(self.detector.predictor, 'trackers', []):
                tracker.reset()

    def infer(self, bgr, focal_ratio=None, include_people=False):
        if self.detector is None:
            raise RuntimeError('Load vision models first')
        gray=cv2.resize(cv2.cvtColor(bgr,cv2.COLOR_BGR2GRAY),(96,72)).astype(np.float32)
        self.motion_unstable=False
        if self.previous_gray is not None:
            shift,response=cv2.phaseCorrelate(self.previous_gray,gray)
            self.motion_unstable=bool(response>.15 and np.hypot(*shift)>5)
        self.previous_gray=gray
        classes = [1, 2, 3, 5, 7] + ([0] if include_people else [])
        result = self.detector.track(bgr, persist=True, tracker='bytetrack.yaml',
                                     classes=classes, conf=.4, imgsz=640,
                                     device=self.device, verbose=False)[0]
        objects = []
        for box in result.boxes:
            label = int(box.cls.item())
            objects.append({'box': box.xyxy[0].cpu().tolist(),
                            'label': result.names[label],
                            'confidence': round(float(box.conf.item()), 3),
                            'track_id': int(box.id.item()) if box.id is not None else None})
        depth = None
        metric = False
        if self.depth_model is not None and self.mode == 'da3':
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            depth = np.asarray(self.depth_model.infer(rgb), dtype=np.float32)
            if focal_ratio is not None:
                # DA3 Metric output is canonical-focal depth. fx normalized by image
                # width stays constant under resizing; use output width here.
                depth = depth * (float(focal_ratio)*depth.shape[1]/300.)
                metric = True
        return objects, depth, metric


def encode_jpeg(image):
    import base64
    ok, data = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return base64.b64encode(data).decode() if ok else None


def depth_preview(depth):
    valid = np.isfinite(depth) & (depth > 0)
    if not valid.any():
        return None
    lo, hi = np.percentile(depth[valid], [5, 95])
    normalized = np.clip((depth-lo)/max(hi-lo, 1e-6), 0, 1)
    normalized = np.nan_to_num(normalized)
    return encode_jpeg(cv2.applyColorMap((normalized*255).astype('uint8'), cv2.COLORMAP_TURBO))
