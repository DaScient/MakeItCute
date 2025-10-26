# macOS Setup

1) Install Command Line Tools:
```bash
xcode-select --install
```

2) Install Homebrew:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

3) Core tools (Python 3, Git):
```bash
brew install python git
```

4) (Optional) Fancy terminal:
- iTerm2 with a pure black, slightly opaque profile.
- Color preset: background #000000 @ 90–95% opacity; foreground #ffd1f2; cursor #ff69b4.

5) Create and activate the venv:
```bash
./PythonForBaddies/MacOS/venv_init.sh
source .venv/bin/activate
```

6) Launch the neon dashboard:
```bash
python PythonForBaddies/MacOS/neon_dash.py
```
