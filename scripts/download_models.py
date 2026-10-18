# SPDX-License-Identifier: AGPL-3.0-only
"""Explicit official download; revision, size and SHA-256 are locked."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen
ROOT=Path(__file__).resolve().parents[1]
def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def main():
    models=json.loads((ROOT/'models.lock.json').read_text())
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model',choices=models)
    parser.add_argument('--accept-license',action='store_true')
    args=parser.parse_args(); entry=models[args.model]
    print(f"{args.model}: {entry['size']:,} bytes; {entry['license']}; revision {entry['revision']}")
    print(entry['url']); print('Read MODEL_LICENSES.md before downloading.')
    if not args.accept_license:parser.error('Re-run with --accept-license after reviewing the license.')
    dest=ROOT/'models'/entry['filename'];dest.parent.mkdir(exist_ok=True)
    if dest.exists():
        if dest.stat().st_size==entry['size'] and digest(dest)==entry['sha256']:
            print('Existing file verified.');return
        raise SystemExit('Existing file failed verification; move it aside and retry.')
    partial=dest.with_suffix('.partial')
    with urlopen(entry['url'],timeout=60) as response,partial.open('wb') as output:
        while chunk:=response.read(1024*1024):output.write(chunk)
    if partial.stat().st_size!=entry['size'] or digest(partial)!=entry['sha256']:
        raise SystemExit('Integrity check failed. Partial retained; no model installed.')
    partial.replace(dest);print('Size and SHA-256 verified.')
if __name__=='__main__':main()
