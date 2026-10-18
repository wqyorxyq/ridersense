# SPDX-License-Identifier: AGPL-3.0-only
import time
from rider.haptics import Haptics as RealHaptics
from enum import IntEnum
from types import SimpleNamespace
class Wave(IntEnum):
    END_SEQUENCE=0
    STRONG_CLICK_P30=1
    STRONG_CLICK_P60=2
    BUZZ5_P20=3
    BUZZ4_P40=4
    BUZZ3_P60=5
    BUZZ2_P80=6
# Arbitrary test-only symbols; not copied SDK values.
FAKE_SDK=SimpleNamespace(VibrationWaveforms=Wave,VibrationMode=SimpleNamespace(OFF=0,LIBRARY=1))
def Haptics(): return RealHaptics(sdk=FAKE_SDK)

class Registers:
    def __init__(self): self.mode=None; self.intensity=None
    def set_vibration_mode(self,x): self.mode=x
    def set_vibration_intensity(self,x): self.intensity=x

class FakeDot:
    def __init__(self): self.calls=[]; self.registers=Registers(); self.heat=0; self.led=None; self.skin=25.
    def play_vibration_sequence(self,x): self.calls.append(x)
    def set_vibration_sequence(self,x): self.planned=x
    def start_vibration_sequence(self): self.calls.append(self.planned)
    def disable_all_thermal(self): self.heat=0
    def activate_thermal_intensity_control(self,x): self.heat=x
    def set_led_off(self): self.led=None
    def set_led(self,*rgb): self.led=rgb
    def get_skin_temperature(self): return self.skin
    def get_heatsink_temperature(self): return 26.

def test_stale_result_cannot_pulse():
    h=Haptics(); d=FakeDot(); h.devices={1:d,2:d,3:d,4:d};h.arm()
    h.offer([{'level':2,'direction':'front','distance_m':1}],time.monotonic()-3)
    time.sleep(.08)
    assert d.calls==[]
    h.close()

def test_finite_pulse_and_stop():
    h=Haptics();d=FakeDot();h.devices={1:d};h.pulse(1)
    assert len(d.calls)==1 and d.calls[0][-1]==0
    h.stop()
    assert d.registers.mode==0 and d.registers.intensity==0 and not h.armed
    h.close()

def test_thermal_deadline_and_light_scaling():
    h=Haptics();d=FakeDot();h.devices={1:d}
    h.set_light(1,200,100,0,.5)
    assert d.led==(100,50,0)
    h.set_thermal(1,-.15,.1)
    assert d.heat==-.15
    time.sleep(.2)
    assert d.heat==0 and not h.thermal
    h.set_thermal(1,.15,3)
    h.stop()
    assert d.heat==0 and d.led is None
    h.close()

def test_temperature_limit_and_no_deadline_extension():
    import pytest
    h=Haptics();d=FakeDot();h.devices={1:d}
    d.skin=41
    with pytest.raises(ValueError):h.set_thermal(1,.2,3)
    assert d.heat==0
    d.skin=25
    h.set_thermal(1,.2,3)
    with pytest.raises(ValueError):h.set_thermal(1,.2,3)
    d.skin=42
    with h.lock:h.next_temperature_check=0;h._check_thermal(time.monotonic())
    assert d.heat==0
    h.close()

def test_30_second_pulse_keeps_deadline():
    import pytest
    h=Haptics();d=FakeDot();h.devices={1:d}
    before=time.monotonic()
    h.set_thermal(1,.15,30)
    assert before+29.9 <= h.thermal[1]['until'] <= time.monotonic()+30
    with pytest.raises(ValueError):h.set_thermal(1,.15,30.1)
    h.stop();h.close()


def test_selection_and_stop_clear_all_channels():
    h=Haptics();h.devices={i:FakeDot() for i in range(1,5)};h.arm()
    def obj(key,score,direction):return dict(track_id=key,risk_score=score,direction=direction,level=2)
    h.offer([obj(1,80,'rear_left'),obj(2,75,'rear_right')],time.monotonic())
    assert h.target['track_id']==1 and h.outputs=={1:.2,2:.8,3:0,4:0}
    h.offer([obj(1,80,'rear_left'),obj(2,85,'rear_right')],time.monotonic())
    assert h.target['track_id']==1
    h.offer([obj(1,80,'rear_left'),obj(2,95,'rear_right')],time.monotonic())
    assert h.target['track_id']==2
    h.offer([],time.monotonic());assert h.target is None and not any(h.outputs.values())
    h.stop();h.offer([obj(1,99,'rear')],time.monotonic())
    assert h.target is None
    h.close()

def test_channels_library_mapping_and_expiry():
    h=Haptics();h.devices={i:FakeDot() for i in range(1,5)}
    h.pulse_channels({1:.2,2:.8,3:0,4:0})
    assert h.command['channels'][1]['nominal']==.2
    assert h.command['channels'][2]['nominal']==.8
    assert h.devices[1].calls[-1][-1]==0
    h.arm();h.offer([dict(track_id=1,risk_score=80,level=2,direction='rear')],time.monotonic()-1.45)
    time.sleep(.15)
    assert h.target is None and not any(h.outputs.values())
    h.close()


def test_thermal_clears_auto_and_blocks_rearm():
    import pytest
    h=Haptics();h.devices={i:FakeDot() for i in range(1,5)};h.arm()
    h.offer([dict(track_id=1,risk_score=90,level=2,direction='rear')],time.monotonic())
    h.set_thermal(1,.15,.1)
    assert not h.armed and h.target is None and not any(h.outputs.values())
    with pytest.raises(ValueError):h.arm()
    h.stop();h.close()


def test_all_sequences_prepared_before_any_trigger():
    events=[]
    class Traced(FakeDot):
        def set_vibration_sequence(self,x):
            super().set_vibration_sequence(x);events.append('prepare')
        def start_vibration_sequence(self):
            super().start_vibration_sequence();events.append('trigger')
    h=Haptics();h.devices={1:Traced(),2:Traced()}
    h.pulse_channels({1:.2,2:.8})
    assert events==['prepare','prepare','trigger','trigger']
    assert h.command['start_span_ms']>=0
    h.close()
