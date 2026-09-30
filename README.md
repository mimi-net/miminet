<p align="center">
    <a href="https://github.com/mimi-net/miminet/actions" alt="Miminet Github Actions">
    <img src="https://github.com/mimi-net/miminet/actions/workflows/full_test.yml/badge.svg" /></a>
    <a href="https://github.com/mimi-net/miminet/actions" alt="Miminet Github Actions">
    <img src="https://github.com/mimi-net/miminet/actions/workflows/back_test.yml/badge.svg" /></a>
    <a href="https://en.wikipedia.org/wiki/Linux" alt="OS Linux">
    <img src="https://img.shields.io/badge/OS-linux-0078D4" /></a>
    <a href="https://opensource.org/licenses/Apache" alt="License">
    <img src="https://img.shields.io/badge/License-Apache-yellow.svg" /></a>
    <a href="https://github.com/mimi-net/miminet/commits/main/" alt="Last Commit">
    <img src="https://img.shields.io/github/last-commit/mimi-net/miminet" /></a>
    <a href="https://github.com/mimi-net/miminet/commits/main/" alt="GitHub commit activity">
    <img src="https://img.shields.io/github/commit-activity/m/mimi-net/miminet" /></a>
    <a href="https://miminet.ru/" alt="Site">
    <img src="https://img.shields.io/website?url=https%3A%2F%2Fmiminet.ru%2F" /></a>
</p>

# Miminet

**Miminet** — эмулятор компьютерных сетей на базе ОС Linux, предназначенный для образовательных целей.

---

## 📖 Содержание

- [Требования](#requirements)
- [Локальное развёртывание](#deployment)
  - [Установка](#installation)
  - [Database migrations](#migration)
  - [Vagrant (не обязательно)](#vagrant)
- [Архитектура](#arch)
  - [Общая информация](#arch-info)
  - [Frontend](#frontend)
  - [Backend](#backend)
- [Тестирование](#testing)
  - [Frontend](#frontend-test)
  - [Backend](#backend-test)

---


## 💡 <a name="requirements"></a>Требования

Перед началом работы убедитесь, что у вас установлены:
- [Docker](https://www.docker.com/get-started/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [Vagrant](https://www.vagrantup.com/) (не обязательно)
- [Ansible](https://docs.ansible.com/ansible/latest/installation_guide/index.html) (не обязательно)

> Если только начинаете знакомство с проектом, не забудьте прочитать [раздел](#arch) посвященный архитектуре приложения.
---

## 🛠️ <a name="deployment"></a>Локальное развёртывание

В каталогах `back` и `front` находятся примеры файлов `.env`, используемых в docker-compose и Ansible.

### Важно: 
- Не используйте ***WSL*** для развёртки бэкенда, оно не заработает.
- Фронтенд можно разворачивать где угодно, в случае, если эмуляция не обязательна для разработки.
- Для удобного запуска всех контейнеров можно воспользоваться скриптом [start_all_containers.sh](./start_all_containers.sh).

### <a name="installation"></a>Установка:
1. ```git clone git@github.com:mimi-net/miminet.git```
2. Копируем ```vk_auth.json``` из группового чата в ```front/src```, чтобы можно было авторизоваться на сайте.
3. Создаём файл ```miminet_secret.conf``` в ```front/src``` и пишем туда случайные буквы/цифры, чтобы не авторизовываться после каждого перезапуска докера.
4. В файле .env (папка ```front```) поменять MODE=prod на MODE=dev.
5. Запускаем приложение (например, через [start_all_containers.sh](./start_all_containers.sh)).
6. Заходим на localhost и проверяем, что всё работает.

## <a name="migration"></a>Database migrations
> Следующие действия необходимо выполнять в случае, если вы обновили модель базы данных ([SQLAlchemy](https://www.sqlalchemy.org/)) и теперь хотите, чтобы изменения появились в реальной базе данных.
```
docker exec -it miminet bash
flask db init
flask db migrate
flask db upgrade
```

### <a name="vagrant"></a>Vagrant (не обязательно)
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
---

## ☁️ <a name="arch">Архитектура</a>

### <a name="arch-info"></a>Общая информация
- Miminet использует контейнеризацию для управления своими компонентами.
- RabbitMQ: Система обмена сообщениями, обеспечивающая взаимодействие между фронтендом и бэкендом.

### <a name="frontend"></a> Frontend (фронтенд, front)
- Клиентская часть, предоставляющая веб-интерфейс для взаимодействия пользователей с системой (авторизация, настройка сетей и так далее).
- Файлы, относящиеся к этой части приложения, находятся в каталоге ```front```.
- За эту часть приложения ответственны три контейнера: miminet (основной веб-сервис), [nginx](https://nginx.org/ru/) (HTTP-сервер для балансировки нагрузки) и rabbitmq.
- В Miminet есть [тесты](https://github.com/mimi-net/miminet/tree/main/front/tests) на фронтенд, позволяющие имитировать действия реального пользователя при конфигурации сетей. Реализовано это с помощью [Selenium](https://www.selenium.dev/).

### <a name="backend"></a> Backend (бэкенд, back) 

- Серверная часть приложения, реализующая логику эмуляции сети.
- Файлы, относящиеся к этой части приложения, находятся в каталоге ```back```.
- За эту часть приложения ответственнен контейнер celery, принимающий задачи от фронтенда и обрабатывающий их.
- В Miminet есть [тесты](https://github.com/mimi-net/miminet/blob/main/back/tests) для бэкенда, проверяющие качество эмуляции заданной сети. Конфигурация тестов происходит через [JSON-файлы](https://github.com/mimi-net/miminet/tree/main/back/tests/test_json).
  
---

## ☑️ <a name="testing"></a> Тестирование

### <a name="frontend-test"></a> Frontend
Тестирование фронтенда работает путем имитации действий пользователя (кликов, ввода текста, навигации) с помощью автоматизированного управления браузером. Браузер(ы) находятся в специальном докер-контейнере(ах), ими управляет другой докер-контейнер (*selenium-hub*).

#### Основное:
- Всё, что связано с тестированием фронтенда, находится в каталоге ```front/tests```.
- Каталог ```docker``` хранит файлы, необходимые для запуска докер-контейнеров, которые позволяют имитировать действия пользователя на сайте.
- В каталоге ```utils``` находятся файлы, необходимые для написания тестов:
    - *checkers.py* — содержит класс, сравнивающий построенную сеть с образцом по заданным параметрам.
    - *locators.py* — содержит специальную структуру, в которой находятся все используемые в тесах имена веб-элементов Miminet. Если хотите добавить тест на новую функцию, не забудьте обновить этот файл.
    - *networks.py* — содержит классы, позволяющие быстро конфигурировать сети Miminet. С примерами использования этих классов можно ознакомиться в основном каталоге ```front/tests```.
- Самый важный файл во всей тестирующей системе — ```conftest.py```, в нём определены ключевые [фикстуры](https://docs.pytest.org/en/stable/explanation/fixtures.html), позволяющие писать тесты. Также функции из этого файла позволяют писать тесты быстрее и безопаснее.

#### Запуск:
1. В ```front/.env``` файле должно быть выставлено: ```MODE=dev```.
2. Запуск контейнеров: ```sh front/tests/docker/run.sh```
3. Запуск тестов: ```pytest front/tests```.

Запуск без Docker (rootless podman): [DEVELOPMENT.md](DEVELOPMENT.md).

#### Набор на Playwright

В ```front/tests/playwright``` лежит тот же набор E2E-тестов, переписанный на [Playwright](https://playwright.dev/python/). Он работает параллельно с основным: Selenium-тесты остаются на месте, оба набора проверяют одно и то же.

Отличия: браузер запускается как обычный процесс, поэтому ```selenium-hub``` и контейнер с Chrome не нужны, а весь набор проходит примерно за минуту вместо пяти.

Первоначальная установка (один раз):
```bash
uv sync                              # поставит pytest-playwright
uv run playwright install chromium   # ~658 МБ на диске
```

Запуск — из корня репозитория:
```bash
sh front/tests/playwright/run.sh                 # весь набор в 4 процесса
sh front/tests/playwright/run.sh test_vlan.py    # один файл
sh front/tests/playwright/run.sh . --headed      # с видимым браузером
```

Скрипт сам подставляет адрес и число воркеров; переопределяются переменными ```TEST_TARGET_HOST``` и ```WORKERS```. То же самое вручную:
```bash
cd front/tests/playwright
TEST_TARGET_HOST=127.0.0.1 uv run pytest . -n 4
```

- ```-n 4``` — тесты в четыре параллельных процесса. Больше брать не стоит: на восьми воркерах тесты начинают падать из-за конкуренции за одну учётную запись.
- ```TEST_TARGET_HOST=127.0.0.1``` нужен при запуске с хоста: адрес по умолчанию (```172.18.0.2```) — это nginx внутри docker-сети, снаружи он отдаёт 502.
- ```--headed``` показывает браузер, ```--slowmo 500``` замедляет действия — удобно при отладке падающего теста.

Подробности — в [docs/FUNCTIONAL_TESTS.md](docs/FUNCTIONAL_TESTS.md): что покрывает каждый тест, чем порт отличается от оригинала и с какими особенностями пришлось столкнуться.

### <a name="backend-test"></a> Backend
1. Установка необходимых пакетов (требуется [uv](https://docs.astral.sh/uv/)):
```bash
uv sync --project back
source .venv/bin/activate
```
2. Запуск тестов:
```bash
sudo bash
source .venv/bin/activate
cd back/tests
export PYTHONPATH=$PYTHONPATH:../src
pytest .
```
> Для mininet обязательно нужен root!

Что покрывают тесты бэкенда, какие из них требуют root, а какие запускаются за секунду без Mininet — в [docs/BACKEND_TESTS.md](docs/BACKEND_TESTS.md).

