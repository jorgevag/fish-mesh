Setup Windows 10 (WIP; Not fully tested)
----------------------
Allow Windows to run scripts from powershell
([ref](https://lazyadmin.nl/powershell/run-a-powershell-script/#:~:text=This%20error%20is%20caused%20by%20the%20PowerShell%20Execution,options%3A%20Requires%20a%20digital%20signature%20for%20downloaded%20scripts.))
* Start Windows PowerShell (admin) and run
* Run:
  ```
  Set-ExecutionPolicy RemoteSigned
  ```
You should now be able to run scripts from PowerShell
(required for activating venv and running python scripts).


Download python version from https://www.python.org/downloads/ and install
or open powershell and run
```
curl https://www.python.org/ftp/python/3.10.4/python-3.10.4-amd64.exe -o python-3.10.4-amd64.exe
./python-3.10.4-amd64.exe  
```
* do NOT "ADD TO PATH" (ambiguity for multiple python version(?))
* Note the path under "Install Now":
  e.g. `C:\Users\$USERNAME\AppData\Local\Programs\Python\Python310`

install git https://git-scm.com/download/win:
```
winget install --id Git.Git -e --source winget
```

clone repository from github:
```
git clone https://github.com/jorgevag/fish-mesh.git
```

Enter project folder
```
cd fish-mesh
```

create virtual environment using path noted during installation. e.g.
```
C:\Users\$USERNAME\AppData\Local\Programs\Python\Python310\python.exe -m venv venv
```

activate virtual environment (requires powershell to be allowed to run scripts)
```
. .\venv\Scripts\activate
```

check that the correct python version is used in the virtual env
```
python --version
```

update pip and install requirements to run the program
```
python -m pip install --upgrade pip
pip install -r .\requirements.txt
```

Finally, run the program using:
```
python fish_mesh.py
```
