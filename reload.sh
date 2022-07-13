#!/bin/bash

docker compose stop
docker compose up -d
docker compose logs --tail 100 --follow
