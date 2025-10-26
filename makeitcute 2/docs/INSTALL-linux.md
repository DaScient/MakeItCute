# Linux Setup

1) Ensure Python 3.10+ and Git:
```bash
# Debian/Ubuntu
sudo apt update && sudo apt install -y python3 python3-venv python3-pip git
# Fedora
sudo dnf install -y python3 python3-pip git
```

2) Clone and bootstrap:
```bash
git clone https://github.com/dascient/makeitcute
cd makeitcute
./PythonForBaddies/Linux/venv_init.sh
source .venv/bin/activate
python PythonForBaddies/MacOS/neon_dash.py
```
