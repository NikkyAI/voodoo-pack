cd %~dp0
python3 -m pip install pyinstaller
@RD /S "dist\cfpecker" #TODO test on a windoofs machine
pyinstaller -Fcy bin/cfpecker.py -p bin