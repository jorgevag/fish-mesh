Setup Ubuntu
------------
Go to folder where you want to the project and run (requires `git`: `sudo apt install git`)
```
git clone https://github.com/jorgevag/fish-mesh
cd fish-mesh
```

If you don't have the correct python version, it can be installed with
```
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.8
```

Create virtual environment and activate it
```
virtualenv --python=/usr/bin/python3.8 venv
source venv/bin/activate
```
install packages
```
pip install -r requirements.txt
```
run application
```
python fish-mesh.py
```