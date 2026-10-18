# SPDX-License-Identifier: AGPL-3.0-only
import asyncio
import copy
import os
import secrets
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from rider.haptics import Haptics
from rider.risk import RiskEngine
from rider.vision import Vision, encode_jpeg, depth_preview

ROOT = Path(__file__).resolve().parents[1]
TOKEN = os.environ.get('RIDER_TOKEN') or secrets.token_urlsafe(24)
haptics = Haptics()
vision = Vision()
risk = RiskEngine()
lock = threading.RLock()
inference_lock = threading.Lock()
state = {'model_status': 'not_loaded', 'error': None, 'result': None,
         'settings': {'focal_ratio': None, 'calibrated': False, 'near': 5.,
                      'urgent': 2., 'include_people': False, 'image_area_demo':False, 'input_mirrored':False, 'intrinsics_fx':None, 'intrinsics_cx':.5, 'intrinsics_verified':False}, 'generation': 0, 'mode':'live'}
pending = None
running = True
camera_stop = threading.Event()
camera_thread = None


def worker():
    global pending
    while running:
        with lock:
            job = pending
            pending = None
            settings = dict(state['settings'])
        if job is None:
            time.sleep(.015)
            continue
        frame, received, generation, seq, source = job
        if time.monotonic()-received > 1.5:
            continue
        start = time.monotonic()
        try:
            with inference_lock:
                objects, depth, metric = vision.infer(frame,
                    settings['focal_ratio'] if settings['calibrated'] else None,
                    settings['include_people'])
                with lock:
                    if generation != state['generation'] or state['mode'] != 'live':
                        continue
                    objects = risk.update(objects, depth, frame.shape, received, metric,
                                          settings['near'], settings['urgent'], settings['image_area_demo'],
                                          settings.get('input_mirrored',False),settings.get('intrinsics_fx'),
                                          settings.get('intrinsics_cx',.5),settings.get('intrinsics_verified',False),
                                          vision.motion_unstable)
            elapsed = time.monotonic()-start
            result = {'seq': seq, 'source': source, 'objects': objects,
                      'metric': metric, 'received': received, 'inference_ms': round(elapsed*1000),
                      'image_area_demo': settings['image_area_demo'],
                      'image': encode_jpeg(frame),
                      'depth_image': depth_preview(depth) if depth is not None else None,
                      'depth_width': depth.shape[1] if depth is not None else None,
                      'width': frame.shape[1], 'height': frame.shape[0]}
            with lock:
                if generation != state['generation'] or state['mode'] != 'live':
                    continue
                result['pipeline_ms']=round((time.monotonic()-received)*1000)
                state['result'] = result
                state['error'] = None
                haptics.offer(objects, received)
        except Exception as exc:
            with lock:
                state['error'] = f'{type(exc).__name__}: {exc}'
            haptics.stop()


@asynccontextmanager
async def lifespan(app):
    global running
    threading.Thread(target=worker, daemon=True).start()
    yield
    running = False
    camera_stop.set()
    haptics.close()


app = FastAPI(title='RiderSense', lifespan=lifespan)


@app.middleware('http')
async def protect(request: Request, call_next):
    # Local dashboard can obtain the token; remote cameras must pair explicitly.
    if request.url.path.startswith('/api/') and request.url.path != '/api/session':
        if not secrets.compare_digest(request.headers.get('x-rider-token', ''), TOKEN):
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail': 'Pair this device with the dashboard token'}, 401)
    return await call_next(request)


@app.get('/api/session')
def session(request: Request):
    if request.client.host not in ('127.0.0.1', '::1', 'testclient'):
        raise HTTPException(403, 'Enter pairing token from the laptop dashboard')
    return {'token': TOKEN}


@app.get('/')
def index():
    return FileResponse(ROOT/'static/index.html')


@app.get('/api/status')
def status():
    with lock:
        output = copy.deepcopy(state)
    output['haptics'] = haptics.status()
    model_file = ROOT/'models/da3metric-large.safetensors'
    downloaded = model_file.is_file()
    partial = ROOT/'models/da3metric-large.partial'
    completed = partial.stat().st_size if partial.exists() else 0
    completed += sum(p.stat().st_size for p in (ROOT/'models/da3-parts').glob('*.part'))
    output['depth_download'] = {'ready': downloaded, 'downloaded_mb': round(min(completed,1336734448)/1024**2), 'total_mb':1275}
    if output['result']:
        output['result']['age_ms'] = round((time.monotonic()-output['result']['received'])*1000)
        output['result']['stale'] = output['result']['age_ms'] > 1500
    return output


class LoadRequest(BaseModel):
    mode: str = 'da3'


@app.post('/api/models/load')
def load_models(body: LoadRequest):
    global pending
    if body.mode not in ('detect', 'da3'):
        raise HTTPException(400, 'Unknown model mode')
    if body.mode == 'da3' and not (ROOT/'models/da3metric-large.safetensors').is_file():
        raise HTTPException(409, 'DA3 weights missing. Run: python scripts/download_models.py da3metric-large --accept-license; see docs/models.md')
    with lock:
        if state['model_status'] == 'loading':
            return {'status': 'loading'}
        state['model_status'] = 'loading'
        state['generation'] += 1
        pending = None
        state['result'] = None
        state['error'] = None
    haptics.stop()
    def load():
        try:
            with inference_lock:
                vision.load(body.mode)
            with lock:
                state['model_status'] = f'ready:{vision.mode}:{vision.device}'
        except Exception as exc:
            with lock:
                state['model_status'] = 'error'
                state['error'] = f'{type(exc).__name__}: {exc}'
    threading.Thread(target=load, daemon=True).start()
    return {'status': 'loading'}


@app.post('/api/frame')
async def frame(request: Request, file: UploadFile = File(...), seq: int = 0, source: str = 'camera'):
    global pending
    raw = await file.read(3_000_001)
    if len(raw) > 3_000_000:
        raise HTTPException(413, 'Frame exceeds 3MB')
    image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None or max(image.shape[:2]) > 4096:
        raise HTTPException(400, 'Invalid image or dimensions')
    with lock:
        if state['mode'] != 'live':
            raise HTTPException(409, 'Simulation rejects live frames')
        if not state['model_status'].startswith('ready:'):
            raise HTTPException(409, 'Models are not ready')
        pending = (image, time.monotonic(), state['generation'], seq, source[:40])
    return {'accepted': seq}


class Settings(BaseModel):
    focal_ratio: float | None = Field(default=None, gt=.05, lt=10)
    calibrated: bool = False
    near: float = Field(default=5, gt=.1, le=100)
    urgent: float = Field(default=2, gt=.05, le=50)
    include_people: bool = False
    image_area_demo: bool = False
    input_mirrored: bool = False
    intrinsics_fx: float | None = Field(default=None,gt=.05,lt=10,allow_inf_nan=False)
    intrinsics_cx: float = Field(default=.5,ge=0,le=1,allow_inf_nan=False)
    intrinsics_verified: bool = False


class Calibration(BaseModel):
    track_id: int
    distance_m: float = Field(gt=.2, le=50, allow_inf_nan=False)


@app.post('/api/calibrate')
def calibrate(body: Calibration):
    """One-point demo scale fit, not a physical camera intrinsic calibration."""
    global pending
    with inference_lock, lock:
        result = state['result']
        if not result or time.monotonic()-result['received'] > 1.5:
            raise HTTPException(409, 'A fresh DA3 frame is required. Keep the camera running.')
        if result['metric']:
            raise HTTPException(400, 'Clear the calibration checkbox and apply settings before recalibrating.')
        obj = next((o for o in result['objects'] if o['track_id']==body.track_id), None)
        if not obj or not obj['depth_value'] or not result['depth_width']:
            raise HTTPException(400, 'Select an object with valid depth.')
        ratio = body.distance_m*300/(obj['depth_value']*result['depth_width'])
        if not .05 < ratio < 10:
            raise HTTPException(400, 'Invalid scale. Check the selected object and measured distance.')
        haptics.stop()
        state['settings'].update(focal_ratio=ratio, calibrated=True)
        state['generation'] += 1
        pending = None
        risk.reset()
        state['result'] = None
        return {'focal_ratio':ratio, 'method':'single-point-demo-scale'}


@app.post('/api/settings')
def settings(body: Settings):
    global pending
    if body.urgent >= body.near or (body.calibrated and body.focal_ratio is None) or (body.intrinsics_verified and body.intrinsics_fx is None):
        raise HTTPException(400, 'Check thresholds and focal calibration')
    haptics.stop()
    with inference_lock, lock:
        state['settings'] = body.model_dump()
        state['generation'] += 1
        state['result'] = None
        pending = None
        risk.reset()
        vision.reset()
    return {'ok': True}


@app.post('/api/stop')
def stop():
    global pending
    haptics.stop()
    camera_stop.set()
    with lock:
        state['generation'] += 1
        state['result'] = None
        state['simulation'] = None
        pending = None
    return {'ok': True}


@app.post('/api/source/reset')
def reset_source():
    global pending
    haptics.stop()
    camera_stop.set()
    with inference_lock, lock:
        state['generation'] += 1
        state['mode'] = 'live'
        state['settings']['intrinsics_verified'] = False
        state['settings']['calibrated'] = False
        state['settings']['focal_ratio'] = None
        state['result'] = None
        pending = None
        risk.reset()
        vision.reset()
    return {'ok': True}


@app.post('/api/replay/reset')
def reset_replay():
    """Discard temporal history at a backwards seek/loop, preserving user arming."""
    global pending
    with inference_lock, lock:
        if state['mode'] != 'live' or (state['result'] and state['result']['source'] != 'video-replay'):
            raise HTTPException(409, 'Replay reset requires video input')
        haptics.clear_alert()
        state['generation'] += 1
        state['result'] = None
        pending = None
        risk.reset()
        vision.reset()
    return {'ok': True}


@app.post('/api/camera/start')
def start_camera():
    global camera_thread, camera_stop
    if camera_thread and camera_thread.is_alive():
        raise HTTPException(409, 'The laptop camera is running or closing. Stop it and retry shortly.')
    reset_source()
    camera_stop = threading.Event()
    local_stop = camera_stop
    with lock:
        state['error'] = None
    def read_camera():
        global pending
        capture = cv2.VideoCapture(int(os.environ.get("RIDER_CAMERA_INDEX", "0")), cv2.CAP_DSHOW if os.name=='nt' else cv2.CAP_ANY)
        try:
            if not capture.isOpened():
                raise RuntimeError('Cannot open the laptop camera. Check its switch, Windows permissions and other apps using it.')
            capture.set(cv2.CAP_PROP_FRAME_WIDTH,960)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT,540)
            sequence = 0
            while not local_stop.is_set():
                received = time.monotonic()
                ok, image = capture.read()
                if not ok:
                    raise RuntimeError('The laptop camera returned no frame.')
                with lock:
                    if not local_stop.is_set() and state['mode']=='live' and state['model_status'].startswith('ready:'):
                        sequence += 1
                        pending = (image, received, state['generation'], sequence, 'computer-camera')
                local_stop.wait(.08)
        except Exception as exc:
            with lock:
                state['error'] = str(exc)
            haptics.stop()
        finally:
            capture.release()
    camera_thread = threading.Thread(target=read_camera, daemon=True)
    camera_thread.start()
    return {'status':'starting'}


@app.post('/api/haptics/scan')
def scan():
    try:
        return haptics.scan()
    except Exception as exc:
        raise HTTPException(400, str(exc))


@app.post('/api/haptics/arm')
def arm():
    with lock:
        if state['mode'] != 'live':
            raise HTTPException(409,'Exit simulation first')
        result = state['result']
        if not result or time.monotonic()-result['received'] > 1.5:
            raise HTTPException(409, 'Start a camera and wait for fresh results')
    try:
        haptics.arm()
        return haptics.status()
    except Exception as exc:
        raise HTTPException(400, str(exc))


@app.post('/api/haptics/disarm')
def disarm():
    with haptics.lock:
        haptics.armed=False
        haptics.clear_alert()
    return {'ok':True}


@app.post('/api/haptics/test/{dot_id}')
def test_dot(dot_id: int):
    try:
        haptics.stop()
        haptics.pulse(dot_id)
        return {'ok': True}
    except Exception as exc:
        raise HTTPException(400, str(exc))


class Mapping(BaseModel):
    left: int = Field(ge=1, le=4)
    front: int = Field(ge=1, le=4)
    right: int = Field(ge=1, le=4)


class ThermalCommand(BaseModel):
    intensity: float = Field(ge=-.3, le=.3, allow_inf_nan=False)
    seconds: float = Field(default=3, ge=.1, le=30, allow_inf_nan=False)


class LightCommand(BaseModel):
    red: int = Field(ge=0, le=255)
    green: int = Field(ge=0, le=255)
    blue: int = Field(ge=0, le=255)
    brightness: float = Field(default=.5, ge=0, le=1, allow_inf_nan=False)


@app.post('/api/haptics/thermal/{dot_id}')
def thermal(dot_id: int, body: ThermalCommand):
    try:
        haptics.set_thermal(dot_id, body.intensity, body.seconds)
        return {'ok': True}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@app.post('/api/haptics/light/{dot_id}')
def light(dot_id: int, body: LightCommand):
    try:
        haptics.set_light(dot_id, body.red, body.green, body.blue, body.brightness)
        return {'ok': True}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@app.get('/api/haptics/temperature/{dot_id}')
def temperature(dot_id: int):
    try:
        return haptics.read_temperature(dot_id)
    except Exception as exc:
        raise HTTPException(400, str(exc))


@app.post('/api/haptics/mapping')
def mapping(body: Mapping):
    values = body.model_dump()
    if len(set(values.values())) != 3:
        raise HTTPException(400, 'Use three different dots')
    raise HTTPException(410, 'Three-direction mapping retired; configure rider/alert_config.py')



class Simulation(BaseModel):
    direction: str
    score: float = Field(ge=0,le=100,allow_inf_nan=False)
    hardware: bool = False

@app.post('/api/simulation')
def simulate(body: Simulation):
    from rider.alert_config import DIRECTIONS, channels, level_for
    if body.direction not in DIRECTIONS: raise HTTPException(400,'Unknown direction')
    stop()
    with lock:
        state['mode']='simulation'
        state['simulation']={'direction':body.direction,'risk_score':body.score,
                             'outputs':channels(body.direction,body.score),'hardware':body.hardware}
        if body.hardware:
            try:
                haptics.arm()
                haptics.offer([dict(direction=body.direction,risk_score=body.score,
                                    level=level_for(body.score),track_id=-1)],time.monotonic())
            except Exception as exc:
                haptics.stop()
                raise HTTPException(400,str(exc))
    return state['simulation']

@app.post('/api/live')
def live():
    reset_source()
    return {'ok':True}

app.mount('/static', StaticFiles(directory=ROOT/'static'), name='static')
