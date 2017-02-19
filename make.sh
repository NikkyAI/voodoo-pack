#!/usr/bin/env bash
cd $(cd -P -- "$(dirname -- "$0")" && pwd -P)
python3 -m pip install pyinstaller
rm -r dist/cfpecker
pyinstaller -Fcy bin/cfpecker.py -p bin
