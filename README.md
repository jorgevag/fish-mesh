![](fish-mesh.png)

fish-mesh
=========
Measure fish (or other things) from a photo using a reference box with known dimensions.

Dependencies
------------
* python >= 3.8

standard python library packages:
* [tkinter](https://docs.python.org/3/library/tk.html)

External packages:
* [numpy](https://numpy.org/)
* [OpenCV](https://docs.opencv.org/4.5.3/)
* [Pillow](https://python-pillow.org/)
* [pyinstaller](https://github.com/pyinstaller/pyinstaller)
* [exif](https://gitlab.com/TNThieding/exif)
* [pandas](https://pandas.pydata.org/docs/)
  and [openpyxl](https://openpyxl.readthedocs.io/en/stable/) (write excel files)

Setup Ubuntu
------------
Go to folder where you want to the project and run (requires `git`: `sudo apt install git`)
```
git clone https://github.com/jorgevag/fish-mesh
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

Possible setup MacOS using pyenv (not tested; WIP)
---------------------------------------------------
#### 1) install pyenv
install tools required for pyenv:
```
xcode-select --install  # XCode command line tool
brew install openssl readline sqlite3 xz zlib
```

Install pyenv:
```
brew update
brew install pyenv
```
After install, run the following to add `pyenv` to your
`$PATH` and start `pyenv` whenever a new terminal is opened
(replace  `~/.zshrc`  if you're using another shell):
```
echo 'eval "$(pyenv init --path)"' >> ~/.zshrc
```
#### 2) install python
check available python versions
```
pyenv install -l
```

Install the required python version
```
pyenv install 3.8.10
```
Check the installed version by running:
```
pyenv versions
```

#### 3) settings python version in pyenv
1. Option: *global version*
   
     Set python version 3.8.10 to be used by pyenv globally
     ```
     pyenv global 3.8.10  # used for any new terminal
     ```
2. Option: *local version*
   
   Navigate to project folder and run:
   ```
   pyenv local 3.8.10  # used for this project only
   ```
   (This creates a .python-version file in the project)
#### 4) Create virtual environment and activate it
```
virtualenv --python=/usr/bin/python3.8 venv
# might be 
# virtualenv -python=python3.8 venv
# or 
# virtualenv -python=/usr/local/bin/python3.8 venv
source venv/bin/activate
```
#### 5) install python packages
```
pip install -r requirements.txt
```
#### 6) run the application
```
python fish-mesh.py
```
