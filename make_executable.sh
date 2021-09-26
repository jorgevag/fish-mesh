#!/bin/bash
cd pyinstaller
pyinstaller ../fish_mesh.py --onefile --name FishMesh.exe --hidden-import='PIL._tkinter_finder'
mv dist/FishMesh.exe ..
cd ..
