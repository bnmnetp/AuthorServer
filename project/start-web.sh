#!/bin/bash

poetry run uvicorn main:app --host 0.0.0.0 --reload
tail -f /var/log/lastlog