# SPDX-License-Identifier: AGPL-3.0-only
import numpy as np
import pytest
from rider.risk import RiskEngine, object_depth, direction
from rider.alert_config import channels, level_for

def det(area=.1,x=.5,key=1):
    side=area**.5*100
    return dict(box=[x*100-side/2,0,x*100+side/2,side],label='car',track_id=key,confidence=.9)

def test_direction_and_mirror():
    for x,name in zip([.05,.3,.5,.7,.95],['right','rear_right','rear','rear_left','left']):
        assert direction([x*100,0,x*100,1],100)==name
        assert direction([(1-x)*100,0,(1-x)*100,1],100,True)==name

@pytest.mark.parametrize('score,expected',[(0,0),(40,0),(40.01,1),(70,1),(70.01,2),(100,2)])
def test_boundaries(score,expected): assert level_for(score)==expected

def test_hysteresis():
    assert level_for(68,2)==2
    assert level_for(65,2)==1
    assert level_for(38,1)==1
    assert level_for(35,1)==0

@pytest.mark.parametrize('name,high,medium',[
    ('left',{1:.8},[]),('right',{2:.8},[]),('rear_left',{1:.2,2:.8},[2]),
    ('rear_right',{3:.8,4:.2},[3]),('rear',{2:.8,3:.8},[2,3])])
def test_channels(name,high,medium):
    assert {k:v for k,v in channels(name,80).items() if v}==high
    assert [k for k,v in channels(name,50).items() if v]==medium
    assert not any(channels(name,40).values())
    for k in medium: assert channels(name,45)[k]<channels(name,65)[k]<.8

def test_missing_depth_fallback_never_claims_distance():
    for value in [float('nan'),0,float('inf'),-1]:
        r=RiskEngine().update([det(.05)],np.full((100,100),value),(100,100),1,True)[0]
        assert r['distance_m'] is None and r['closing_mps'] is None
        assert r['level']==0 and r['risk_mode']=='area-fallback'
    r=RiskEngine().update([det(.35)],None,(100,100),1)[0]
    assert r['level']==2 and r['distance_m'] is None

def test_center_crop_rejects_background():
    depth=np.full((100,100),40.);depth[25:75,25:75]=3.
    assert object_depth(depth,[0,0,100,100],(100,100))==3.

def test_approach_growth_and_track_expiration():
    e=RiskEngine()
    a=e.update([det()],np.full((100,100),8.),(100,100),1,True)[0]
    b=e.update([det(.12)],np.full((100,100),6.),(100,100),1.5,True)[0]
    assert b['closing_mps']>0 and b['risk_score']>a['risk_score']
    c=e.update([det()],np.full((100,100),20.),(100,100),5,True)[0]
    assert c['distance_m']==20 and c['closing_mps'] is None

def test_depth_jump_dropped_and_track_switch_no_speed():
    e=RiskEngine(); e.update([det()],np.full((100,100),30.),(100,100),1,True)
    b=e.update([det()],np.full((100,100),1.),(100,100),1.2,True)[0]
    assert b['distance_m'] is None and b['closing_mps'] is None
    c=e.update([det(key=2)],np.full((100,100),3.),(100,100),1.3,True)[0]
    assert c['closing_mps'] is None

def test_direction_deadband_and_intrinsics():
    e=RiskEngine();a=e.update([det(x=.59)],None,(100,100),1)[0]
    b=e.update([det(x=.61)],None,(100,100),1.2)[0]
    assert a['direction']==b['direction']=='rear'
    c=e.update([det(x=.9,key=2)],None,(100,100),2,intrinsics_fx=.8,intrinsics_verified=True)[0]
    assert c['direction_method']=='intrinsics-angle' and c['angle_deg']>0


def test_camera_motion_discards_temporal_speed():
    e=RiskEngine();e.update([det()],np.full((100,100),8.),(100,100),1,True)
    r=e.update([det(.15)],np.full((100,100),6.),(100,100),1.2,True,motion_unstable=True)[0]
    assert r['closing_mps'] is None and r['area_growth']==0 and r['motion_filtered']


def test_numpy_motion_flag_is_json_serializable():
    import json
    r=RiskEngine().update([det()],None,(100,100),1,motion_unstable=np.bool_(True))
    assert json.loads(json.dumps(r))[0]['motion_filtered'] is True
