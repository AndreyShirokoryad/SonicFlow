# PlaylistAnalyze deployment

## Что запускается

Docker Compose поднимает два сервиса:

- `app` - FastAPI backend, API и статический frontend.
- `caddy` - публичный reverse proxy. На сервере с доменом Caddy автоматически выпускает HTTPS-сертификат.

Сырые MPD JSON-файлы не копируются в Docker image. Для inference нужен только экспорт модели:

```text
item_vectors_normalized.npy
vocab.jsonl
model_meta.json
```

## Локальный запуск через Docker

```bash
cp .env.example .env
docker compose up --build
```

После запуска:

- приложение: `http://localhost/`
- документация проекта: `http://localhost/documentation`
- Swagger API: `http://localhost/docs`
- healthcheck: `http://localhost/health`

## Запуск на сервере с HTTPS

1. Скопировать проект на сервер.
2. Положить модель в директорию, указанную в `HOST_MODEL_DIR`.
3. Настроить DNS A/AAAA-запись домена на IP сервера.
4. Создать `.env`:

```env
SITE_ADDRESS=playlist.example.com
PUBLIC_BASE_URL=https://playlist.example.com
GITHUB_URL=https://github.com/your-username/PlaylistAnalyze
HOST_MODEL_DIR=/srv/playlist-analyze/models/item2vec_mpd_gensim
MODEL_DIR=/models/item2vec_mpd_gensim
CORS_ORIGINS=https://playlist.example.com
ENABLE_FAISS=1
REQUIRE_MODEL_ON_STARTUP=1
```

5. Запустить:

```bash
docker compose up --build -d
```

Caddy откроет порты `80` и `443`, получит сертификат Let's Encrypt и будет проксировать трафик в FastAPI.

## Индексация поисковиками

Приложение отдает:

- `GET /robots.txt`
- `GET /sitemap.xml`
- индексируемую страницу `/documentation`

Для корректных абсолютных URL в sitemap нужно задать `PUBLIC_BASE_URL`.

## Проверка после деплоя

```bash
curl https://playlist.example.com/health
curl https://playlist.example.com/sitemap.xml
curl https://playlist.example.com/documentation
```

В `/health` поле `model_loaded` должно быть `true`. В `/model` можно проверить
`faiss_index_loaded`; если на сервере не хватает памяти, временно поставьте `ENABLE_FAISS=0`.
