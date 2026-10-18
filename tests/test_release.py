# SPDX-License-Identifier: AGPL-3.0-only
import importlib.util
from pathlib import Path
import pytest
from rider.haptics import Haptics
from rider.vision import Vision

def test_no_sdk_stop_and_clear(monkeypatch):
    monkeypatch.setenv('RIDER_HARDWARE','off')
    h=Haptics()
    try:
        h.clear_alert(); h.stop()
        assert not any(h.outputs.values())
        with pytest.raises(RuntimeError,match='Hardware is disabled'):h.scan()
    finally:h.close()

def test_missing_weights_never_load_or_download(monkeypatch,tmp_path):
    from rider import vision
    monkeypatch.setattr(vision,'ROOT',tmp_path)
    with pytest.raises(RuntimeError,match='download_models.py'):Vision().load('detect')
    assert list(tmp_path.iterdir())==[]

def test_downloader_rejects_unverified_existing_file(monkeypatch,tmp_path):
    import json,sys,hashlib
    path=Path(__file__).resolve().parents[1]/'scripts/download_models.py'
    spec=importlib.util.spec_from_file_location('download_models',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    (tmp_path/'models').mkdir();(tmp_path/'models/test.pt').write_bytes(b'bad')
    (tmp_path/'models.lock.json').write_text(json.dumps({'test':dict(filename='test.pt',size=3,sha256=hashlib.sha256(b'good').hexdigest(),url='https://example.invalid',license='test',revision='test')}))
    monkeypatch.setattr(module,'ROOT',tmp_path)
    monkeypatch.setattr(sys,'argv',['download_models.py','test','--accept-license'])
    with pytest.raises(SystemExit,match='failed verification'):module.main()
