#!/bin/sh
cd $(cd -P -- "$(dirname -- "$0")" && pwd -P)
sudo pip install .
