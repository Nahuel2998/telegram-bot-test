#!/usr/bin/env python

from errno import EEXIST

import os
import venv
import platform
import subprocess

src_path = os.path.join(os.path.dirname(__file__), 'src')

venv_path = os.path.join(src_path, 'venv')

if os.path.exists(venv_path):
    print("La carpeta venv ya existe.\nYa has corrido este script?")
    exit(EEXIST)

venv.create(venv_path, with_pip=True)

pip = os.path.join(venv_path, 'bin', 'pip3') \
    if platform.system() != 'Windows' else \
    os.path.join(venv_path, 'Scripts', 'pip3.exe') 

subprocess.call([pip, "install", "-r", os.path.join(src_path, "requirements.txt")])

