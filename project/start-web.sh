#!/bin/bash

if [ ! -f .web-installed ]
then
    poetry install
    touch .web-installed
fi
poetry run uvicorn main:app --host 0.0.0.0 --reload
tail -f /var/log/lastlog