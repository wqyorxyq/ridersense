# SPDX-License-Identifier: AGPL-3.0-only
from fastapi.testclient import TestClient
from rider.server import app, TOKEN

client=TestClient(app)
headers={'x-rider-token':TOKEN}

def test_dashboard_and_access_control():
    assert client.get('/').status_code==200
    assert client.get('/api/status').status_code==401
    assert client.get('/api/status',headers=headers).status_code==200

def test_bad_calibration_and_mapping_rejected():
    assert client.post('/api/settings',headers=headers,json={'calibrated':True}).status_code==400
    assert client.post('/api/settings',headers=headers,json={'near':1,'urgent':2}).status_code==400
    assert client.post('/api/haptics/mapping',headers=headers,json={'left':1,'front':1,'right':3}).status_code==400

def test_source_change_resets_calibration():
    assert client.post('/api/settings',headers=headers,json={'calibrated':True,'focal_ratio':.8}).status_code==200
    client.post('/api/source/reset',headers=headers)
    s=client.get('/api/status',headers=headers).json()
    assert not s['settings']['calibrated']
    assert client.post('/api/haptics/arm',headers=headers).status_code==409

def test_thermal_duration_up_to_30_seconds(monkeypatch):
    from rider import server
    calls=[]
    monkeypatch.setattr(server.haptics,'set_thermal',lambda *args:calls.append(args))
    assert client.post('/api/haptics/thermal/1',headers=headers,json={'intensity':.15,'seconds':30}).status_code==200
    assert calls==[(1,.15,30)]
    assert client.post('/api/haptics/thermal/1',headers=headers,json={'intensity':.15,'seconds':30.1}).status_code==422

def test_calibration_needs_fresh_depth():
    assert client.post('/api/calibrate',headers=headers,json={'track_id':1,'distance_m':2}).status_code==409


def test_simulation_isolation_and_stop():
    from rider import server
    r=client.post('/api/simulation',headers=headers,json={'direction':'rear_left','score':80})
    assert r.status_code==200 and r.json()['outputs']['2']==.8
    assert server.state['mode']=='simulation'
    assert client.post('/api/haptics/arm',headers=headers).status_code==409
    client.post('/api/stop',headers=headers)
    assert server.haptics.target is None and not any(server.haptics.outputs.values())
    client.post('/api/live',headers=headers)
    assert server.state['mode']=='live'

def test_intrinsic_validation():
    assert client.post('/api/settings',headers=headers,json={'intrinsics_verified':True}).status_code==400
    assert client.post('/api/settings',headers=headers,json={'intrinsics_verified':True,'intrinsics_fx':.8}).status_code==200
    client.post('/api/source/reset',headers=headers)


def test_replay_wrap_clears_history_but_preserves_arming(monkeypatch):
    from rider import server
    import time
    client.post('/api/live',headers=headers)
    monkeypatch.setattr(server.haptics,'pulse_channels',lambda output:None)
    server.state['result']={'source':'video-replay'}
    server.haptics.armed=True
    server.haptics.target={'direction':'rear','level':2}
    server.haptics.outputs={1:0,2:.8,3:.8,4:0}
    server.haptics.expires=time.monotonic()+10
    previous=server.state['generation']
    r=client.post('/api/replay/reset',headers=headers)
    assert r.status_code==200 and server.haptics.armed
    assert not any(server.haptics.outputs.values()) and server.haptics.target is None
    assert server.state['result'] is None and server.state['generation']==previous+1
    client.post('/api/stop',headers=headers)
    server.state['result']={'source':'computer-camera'}
    assert client.post('/api/replay/reset',headers=headers).status_code==409
    client.post('/api/stop',headers=headers)
