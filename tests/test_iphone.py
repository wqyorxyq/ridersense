# SPDX-License-Identifier: AGPL-3.0-only
"""Gateway boundary checks on loopback only; no phone, camera, or certificates."""
import importlib.util
from pathlib import Path
import threading
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import urlopen
import pytest

@pytest.mark.parametrize('path',['/api/session','/%61pi/session','/x/../api/session','/api%2fsession'])
def test_gateway_cannot_retrieve_pairing_token(path):
    source=Path(__file__).resolve().parents[1]/'scripts/iphone_access.py'
    spec=importlib.util.spec_from_file_location('iphone_access',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    server=ThreadingHTTPServer(('127.0.0.1',0),module.Handler)
    server.bootstrap=False
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with pytest.raises(HTTPError) as caught:
            urlopen(f'http://127.0.0.1:{server.server_port}{path}',timeout=2)
        assert caught.value.code==403
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)
