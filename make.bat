cd %~dp0
py -3 -m pip install pyinstaller
pyinstaller -Fcy bin/cfpecker.py -p bin