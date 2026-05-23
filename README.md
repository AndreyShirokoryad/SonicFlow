# PlaylistAnalyze

Веб-сервис для продолжения пользовательского плейлиста. Проект использует Spotify Million Playlist Dataset и Item2Vec: реальные плейлисты выступают обучающим сигналом co-occurrence, а каждый трек представлен embedding-вектором.

## Возможности

- поиск треков по названию и артисту;
- сборка и редактирование seed-плейлиста;
- импорт TXT/CSV с пометками `найдено в MPD`, `нет в MPD`, `неуверенное совпадение`;
- top-N рекомендации;
- режимы `Balance`, `More recent`, `Favorite`, `More popular`;
- score-компоненты: recent similarity, whole playlist similarity, multi-seed support, popularity prior, favorite artist affinity;
- FAISS-индекс для ускорения подбора candidate pool в рекомендациях;
- быстрый token index для поиска по словарю модели;
- отдельная индексируемая страница `/documentation`;
- Docker Compose deployment с Caddy и HTTPS.

## Что хранится в репозитории

В git хранится код, frontend, backend, deployment-файлы, документация и маленькая smoke-модель для проверки API.

В git намеренно не хранятся:

- `.venv`;
- `.env`;
- сырые MPD-датасеты;
- большая production-модель;
- логи, сертификаты, pid-файлы;
- IDE/cache файлы.

Полная модель весит слишком много для обычного GitHub-репозитория. Ее нужно положить локально отдельно.

## Требования

Для локального запуска без Docker:

- Python 3.8+;
- `pip`;
- модель Item2Vec, если нужен полноценный поиск и рекомендации.

Для Docker-запуска:

- Docker;
- Docker Compose.

## Быстрый запуск только для проверки API

В репозитории есть маленькая smoke-модель. Она нужна только для проверки, что API стартует и endpoints работают.

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
MODEL_DIR=data/models/item2vec_mpd_gensim_smoke .venv/bin/python scripts/smoke_api.py
```

Если smoke прошел, базовая установка корректна.

## Локальный запуск с полной моделью

1. Клонировать репозиторий:

```bash
git clone https://github.com/your-username/PlaylistAnalyze.git
cd PlaylistAnalyze
```

2. Создать окружение и поставить зависимости:

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
```

3. Положить экспортированную модель в:

```text
data/models/item2vec_mpd_gensim/
```

Минимально нужны файлы:

```text
item_vectors_normalized.npy
vocab.jsonl
model_meta.json
```

4. Запустить backend и frontend:

```bash
.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

5. Открыть сайт:

```text
http://127.0.0.1:8000/
```

Полезные страницы:

```text
http://127.0.0.1:8000/documentation
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/health
http://127.0.0.1:8000/model
```

## Запуск без полной модели

Если полной модели нет, можно запустить приложение в degraded mode:

```bash
.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Сайт откроется, но `/health` покажет, что модель не загружена, а поиск и рекомендации не будут полноценно работать.

Для проверки API используйте smoke-модель:

```bash
MODEL_DIR=data/models/item2vec_mpd_gensim_smoke .venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

## Docker

1. Создать `.env`:

```bash
cp .env.example .env
```

2. Если есть полная модель, указать путь к ней в `.env`:

```env
HOST_MODEL_DIR=./data/models/item2vec_mpd_gensim
MODEL_DIR=/models/item2vec_mpd_gensim
```

3. Запустить:

```bash
docker compose up --build
```

После запуска:

```text
http://localhost/
```

Подробная инструкция по production deployment: [DEPLOYMENT.md](DEPLOYMENT.md).

## Основные API endpoints

```text
GET  /health
GET  /model
GET  /tracks/search?q=...&limit=...&offset=...
POST /tracks/batch
POST /recommend/match
POST /recommend/playlist
POST /recommend/uris
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## Настройки окружения

Основные переменные:

```env
MODEL_DIR=data/models/item2vec_mpd_gensim
PUBLIC_BASE_URL=http://localhost
GITHUB_URL=https://github.com/your-username/PlaylistAnalyze
CORS_ORIGINS=*
ENABLE_FAISS=1
REQUIRE_MODEL_ON_STARTUP=0
```

Если FAISS не ставится или на сервере мало памяти, можно временно отключить его:

```env
ENABLE_FAISS=0
```

Рекомендации продолжат работать через numpy fallback.

## Структура проекта

```text
backend/                 FastAPI backend
frontend/static/          HTML/CSS/JS frontend
src/                      обучение/экспорт/CLI-утилиты Item2Vec
scripts/                  smoke-check и вспомогательные скрипты
data/models/...           локальные модели, большая модель игнорируется git
Dockerfile
docker-compose.yml
Caddyfile
DEPLOYMENT.md
PROJECT_DETAILED_REPORT.md
```

## Публикация на GitHub

Перед публикацией проверьте:

```bash
git status --short
```

В репозиторий не должны попасть:

- `.env`;
- `.venv`;
- `data/models/item2vec_mpd_gensim`;
- сырые MPD-файлы;
- сертификаты;
- пароли и ключи.

После создания репозитория на GitHub:

```bash
git init
git add .
git commit -m "Initial PlaylistAnalyze project"
git branch -M main
git remote add origin https://github.com/your-username/PlaylistAnalyze.git
git push -u origin main
```

Затем поменяйте `GITHUB_URL` в `.env`/deployment-настройках на настоящий URL репозитория.
