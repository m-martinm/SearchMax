# SearchMax

Simple GUI wrapper around [ripgrep-all](https://github.com/phiresky/ripgrep-all).

## Installation

1. `python -m venv env` (optional)
2. Activate the enviroment (optional)
3. `pip install -r requirements.txt`
4. `python src/main.py`

**Alternative**

You need to have a C compiler to compile the python program to an executable.


1. python -m venv env (optional)
2. Activate the enviroment (optional)
3. `pip install -r requirements.txt`
4. `pip install nuitka` [nuitka](https://nuitka.net/)
5. `python -m nuitka --onefile --standalone --enable-plugin=pyside6 --output-dir=build --output-filename=SearchMax .\src\main.py`

## Known issues

If you try compiling it without a console window so passing `--disable-console` to nuitka, it doesn't work, or if you try running it with pythonw same issue. Don't know why, probably stdout isn't piped properly from rga.
