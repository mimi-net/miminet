![Test Status](https://github.com/mimi-net/miminet/actions/workflows/full_test.yml/badge.svg)
![Test Status](https://github.com/mimi-net/miminet/actions/workflows/back_test.yml/badge.svg)
![OS](https://img.shields.io/badge/OS-linux-0078D4)
[![License: Apache](https://img.shields.io/badge/License-Apache-yellow.svg)](https://opensource.org/licenses/Apache)
[![GitHub last commit](https://img.shields.io/github/last-commit/mimi-net/miminet)](#)
![GitHub commit activity](https://img.shields.io/github/commit-activity/m/mimi-net/miminet)
# Miminet ![Group 3 (3)](https://github.com/user-attachments/assets/f5ea166c-03ed-43bb-9f9b-92543fa97ba2)

**Miminet** — эмулятор компьютерных сетей на базе ОС Linux, предназначенный для образовательных целей.

---

## Требования

Перед началом работы убедитесь, что у вас установлены:
- [Docker](https://www.docker.com/get-started/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [Vagrant](https://www.vagrantup.com/) (не обязательно)
- [Ansible](https://docs.ansible.com/ansible/latest/installation_guide/index.html) (не обязательно)
---

## 🛠️ Локальное развёртывание

В каталогах `back` и `front` находятся примеры файлов `.env`, используемых в docker-compose и Ansible.

### Важно:
- Развёртка бэкенда на ***WSL*** — плохая идея, используйте нормальный линукс.
- Фронтенд можно разворачивать где угодно, в случае, если эмуляция не обязательна для разработки.
- Для удобного запуска всех контейнеров можно воспользоваться скриптом [start_all_containers.sh](./start_all_containers.sh).

### Гайд:
1. ```git clone git@github.com:mimi-net/miminet.git```
2. Копируем ```vk_auth.json``` из группового чата в ```front/src```, чтобы можно было авторизоваться на сайте.
3. Создаём файл ```miminet_secret.conf``` в ```front/src``` и пишем туда случайные буквы/цифры, чтобы не авторизовываться после каждого перезапуска докера.
4. Запускаем приложение (например, через [start_all_containers.sh](./start_all_containers.sh)).
5. Заходим на localhost и проверяем, что всё работает.

### Vagrant (не обязательно)
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

## ☑️ Тестирование
1. В ```front/.env``` файле должно быть выставлено: ```MODE=dev```.
2. Запуск тестов:
```
sh front/tests/docker/run.sh
pytest front/tests
```


