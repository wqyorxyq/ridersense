# SPDX-License-Identifier: AGPL-3.0-only
"""Start the dashboard without downloading models or opening hardware."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    import uvicorn
    uvicorn.run('rider.server:app',host='127.0.0.1',port=args.port)
