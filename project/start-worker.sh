#!/bin/bash

if [ ! -f .worker-installed ]
then
    poetry install
    touch .worker-installed
fi
poetry run celery -A worker.celery worker
tail -f /var/log/lastlog