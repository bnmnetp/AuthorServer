#!/bin/bash

set +e
poetry run celery -A worker.celery worker
if [ $? -ne 0 ]; then
    poetry install
    poetry run celery -A worker.celery worker
fi
tail -f /var/log/lastlog