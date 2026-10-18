# SPDX-License-Identifier: AGPL-3.0-only
"""Demonstration proximity rules, not a collision prediction system."""
from dataclasses import dataclass
import math
import numpy as np


def direction(box, width, mirrored=False):
    from rider.alert_config import DIRECTIONS, CONFIG
    x=(box[0]+box[2])/(2*width)
    if mirrored: x=1-x
    return DIRECTIONS[sum(x>edge for edge in CONFIG['edges'])]


def object_depth(depth, box, image_shape):
    """Use an inset box to reduce (not eliminate) background contamination."""
    h, w = image_shape[:2]
    dh, dw = depth.shape
    x1, y1, x2, y2 = box
    ix, iy = (x2-x1)*.25, (y2-y1)*.25
    xa, xb = [int(np.clip(v*dw/w, 0, dw)) for v in (x1+ix, x2-ix)]
    ya, yb = [int(np.clip(v*dh/h, 0, dh)) for v in (y1+iy, y2-iy)]
    values = depth[ya:yb, xa:xb]
    values = values[np.isfinite(values) & (values > 0)]
    return float(np.median(values)) if values.size >= 9 else None


class RiskEngine:
    def __init__(self): self.tracks = {}
    def reset(self): self.tracks.clear()

    def update(self, detections, depth, shape, now, metric=False, near=5., urgent=2.,
               image_area_demo=False, input_mirrored=False, intrinsics_fx=None,
               intrinsics_cx=.5, intrinsics_verified=False, motion_unstable=False):
        from rider.alert_config import CONFIG as c, level_for, DIRECTIONS
        self.tracks = {k:v for k,v in self.tracks.items() if 0 <= now-v['time'] < c['max_gap']}
        output=[]
        for det in detections:
            key=det.get('track_id'); old=self.tracks.get(key) if key is not None else None
            if motion_unstable: old=None
            x1,y1,x2,y2=det['box']; h,w=shape[:2]
            area=float(np.clip((x2-x1)*(y2-y1)/(w*h),0,1))
            x=(x1+x2)/(2*w); x=1-x if input_mirrored else x
            dt=now-old['time'] if old else 0
            if old and (abs(area-old['area'])>c['max_area_jump'] or abs(x-old['x'])>.25): old=None
            value=object_depth(depth,det['box'],shape) if depth is not None else None
            distance=value if metric and not image_area_demo else None
            closing=None; growth=0.
            if old and .05 < dt < c['max_gap']:
                growth=max(0.,min(c['growth_full'],(area-old['area'])/dt))
                if distance is not None and old['distance'] is not None:
                    delta=(old['distance']-distance)/dt
                    if abs(delta)>c['max_relative_speed']: distance=None
                    else:
                        distance=.45*distance+.55*old['distance']
                        closing=(old['distance']-distance)/dt
                x=.55*x+.45*old['x']
            angular=intrinsics_verified and intrinsics_fx is not None
            coordinate=math.degrees(math.atan((x-intrinsics_cx)/intrinsics_fx)) if angular else x
            edges=c['angle_edges'] if angular else c['edges']
            idx=sum(coordinate>edge for edge in edges)
            if old and old['angular']==angular:
                oldidx=old['idx']; margin=3. if angular else c['direction_margin']
                lower=edges[oldidx-1]-margin if oldidx else -float('inf')
                upper=edges[oldidx]+margin if oldidx<4 else float('inf')
                if lower<=coordinate<=upper: idx=oldidx
            a=min(1.,area/c['area_full']); g=min(1.,growth/c['growth_full'])
            mode='metric' if distance is not None else 'area-fallback'
            if distance is not None:
                d=float(np.clip((c['distance_far']-distance)/(c['distance_far']-c['distance_near']),0,1))
                v=float(np.clip((closing or 0)/c['closing_full'],0,1))
                features=[a,g,d,v]; weights=c['metric_weights']
            else: features=[a,g]; weights=c['area_weights']
            score=100*sum(f*t for f,t in zip(features,weights))
            if old: score=c['alpha']*score+(1-c['alpha'])*old['score']
            level=level_for(score,old['level'] if old else 0)
            if key is not None:
                self.tracks[key]=dict(time=now,area=area,x=x,distance=distance,score=score,level=level,idx=idx,angular=angular)
            output.append(dict(det,direction=DIRECTIONS[idx],level=level,risk_score=round(score,2),
                distance_m=round(distance,2) if distance is not None else None,
                closing_mps=round(closing,2) if closing is not None else None,
                depth_value=value,image_fraction=round(area,4),area_growth=round(growth,4),
                risk_mode=mode,direction_method='intrinsics-angle' if angular else 'image-bands',
                motion_filtered=bool(motion_unstable),angle_deg=round(coordinate,1) if angular else None))
        return output
