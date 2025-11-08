#!/bin/sh
# Downing all containers

cd back || exit
sudo docker compose down
cd ..
cd front || exit
sudo docker compose down
cd ..
docker ps -a