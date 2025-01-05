#!/bin/sh
#Starting all containers

cd back || exit
docker compose up -d --build
cd ..
cd front || exit
docker compose up -d --build
cd ..
docker ps -a