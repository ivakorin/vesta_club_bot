#!/usr/bin/env bash

BASEDIR=$(dirname "$0")
#BASEDIR=$(pwd)
echo "Executing App in '$BASEDIR'"

source $BASEDIR/venv/bin/activate

python $BASEDIR/main.py 
