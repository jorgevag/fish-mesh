#!/bin/bash
cd pyinstaller
pyinstaller ../fish_mesh.py --onefile --name fish-mesh.exe --hidden-import='PIL._tkinter_finder'
mv dist/fish-mesh.exe ..
cd ..
chmod +x fish-mesh.exe
