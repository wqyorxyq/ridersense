# SPDX-License-Identifier: AGPL-3.0-only
"""Local HTTPS gateway and certificate-only bootstrap server for iPhone.

Does not expose /api/session or private keys. The existing local application
continues to own the camera, model and USB controller.
"""
import argparse
import hashlib
import http.client
import ipaddress
import json
import plistlib
import posixpath
import ssl
import threading
import uuid
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
CERTS = ROOT / 'certs'


def prepare(address):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
    ip = ipaddress.ip_address(address)
    if not ip.is_private or ip.is_loopback:
        raise ValueError('Use the private LAN address of this laptop')
    CERTS.mkdir(exist_ok=True)
    metadata = CERTS / 'iphone.json'
    if metadata.exists():
        old = json.loads(metadata.read_text())
        if old['address'] == address and datetime.fromisoformat(old['expires']) > datetime.now(timezone.utc)+timedelta(hours=1):
            if all((CERTS / name).is_file() for name in ('server.pem','server-key.pem','ca.pem','ridersense.mobileconfig')):
                return old
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=7)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'RiderSense Demo CA')])
    ca = (x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name)
          .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
          .not_valid_before(now-timedelta(minutes=5)).not_valid_after(expires)
          .add_extension(x509.BasicConstraints(ca=True,path_length=0),critical=True)
          .add_extension(x509.KeyUsage(digital_signature=True,content_commitment=False,
              key_encipherment=False,data_encipherment=False,key_agreement=False,
              key_cert_sign=True,crl_sign=True,encipher_only=False,decipher_only=False),critical=True)
          .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()),critical=False)
          .sign(ca_key,hashes.SHA256()))
    key = rsa.generate_private_key(public_exponent=65537,key_size=2048)
    cert = (x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'RiderSense LAN')]))
            .issuer_name(ca_name).public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now-timedelta(minutes=5)).not_valid_after(expires)
            .add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True)
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ip)]),critical=False)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),critical=False)
            .add_extension(x509.KeyUsage(digital_signature=True,content_commitment=False,
                key_encipherment=True,data_encipherment=False,key_agreement=False,
                key_cert_sign=False,crl_sign=False,encipher_only=False,decipher_only=False),critical=True)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),critical=False)
            .sign(ca_key,hashes.SHA256()))
    der = ca.public_bytes(serialization.Encoding.DER)
    (CERTS/'ca.pem').write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    (CERTS/'server.pem').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    (CERTS/'server-key.pem').write_bytes(key.private_bytes(serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    payload = dict(PayloadType='com.apple.security.root',PayloadVersion=1,
        PayloadIdentifier='local.ridersense.demo.ca',PayloadUUID=str(uuid.uuid4()),
        PayloadDisplayName='RiderSense Demo CA',PayloadContent=der)
    profile = dict(PayloadType='Configuration',PayloadVersion=1,
        PayloadIdentifier='local.ridersense.demo',PayloadUUID=str(uuid.uuid4()),
        PayloadDisplayName='RiderSense Demo CA',PayloadOrganization='RiderSense local demo',
        PayloadDescription='Seven-day local certificate for the RiderSense iPhone camera demo. No device management.',
        PayloadContent=[payload],PayloadRemovalDisallowed=False)
    (CERTS/'ridersense.mobileconfig').write_bytes(plistlib.dumps(profile))
    info = dict(address=address,expires=expires.isoformat(),sha256=hashlib.sha256(der).hexdigest())
    metadata.write_text(json.dumps(info,indent=2))
    # The CA signing key is deliberately not saved.
    return info


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, data, content_type='application/json'):
        self.send_response(status)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store')
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_):
        pass  # Do not write uploaded images, pairing secrets or request URLs to logs.

    def do_GET(self):
        self.route()

    def do_POST(self):
        self.route()

    def route(self):
        path=posixpath.normpath(unquote(urlsplit(self.path).path))
        if self.server.bootstrap:
            if self.command!='GET': return self.reply(405,b'{}')
            if path=='/ridersense.mobileconfig':
                return self.reply(200,(CERTS/'ridersense.mobileconfig').read_bytes(),'application/x-apple-aspen-config')
            if path=='/':
                address=self.server.server_address[0]
                body=(f'<meta name="viewport" content="width=device-width"><h1>RiderSense iPhone</h1>'
                      f'<p>1. <a href="/ridersense.mobileconfig">Install RiderSense Demo CA profile</a></p>'
                      f'<p>2. Settings / General / About / Certificate Trust Settings: trust RiderSense Demo CA.</p>'
                      f'<p>3. <a href="https://{address}:8766/">Open secure camera dashboard</a></p>').encode()
                return self.reply(200,body,'text/html; charset=utf-8')
            return self.reply(404,b'{}')
        # Local-only session endpoint must never be reachable through a loopback proxy.
        if path.startswith('/api/session') or path.startswith('//'):
            return self.reply(403,b'{"detail":"Enter the pairing token from the laptop dashboard"}')
        if self.headers.get('Transfer-Encoding'):
            return self.reply(400,b'{"detail":"Use Content-Length"}')
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<=length<=3_100_000: return self.reply(413,b'{}')
        except ValueError: return self.reply(400,b'{}')
        self.connection.settimeout(15)
        connection=http.client.HTTPConnection('127.0.0.1',8765,timeout=20)
        try:
            body=self.rfile.read(length) if length else None
            headers={k:self.headers[k] for k in ('Content-Type','X-Rider-Token') if k in self.headers}
            connection.request(self.command,self.path,body=body,headers=headers)
            result=connection.getresponse()
            self.reply(result.status,result.read(),result.getheader('Content-Type','application/json'))
        except (OSError,http.client.HTTPException):
            self.reply(502,b'{"detail":"Local RiderSense server is not available"}')
        finally: connection.close()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--ip',required=True)
    args=parser.parse_args()
    info=prepare(args.ip)
    secure=ThreadingHTTPServer((args.ip,8766),Handler)
    secure.bootstrap=False
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version=ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(CERTS/'server.pem',CERTS/'server-key.pem')
    secure.socket=context.wrap_socket(secure.socket,server_side=True)
    bootstrap=ThreadingHTTPServer((args.ip,8767),Handler)
    bootstrap.bootstrap=True
    threading.Thread(target=bootstrap.serve_forever,daemon=True).start()
    print(f'Certificate setup: http://{args.ip}:8767/',flush=True)
    print(f'iPhone camera: https://{args.ip}:8766/',flush=True)
    print(f'Certificate expires: {info["expires"]}',flush=True)
    try: secure.serve_forever()
    except KeyboardInterrupt: pass
    finally:
        bootstrap.shutdown()
        bootstrap.server_close()
        secure.server_close()


if __name__=='__main__': main()
