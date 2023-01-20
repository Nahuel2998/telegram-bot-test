#!/usr/bin/env python

import os
import subprocess
import platform

src_path = os.path.join(os.path.dirname(__file__), 'src')
venv_path = os.path.join(src_path, 'venv')

python3 = os.path.join(venv_path, 'bin', 'python3') \
    if platform.system() != 'Windows' else \
    os.path.join(venv_path, 'Scripts', 'python3.exe') 

try:
    subprocess.call([python3, os.path.join(src_path, 'main.py')])
except KeyboardInterrupt:
    pass

