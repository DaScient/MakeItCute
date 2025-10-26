# Windows Setup (PowerShell)

1) Install Python (3.10+) from python.org and ensure "Add to PATH" is checked.
2) Install Git for Windows.

3) Clone and bootstrap:
```powershell
git clone https://github.com/dascient/makeitcute
cd makeitcute
PowerShell -ExecutionPolicy Bypass -File .\PythonForBaddies\Windows\venv_init.ps1
python .\PythonForBaddies\MacOS\neon_dash.py
```
