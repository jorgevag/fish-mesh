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

Setup MacOS (using pyenv)
---------------------------------------------------
#### 1) required tools
The following steps require some additional tools (e.g. git),
so we need to install *XCode command line tool (CTL)*:
```
xcode-select --install
```

We also need [Homebrew](https://brew.sh/) to install additional packages like python and pyenv:
```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```


#### 2) install pyenv and python
We'll be using pyenv to handle specific python versions, and to avoid messing
the operating system's python
```
brew update
brew install pyenv
```

After install, run the following to add `pyenv` to your
`$PATH` and start `pyenv` whenever a new terminal is opened
```
echo 'eval "$(pyenv init --path)"' >> ~/.bashrc
```
(or `~/.zshrc`  depending on the shell you're using):

Install the required python version
(Check available python versions using `pyenv install -l`):
```
pyenv install 3.8.10
```
(You can check the installed version by running: `pyenv versions`)

#### 3) settings python version in pyenv
Go to folder where you want to the project and run
```
git clone https://github.com/jorgevag/fish-mesh
cd fish-mesh
```

#### 4) set correct python version (using pyenv)
(choose (1) or (2))
1. *global version*
   
   Set python version 3.8.10 to be used by pyenv globally
   ```
   pyenv global 3.8.10  # used for any new terminal
   ```
2. *local version*
   
   In the `fish-mesh/` project folder,  run:
   ```
   pyenv local 3.8.10
   ```
   This creates a .python-version file in the project,
   used in this project only
   
#### 4) Create virtual environment and activate it
If you don't have `virtualenv` installed, then install it with
```
pip3 install virtualenv
```
In the `fish-mesh/` project folder, create the virtual environment
by running
```
virtualenv --python=python3.8 venv
```
This will create the virtual environment in the project folder.
Activate it using 
```
source venv/bin/activate
```

#### 5) install python packages
```
source venv/bin/activate
pip install -r requirements.txt
```

#### 6) run the application
```
source venv/bin/activate
python fish-mesh.py
```

#### 7) create executable (WIP; not working)
```
mkdir pyinstaller
bash ./make_executable.sh
```

**If above fails**:
try reinstall pyenv using (
[ref](https://stackoverflow.com/questions/58548730/how-to-use-pyinstaller-with-pipenv-pyenv)
)
```
pyenv uninstall 3.8.10
env PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 3.8.10
eval "$(pyenv init -)"
```
if it still fails, then also try to downgrade pyinstaller (
[ref](https://stackoverflow.com/questions/68884906/pyinstaller-error-systemerror-codesign-failure-on-macos)
)
(Was able to generate executable, but it still isn't signed (TODO))