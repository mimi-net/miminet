#!/bin/sh
#Starting all containers

cd back || exit
docker compose down
cd ..
cd front || exit
docker compose down
cd ..
docker ps -a