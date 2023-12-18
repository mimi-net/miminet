# Miminet
Эмулятор компьютерной сети для образовательных целей на базе ОС Linux.

![diagram drawio](https://github.com/mimi-net/miminet/assets/89993880/9f6ddcc2-afeb-43bd-9abf-fc34cb102e8b)<?xml version="1.0" encoding="UTF-8"?>


## Local Deployment
В директориях back и front находятся .env examples, которые используются в docker-compose и ansible. 

Если Вы используете Docker для backend и frontend, не меняйте имена хостов для url в .env.

Если Вы используете virtualbox/vmware с Vagrant для backend, и разворачиваете Redis и Rabbitmq на хосте, укажите ip хоста в back/.env. (в virtual box по умолчанию 192.168.56.1)

## Backend

### Docker
```
cd back
COMPOSE_PROFILES=celery,rabbitmq,redis docker compose up -d --build
```
Celery, Rabbitmq и Redis будут доступны после этого шага. В завимости от того, где разворачивается Rabbitmq и Redis, вам потребуется указать имена сервисов.

Например, если у Вас уже развернуты Rabbitmq и Redis на другом сервере и нужен только ipmininet worker:
```
cd back
COMPOSE_PROFILES=celery docker compose up -d --build
```

### Vagrant
NFS(для полной автоматизации vagrant up):
```
# /etc/sudoers.d/vagrant-syncedfolders
Cmnd_Alias VAGRANT_EXPORTS_CHOWN = /bin/chown 0\:0 /tmp/vagrant-exports
Cmnd_Alias VAGRANT_EXPORTS_MV = /bin/mv -f /tmp/vagrant-exports /etc/exports
Cmnd_Alias VAGRANT_NFSD_CHECK = /etc/init.d/nfs-kernel-server status
Cmnd_Alias VAGRANT_NFSD_START = /etc/init.d/nfs-kernel-server start
Cmnd_Alias VAGRANT_NFSD_APPLY = /usr/sbin/exportfs -ar
%sudo ALL=(root) NOPASSWD: VAGRANT_EXPORTS_CHOWN, VAGRANT_EXPORTS_MV, VAGRANT_NFSD_CHECK, VAGRANT_NFSD_START, VAGRANT_NFSD_APPLY
```

```
cd back
export numberOfBoxes=N
export provider=vbox/vmware
. vagrant_vms.sh
```
N - количество экземпляров vagrant(Miminet на данный момент не поддерживает мультипроцессинг, выходом является запуск нескольких вм).

## Frontend

### Docker
Поднимаем после Rabbitmq и Redis.
```
cd front && docker compose up -d --build
```
