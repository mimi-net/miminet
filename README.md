# Miminet
Эмулятор компьютерной сети для образовательных целей на базе ОС Linux.

## Local Deployment
В директориях back и front находятся .env examples, которые используются в docker-compose и ansible. 

Если Вы используете Docker для backend и frontend, не меняйте имена хостов для url в .env.

Если Вы используете virtualbox/vmware с Vagrant для backend, и разворачиваете Redis и Rabbitmq на хосте, укажите ip хоста в back/.env. (в virtual box по умолчанию 192.168.56.1)

## Backend

### Docker
```
cd back
COMPOSE_PROFILES=celery,rabbitmq docker compose up -d --build
```
Celery, Rabbitmq будут доступны после этого шага. В завимости от того, где разворачивается Rabbitmq, вам потребуется указать имена сервисов.

Например, если у Вас уже развернут Rabbitmq на другом сервере и нужен только ipmininet worker:
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
Поднимаем после Rabbitmq.
```
cd front && docker compose up -d --build
```

## Authorization
Для возможности авторизации необходимо создать свое Google/Vk приложение и поместить client_google.json/vk_auth.json в front/src. Можно обратиться к разработчикам для получения общих credentials, но это не является безопасным решением.

## Database migrations
```
docker exec -it miminet bash
flask db init
flask db migrate
flask db upgrade
```
