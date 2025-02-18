# SearchMax

Simple GUI wrapper around [ripgrep-all](https://github.com/phiresky/ripgrep-all).

## Installation

1. `python -m venv env` (optional)
2. Activate the enviroment (optional)
3. `pip install -r requirements.txt`
4. `python src/main.py`

**Alternative**

You need to have a C compiler to compile the python program to an executable.

1. `python -m venv env` (optional)
2. Activate the enviroment (optional)
3. `pip install -r requirements.txt`
4. `pip install nuitka imageio` ([nuitka](https://nuitka.net/))
5. `python -m nuitka \src\main.py` from the root folder.

## Known issues

If you get too many Access denied erros the program may crash.
Exclude option is not really working.

## TODO

1. Add a batch script for windows which adds the program to folder context menus.
2. Fix the current directory label, it looks like ...
3. Somehow make a smooth horizontal scroll, if enabled it feels laggy
4. Add some more options and a settings window, move adapters to settings (more in src/main.py).
5. Maybe split up the script it starts to be too long.
