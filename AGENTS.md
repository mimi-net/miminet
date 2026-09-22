# Miminet

Miminet - веб-эмулятор компьютерных сетей на базе ОС Linux, предназначенный для образовательных целей.

## Документация

- `docs/GIT.md` - работа с git, правила именования веток и коммитов
- `docs/DEVELOPMENT.md` - запуск локальных тестов без Docker

## Определение ключевых слов

- **MUST**/**ДОЛЖЕН** - this word, or the terms **REQUIRED**/**ОБЯЗАТЕЛЬНО** or **SHALL**/**ДОЛЖНО**, mean that the
  definition is an absolute requirement of the specification.

- **MUST NOT**/**НЕ ДОЛЖЕН** - this phrase, or the phrase **SHALL NOT**/**НЕ ДОЛЖНО**, mean that the
  definition is an absolute prohibition of the specification.

- **SHOULD**/**СЛЕДУЕТ** - this word, or the adjective **RECOMMENDED**/**РЕКОМЕНДУЕТСЯ**, mean that there
  may exist valid reasons in particular circumstances to ignore a
  particular item, but the full implications must be understood and
  carefully weighed before choosing a different course.

- **SHOULD NOT**/**НЕ СЛЕДУЕТ** - this phrase, or the phrase **NOT RECOMMENDED**/**НЕ РЕКОМЕНДУЕТСЯ** mean that
  there may exist valid reasons in particular circumstances when the
  particular behavior is acceptable or even useful, but the full
  implications should be understood and the case carefully weighed
  before implementing any behavior described with this label.

- **MAY**/**МОЖЕТ** - this word, or the adjective **OPTIONAL**/**ОПЦИОНАЛЬНО**, mean that an item is
  truly optional.

## Стек технологий

- Bootstrap - для верстки HTML страниц
- Cytoscape (JS library) - для рисования топологии сети в браузере (canvas)
- Python Flask - фронтэнда (обработка запросов пользователя - регистрация, вход, создание новых сетей, просмотр существующих сетей и т.д.) 
- SQLAlchemy - ORM для работы с базами данных
- RabbitMQ - очередь сообщений для обмена с эмулятором сетей Mininet
- PostgreSQL - хранение данных пользователей
- Mininet - OpenSource эмулятор компьютерных сетей под ОС Linux


