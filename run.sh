#!/usr/bin/env bash

#BASEDIR=$(dirname "$0")
BASEDIR=/opt/lada_online_bot
echo "Executing App in '$BASEDIR'"

source $BASEDIR/venv/bin/activate

python $BASEDIR/main.py 
