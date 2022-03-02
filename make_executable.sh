#!/bin/bash
cd pyinstaller
pyinstaller ../fish_mesh.py \
  --name fish-mesh.exe \
  --onefile \
  --hidden-import='PIL._tkinter_finder' \
  --windowed # avoid console on windows systems
mv dist/fish-mesh.exe ..
cd ..
chmod +x fish-mesh.exe
