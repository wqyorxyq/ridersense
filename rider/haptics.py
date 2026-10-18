# SPDX-License-Identifier: AGPL-3.0-only
"""USB adapter for DataFeel Gen 10 vibration, timed thermal and LED control."""
from pathlib import Path
import sys
import os
import time
import threading
import math

SDK = os.environ.get('DATAFEEL_SDK_PATH')
if SDK:
    sys.path.insert(0, str(Path(SDK).resolve()))


class Haptics:
    def __init__(self, sdk=None):
        self.sdk = sdk
        self.lock = threading.RLock()
        self.devices = {}
        self.mapping = {'left': 1, 'front': 2, 'right': 3}
        self.armed = False
        self.error = None
        self.target = None
        self.expires = 0.
        self.last_pulse = 0.
        self.outputs = {i:0. for i in range(1,5)}
        self.command = None
        self.thermal = {}
        self.temperatures = {}
        self.next_temperature_check = 0.
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _sdk(self):
        if self.sdk is None:
            if os.environ.get('RIDER_HARDWARE', 'off') != 'datafeel':
                raise RuntimeError('Hardware is disabled. See docs/hardware.md to enable DataFeel explicitly.')
            try:
                import datafeel.device
                self.sdk = datafeel.device
            except ImportError as exc:
                raise RuntimeError('DataFeel SDK missing. Set DATAFEEL_SDK_PATH to your authorized SDK Python directory; see docs/hardware.md.') from exc
        return self.sdk

    def scan(self, port=None):
        Dot = self._sdk().Dot
        from serial.tools.list_ports import comports
        with self.lock:
            self.stop()
            self.close_ports()
            self.devices = {}
            ports = [p.device for p in comports() if p.vid == 0x10c4 and p.pid == 0xea60]
            if port:
                if port not in ports:
                    raise ValueError('Selected port is not a detected CP210x USB controller')
                ports = [port]
            if len(ports) > 1 and not port:
                raise ValueError('Multiple USB controllers: choose an explicit port')
            self.error = None
            for selected in ports[:1]:
                # Some controllers take longer than minimalmodbus's default
                # timeout to return the identification string.
                import minimalmodbus
                probe = minimalmodbus.Instrument(selected, 1, minimalmodbus.MODE_RTU)
                probe.serial.timeout = .5
                probe.serial.write_timeout = .5
                for address in range(1, 5):
                    try:
                        dot = Dot(selected, address)
                        dot.registers.dev.serial.timeout = .15
                        self.devices[address] = dot
                    except Exception as exc:
                        self.error = f'Address {address}: {exc}'
                if not self.devices:
                    probe.serial.close()
            return self.status()

    def close_ports(self):
        for dot in self.devices.values():
            try:
                dot.registers.dev.serial.close()
            except Exception:
                pass

    def status(self):
        with self.lock:
            return {'armed': self.armed, 'devices': [
                {'id': k, 'name': d.device_name.strip('\x00'), 'port': d.port}
                for k,d in self.devices.items()], 'mapping': dict(self.mapping),
                'target': self.target if time.monotonic() < self.expires else None,
                'outputs': dict(self.outputs), 'last_command': self.command,
                'error': self.error, 'thermal': dict(self.thermal),
                'temperatures': dict(self.temperatures)}

    def set_light(self, dot_id, red, green, blue, brightness=1.):
        if not 0 <= brightness <= 1 or any(not 0 <= c <= 255 for c in (red,green,blue)):
            raise ValueError('Invalid light color or brightness')
        with self.lock:
            dot = self.devices.get(dot_id)
            if dot is None:
                raise ValueError('Dot is not connected')
            if brightness == 0:
                dot.set_led_off()
            else:
                dot.set_led(*(round(c*brightness) for c in (red,green,blue)))

    def read_temperature(self, dot_id):
        with self.lock:
            dot = self.devices.get(dot_id)
            if dot is None:
                raise ValueError('Dot is not connected')
            skin = float(dot.get_skin_temperature())
            sink = float(dot.get_heatsink_temperature())
            if not all(math.isfinite(v) and -10 < v < 85 for v in (skin,sink)):
                raise ValueError('Temperature reading is invalid')
            result = {'skin': round(skin,2), 'sink': round(sink,2)}
            self.temperatures[dot_id] = result
            return result

    def set_thermal(self, dot_id, intensity, seconds=3.):
        if not math.isfinite(intensity) or not -.3 <= intensity <= .3:
            raise ValueError('Demo thermal intensity must be between -0.3 and 0.3')
        if not math.isfinite(seconds) or not .1 <= seconds <= 30:
            raise ValueError('Duration must be between 0.1 and 30 seconds')
        with self.lock:
            dot = self.devices.get(dot_id)
            if dot is None:
                raise ValueError('Dot is not connected')
            if intensity == 0:
                dot.disable_all_thermal()
                self.thermal.pop(dot_id, None)
                return
            if dot_id in self.thermal:
                raise ValueError('Wait for the current thermal pulse to finish or stop it first')
            temperature = self.read_temperature(dot_id)
            if not 15 < temperature['skin'] < 40 or temperature['sink'] >= 45:
                raise ValueError('Temperature outside the demo operating limits')
            self.clear_alert()
            self.armed = False
            # Register timeout before writing so even partial writes get an OFF attempt.
            self.thermal[dot_id] = {'intensity': intensity, 'until': time.monotonic()+seconds}
            try:
                dot.activate_thermal_intensity_control(intensity)
            except Exception:
                self.thermal[dot_id]['until'] = 0
                raise

    def _check_thermal(self, now):
        for dot_id, active in list(self.thermal.items()):
            stop = now >= active['until']
            if not stop and now >= self.next_temperature_check:
                try:
                    t = self.read_temperature(dot_id)
                    stop = not 15 < t['skin'] < 40 or t['sink'] >= 45
                except Exception as exc:
                    self.error = str(exc)
                    stop = True
            if stop:
                try:
                    self.devices[dot_id].disable_all_thermal()
                    del self.thermal[dot_id]
                except Exception as exc:
                    self.error = f'Thermal OFF failed; switch off controller: {exc}'
                    active['until'] = 0
        if now >= self.next_temperature_check:
            self.next_temperature_check = now+.5

    def stop(self):
        with self.lock:
            self.armed = False
            self.target = None
            self.outputs = {i:0. for i in range(1,5)}
            self.expires = 0
            errors = []
            for dot in self.devices.values():
                VibrationMode = self._sdk().VibrationMode
                for operation in (dot.disable_all_thermal, dot.set_led_off,
                                  lambda: dot.registers.set_vibration_mode(VibrationMode.OFF),
                                  lambda: dot.registers.set_vibration_intensity(0.)):
                    try:
                        operation()
                    except Exception as exc:
                        errors.append(str(exc))
            for active in self.thermal.values():
                active['until'] = 0
            if errors:
                self.error = '; '.join(errors)
            else:
                self.thermal.clear()

    def arm(self):
        with self.lock:
            if self.thermal:
                raise ValueError('Stop thermal control before arming vibration')
            if not self.devices:
                raise ValueError('No DataFeel dots detected')
            if not all(v in self.devices for v in range(1,5)):
                raise ValueError('A mapped dot is missing; check direction mapping')
            self.error = None
            self.armed = True

    def clear_alert(self):
        with self.lock:
            self.target = None
            self.expires = 0
            self.outputs = {i:0. for i in range(1,5)}
            for dot in self.devices.values():
                VibrationMode = self._sdk().VibrationMode
                dot.registers.set_vibration_mode(VibrationMode.OFF)
                dot.registers.set_vibration_intensity(0.)

    def offer(self, objects, received_at):
        from rider.alert_config import channels, CONFIG
        with self.lock:
            if not self.armed: return
            candidates = [o for o in objects if o['level'] > 0]
            selected = max(candidates,key=lambda o:o.get('risk_score',0)) if candidates else None
            if selected and self.target:
                current=next((o for o in candidates if o.get('track_id') is not None and o.get('track_id')==self.target.get('track_id')),None)
                if current and selected.get('risk_score',0)<current.get('risk_score',0)+CONFIG['switch_margin']: selected=current
            if not selected or time.monotonic()>=received_at+1.5:
                if self.target or any(self.outputs.values()): self.clear_alert()
                return
            new=channels(selected['direction'],selected.get('risk_score',80),selected['level'])
            if any(self.outputs.values()) and set(k for k,v in new.items() if v)!=set(k for k,v in self.outputs.items() if v): self.clear_alert()
            self.target = {k:selected.get(k) for k in ('direction','level','risk_score','track_id')}
            self.outputs = new
            self.expires = received_at+1.5

    def pulse_channels(self, output):
        sdk = self._sdk(); W, VibrationMode = sdk.VibrationWaveforms, sdk.VibrationMode
        # Finite library effects; nominal SDK strengths, not measured amplitudes.
        choices=[(.2,W.BUZZ5_P20),(.4,W.BUZZ4_P40),(.6,W.BUZZ3_P60),(.8,W.BUZZ2_P80)]
        started=time.monotonic(); sent={}
        with self.lock:
            for dot_id,strength in output.items():
                if strength<=0: continue
                nominal,wave=min(choices,key=lambda pair:abs(pair[0]-strength))
                dot=self.devices[dot_id]
                dot.registers.set_vibration_mode(VibrationMode.LIBRARY)
                dot.set_vibration_sequence([wave,W.END_SEQUENCE])
                sent[dot_id]={'requested':strength,'nominal':nominal,'waveform':wave.name}
            trigger_times=[]
            for dot_id in sent:
                trigger_times.append(time.monotonic())
                self.devices[dot_id].start_vibration_sequence()
            start_span=(trigger_times[-1]-trigger_times[0])*1000 if trigger_times else 0.
            self.command={'start_span_ms':round(start_span,1),'channels':sent,'write_span_ms':round((time.monotonic()-started)*1000,1),
                          'time':time.monotonic(),'status':'serial-writes-returned','physical_feedback':False}

    def pulse(self, dot_id, level=1):
        VibrationWaveforms = self._sdk().VibrationWaveforms
        with self.lock:
            if dot_id not in self.devices:
                raise ValueError('Dot is not connected')
            # Finite library effects stop on the device even if the application dies.
            waveform = VibrationWaveforms.STRONG_CLICK_P30 if level == 1 else VibrationWaveforms.STRONG_CLICK_P60
            self.devices[dot_id].play_vibration_sequence([waveform, VibrationWaveforms.END_SEQUENCE])

    def _loop(self):
        while self.running:
            with self.lock:
                now = time.monotonic()
                self._check_thermal(now)
                if self.armed and self.target and now < self.expires:
                    interval = .8 if self.target['level'] == 1 else .35
                    if now-self.last_pulse >= interval:
                        try:
                            self.pulse_channels(self.outputs)
                            self.last_pulse = now
                        except Exception as exc:
                            self.error = str(exc)
                            self.stop()
                elif now >= self.expires and (self.target or any(self.outputs.values())):
                    try: self.clear_alert()
                    except Exception as exc: self.error=str(exc); self.armed=False
            time.sleep(.03)

    def close(self):
        self.running = False
        self.stop()
        self.close_ports()

