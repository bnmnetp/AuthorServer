#!/bin/bash

poetry run celery -A worker.celery worker
tail -f /var/log/lastlog