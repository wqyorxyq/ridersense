# SPDX-License-Identifier: AGPL-3.0-only
"""Scan tracked content and every reachable Git blob without printing secrets."""
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def main():
    files=git('ls-files','-z').decode().split('\0')
    forbidden_dirs={'.venv','vendor','models','certs','node_modules','__pycache__','.runtime'}
    forbidden_suffixes={'.pt','.safetensors','.part','.partial','.pem','.key','.mobileconfig','.mp4','.mov','.log','.zip','.pdf','.dll','.exe'}
    patterns=[rb'-----BEGIN [A-Z ]*PRIVATE KEY-----',rb'gh[pousr]_[A-Za-z0-9]{30,}',rb'github_pat_[A-Za-z0-9_]{30,}',rb'AKIA[A-Z0-9]{16}',rb'(?i)[A-Z]:[\\/](?:Users|Hackson)[\\/]',rb'\b192\.168\.\d{1,3}\.\d{1,3}\b']
    issues=[]
    def inspect(name,data):
        if len(data)>2_000_000:issues.append((name,'oversized file'))
        if any(re.search(p,data) for p in patterns):issues.append((name,'sensitive pattern; value withheld'))
    for name in filter(None,files):
        p=Path(name)
        if forbidden_dirs.intersection(p.parts) or p.suffix.lower() in forbidden_suffixes or p.name.startswith('.env'):
            issues.append((name,'forbidden artifact'))
        inspect(name,(ROOT/p).read_bytes())
        inspect(name+' (index)',git('show',':'+name))
    # Every committed blob, including deleted files in earlier commits.
    refs=git('rev-list','--all','--objects').decode().splitlines()
    seen=set()
    for row in refs:
        oid,_,name=row.partition(' ')
        if oid in seen:continue
        seen.add(oid)
        if git('cat-file','-t',oid).strip()==b'blob':inspect(name or oid,git('cat-file','blob',oid))
    for name,reason in issues:print(f'{name}: {reason}')
    if issues:raise SystemExit('Release audit failed; no secret values were printed.')
    print(f'Release audit passed: {len(list(filter(None,files)))} tracked files; {len(seen)} historical objects examined.')
if __name__=='__main__':main()
