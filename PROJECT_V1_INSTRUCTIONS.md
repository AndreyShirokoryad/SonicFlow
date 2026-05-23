# PlaylistAnalyze: инструкция для завершения первой версии

Документ фиксирует актуальное состояние проекта после перехода на Spotify Million Playlist Dataset (MPD), Item2Vec и FastAPI backend.

## 1. Цель первой версии

Первая версия проекта должна уметь:

1. Загружать обученную Item2Vec-модель.
2. Искать треки по названию и артисту.
3. Принимать плейлист пользователя как список треков.
4. Матчить треки пользователя с треками из MPD.
5. Выдавать top-N рекомендаций.
6. Показывать объяснимые компоненты score:
   - similarity к последним трекам;
   - similarity ко всему плейлисту;
   - поддержку несколькими seed-треками;
   - популярность трека в MPD.

Первая версия не обязана использовать Music4All, аудио-признаки, жанры, теги, тексты или Postgres. Сейчас основной сигнал - co-occurrence треков в реальных Spotify-плейлистах из MPD.

## 2. Основной датасет

Основной датасет для первой версии:

```text
Spotify Million Playlist Dataset (MPD)
```

Локально он лежит здесь:

```text
data/MPD/archive/data
```

В MPD:

```text
1,000,000 playlists
66,346,428 track occurrences
2,262,292 unique tracks
```

Сырые MPD-файлы нужны для обучения модели и аналитических скриптов. Для запуска backend на сервере сырые MPD JSON-файлы не нужны, если модель уже обучена и экспортирована.

## 3. Что уже сделано

### Анализ пользовательского плейлиста

Основной пользовательский плейлист:

```text
data/playlist_examples/Мне нравится.txt
```

Проверка покрытия MPD:

```text
data/processed/playlist_analysis/Мне нравится_mpd_coverage.json
data/processed/playlist_analysis/Мне нравится_mpd_coverage_summary.md
```

Результат:

```text
Всего треков: 1463
Matched в MPD: 523
Coverage: 35.8%
Confident matched: 415
Confident coverage: 28.4%
```

Неуверенные распознавания:

```text
data/processed/playlist_analysis/Мне нравится_mpd_uncertain_matches.csv
data/processed/playlist_analysis/Мне нравится_mpd_uncertain_matches.md
```

### Кириллические треки MPD

Выборка треков с кириллицей:

```text
data/processed/mpd/mpd_cyrillic_tracks.csv
data/processed/mpd/mpd_cyrillic_tracks_manifest.json
```

Результат:

```text
7,618 unique Cyrillic tracks
18,598 occurrences
```

Важно: это не строго "российские треки", а треки, где кириллица есть в названии трека, артиста или альбома.

## 4. Обучение Item2Vec

Item2Vec здесь - это Word2Vec-подход, где:

```text
плейлист = предложение
трек = слово
```

Модель учится по соседству треков внутри реальных плейлистов. Если два трека часто встречаются в похожем контексте, их векторы становятся близкими.

Основная реализация обучения:

```text
src/item2vec_train.py
```

Общие функции чтения MPD и матчинга:

```text
src/mpd_corpus.py
```

CLI-рекомендации без backend:

```text
src/item2vec_recommend.py
```

Команда обучения полной модели:

```bash
.venv/bin/python -m src.item2vec_train \
  --mpd-data-dir data/MPD/archive/data \
  --output-dir data/models/item2vec_mpd_gensim \
  --vector-size 64 \
  --window 5 \
  --negative 5 \
  --min-count 2 \
  --epochs 5 \
  --workers 8 \
  --progress-every-files 50
```

Для Apple M4 Pro нормальный стартовый вариант - `--workers 8`. Если система остается отзывчивой, можно попробовать 10-12. Если появляются странные ошибки, перегрев или сильные лаги, лучше вернуть 8.

## 5. Артефакты модели

Основная обученная модель лежит здесь:

```text
data/models/item2vec_mpd_gensim
```

Файлы:

```text
gensim_word2vec.model
gensim_word2vec.model.syn1neg.npy
gensim_word2vec.model.wv.vectors.npy
gensim_keyed_vectors.kv
gensim_keyed_vectors.kv.vectors.npy
item_vectors.npy
item_vectors_normalized.npy
vocab.jsonl
model_meta.json
```

Назначение:

```text
vocab.jsonl
```

Каталог треков. В каждой строке один трек: `track_uri`, `artist_name`, `track_name`, `album_name`, `count`, `idx`.

```text
item_vectors.npy
```

Обычные эмбеддинги треков после обучения.

```text
item_vectors_normalized.npy
```

Нормализованные эмбеддинги. Каждый вектор поделен на свою L2-норму, поэтому cosine similarity можно считать обычным dot product:

```text
similarity = vector_a @ vector_b
```

Именно этот файл использует backend для рекомендаций.

```text
model_meta.json
```

Параметры обучения и статистика модели.

```text
gensim_word2vec.model
gensim_keyed_vectors.kv
```

Файлы gensim. Нужны, если нужно дообучать модель, анализировать ее через gensim или переэкспортировать эмбеддинги.

Для backend MVP минимально нужны:

```text
data/models/item2vec_mpd_gensim/item_vectors_normalized.npy
data/models/item2vec_mpd_gensim/vocab.jsonl
data/models/item2vec_mpd_gensim/model_meta.json
```

## 6. Алгоритм рекомендаций

Для входного плейлиста:

1. Текстовые треки матчатся в Spotify `track_uri`.
2. Берутся эмбеддинги seed-треков.
3. Считается вектор всего плейлиста.
4. Считается вектор последних `recent_k` треков.
5. Из всей базы выбирается candidate pool похожих треков.
6. Кандидаты ранжируются гибридной формулой.

Текущая формула:

```text
score =
  0.45 * recent_similarity
+ 0.25 * whole_playlist_similarity
+ 0.20 * multi_seed_support
+ 0.10 * popularity_prior
```

Расшифровка:

```text
recent_similarity
```

Похожесть кандидата на последние `recent_k` треков. Это нужно, чтобы рекомендации учитывали текущий конец плейлиста.

```text
whole_playlist_similarity
```

Похожесть кандидата на средний вектор всего плейлиста. Это удерживает рекомендации в общем стиле плейлиста.

```text
multi_seed_support
```

Насколько кандидат похож сразу на несколько seed-треков, а не только на один случайный трек.

```text
popularity_prior
```

Популярность трека в MPD. Считается через `log1p(count)`, чтобы популярные треки получали небольшой плюс, но не забивали все рекомендации.

```text
count
```

Количество появлений трека в MPD-плейлистах.

Рекомендуемый фильтр для первой версии:

```text
min_count = 10
recent_k = 5
candidate_pool = 10000
top_n = 20
```

## 7. CLI-запуск рекомендаций

Проверить рекомендации без backend:

```bash
.venv/bin/python -m src.item2vec_recommend playlist \
  --model-dir data/models/item2vec_mpd_gensim \
  --playlist "data/playlist_examples/Мне нравится.txt" \
  --top-n 20 \
  --min-count 10 \
  --recent-k 5 \
  --candidate-pool 10000
```

Этот путь полезен для отладки модели и качества рекомендаций без frontend/backend.

## 8. Backend

Backend собран на FastAPI.

Структура:

```text
backend/app/main.py
backend/app/config.py
backend/app/schemas.py
backend/app/api/health.py
backend/app/api/tracks.py
backend/app/api/recommendations.py
backend/app/services/model_store.py
backend/app/services/playlist_matcher.py
backend/app/services/recommender.py
backend/app/services/item2vec_service.py
backend/requirements.txt
```

Разделение сервисов:

```text
model_store.py
```

Читает модель и данные треков: `vocab.jsonl`, `item_vectors_normalized.npy`, `model_meta.json`. Также хранит индексы для поиска.

```text
playlist_matcher.py
```

Матчит текстовые треки пользователя с `track_uri` из модели.

```text
recommender.py
```

Считает top-N рекомендации и компоненты score.

```text
item2vec_service.py
```

Тонкий фасад, который соединяет `model_store`, `playlist_matcher` и `recommender`, чтобы API было проще.

Запуск backend:

```bash
.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Если модель лежит не в стандартной папке:

```bash
MODEL_DIR=data/models/item2vec_mpd_gensim \
.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

## 9. API первой версии

### Healthcheck

```http
GET /health
```

Возвращает:

```json
{
  "status": "ok",
  "model_loaded": true,
  "model_dir": "data/models/item2vec_mpd_gensim",
  "vocab_size": 1188873
}
```

### Информация о модели

```http
GET /model
```

Возвращает параметры обучения и состояние загрузки модели.

### Поиск треков

```http
GET /tracks/search?q=nirvana%20heart&limit=10&min_count=10
```

Используется frontend-ом для добавления треков в плейлист.

### Получение трека по URI

```http
GET /tracks/{track_uri}
```

Пример:

```text
/tracks/spotify:track:11LmqTE2naFULdEP94AUBa
```

### Рекомендации по URI

```http
POST /recommend/uris
```

Payload:

```json
{
  "seed_uris": [
    "spotify:track:11LmqTE2naFULdEP94AUBa",
    "spotify:track:4xBHZ2Mr0gCdFYXrPZuYXO"
  ],
  "top_n": 20,
  "recent_k": 5,
  "min_count": 10,
  "candidate_pool": 10000,
  "recent_weight": 0.45,
  "whole_weight": 0.25,
  "multi_seed_weight": 0.2,
  "popularity_weight": 0.1
}
```

### Рекомендации по текстовому плейлисту

```http
POST /recommend/playlist
```

Payload:

```json
{
  "tracks": [
    {"artist": "Nirvana", "title": "Heart-Shaped Box"},
    {"artist": "System Of A Down", "title": "Lonely Day"}
  ],
  "top_n": 20,
  "recent_k": 5,
  "min_count": 10,
  "candidate_pool": 10000
}
```

Ответ:

```json
{
  "matched_seed_count": 2,
  "recommendations": [
    {
      "rank": 1,
      "score": 0.9061,
      "track_uri": "spotify:track:...",
      "track_name": "Come As You Are",
      "artist_name": "Nirvana",
      "album_name": "...",
      "count": 12345,
      "recent_similarity": 0.91,
      "whole_playlist_similarity": 0.89,
      "multi_seed_support": 0.86,
      "popularity_prior": 0.72
    }
  ]
}
```

## 10. Что нужно для переноса на сервер

Минимальный набор:

```text
backend/
src/mpd_corpus.py
data/models/item2vec_mpd_gensim/item_vectors_normalized.npy
data/models/item2vec_mpd_gensim/vocab.jsonl
data/models/item2vec_mpd_gensim/model_meta.json
backend/requirements.txt
```

Если нужно дообучение или переэкспорт модели на сервере, дополнительно перенести:

```text
src/item2vec_train.py
src/item2vec_recommend.py
data/models/item2vec_mpd_gensim/gensim_word2vec.model
data/models/item2vec_mpd_gensim/gensim_word2vec.model.syn1neg.npy
data/models/item2vec_mpd_gensim/gensim_word2vec.model.wv.vectors.npy
data/models/item2vec_mpd_gensim/gensim_keyed_vectors.kv
data/models/item2vec_mpd_gensim/gensim_keyed_vectors.kv.vectors.npy
```

Сырые данные MPD для production inference не нужны:

```text
data/MPD/archive/data
```

Их стоит хранить локально или в отдельном storage только для переобучения.

## 11. Ожидаемый вес на сервере

Минимальный inference-набор:

```text
item_vectors_normalized.npy  ~290 MB
vocab.jsonl                  ~343 MB
model_meta.json              <1 KB
backend + src                мало
```

Итого на диске для MVP:

```text
около 650-800 MB
```

В памяти будет больше, потому что backend загружает `vocab.jsonl` в Python-объекты и строит индексы:

```text
примерно 1.5-3+ GB RAM
```

Точное значение зависит от Python, ОС и количества индексов.

## 12. Что нужно доделать для первой версии

### Backend

1. Добавить CORS для frontend.
2. Добавить endpoint для batch-lookup треков по списку URI.
3. Добавить endpoint, который возвращает подробный результат матчинга:
   - входной artist/title;
   - найденный artist/title;
   - `track_uri`;
   - confidence/status.
4. Добавить обработку ошибок:
   - модель не найдена;
   - пустой плейлист;
   - слишком большой плейлист;
   - слишком большой `candidate_pool`.
5. Добавить простые backend-тесты:
   - загрузка модели;
   - поиск трека;
   - матчинг текстового плейлиста;
   - рекомендации по URI.

### Качество рекомендаций

1. Сделать несколько preset-режимов:
   - `balanced`;
   - `more_recent`;
   - `more_popular`;
   - `deep_cuts`.
2. Добавить фильтр дубликатов:
   - не рекомендовать другой вариант того же трека;
   - не рекомендовать karaoke/live/remaster, если в плейлисте уже есть оригинал.
3. Добавить объяснение рекомендации нормальным текстом:
   - "похож на последние треки";
   - "поддержан несколькими треками плейлиста";
   - "часто встречается в MPD".
4. Проверить качество на плейлисте `Мне нравится.txt` и сохранить 2-3 примера выдачи.

### Frontend

Минимальный frontend первой версии:

1. Поле поиска треков.
2. Список результатов поиска.
3. Плейлист пользователя.
4. Drag-and-drop или кнопки вверх/вниз для изменения порядка.
5. Кнопка "Получить рекомендации".
6. Таблица рекомендаций:
   - rank;
   - artist;
   - track;
   - score;
   - count;
   - объяснение.
7. Кнопка "Добавить в плейлист" рядом с рекомендацией.

### Deployment

1. Сделать `Dockerfile` для backend.
2. Сделать `.dockerignore`, чтобы не тащить сырой MPD.
3. Сделать `docker-compose.yml` для локального запуска.
4. Проверить, что `MODEL_DIR` можно задавать через env.
5. Проверить запуск на чистом окружении:

```bash
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

## 13. Возможные улучшения после MVP

### FAISS

Сейчас поиск кандидатов идет через numpy scan по векторам. Для MVP это нормально, но для более быстрого production лучше добавить FAISS.

Что даст FAISS:

```text
быстрый nearest-neighbor search
меньше latency при большом числе запросов
проще масштабировать рекомендации
```

Что появится в артефактах:

```text
faiss.index
id_mapping.npy или id_mapping.json
```

### Postgres

Postgres не нужен для первой версии inference, но пригодится для:

```text
пользователей
сохраненных плейлистов
истории рекомендаций
лайков/дизлайков
логов качества
```

Embeddings в Postgres/pgvector можно добавить позже, но для текущей модели проще и быстрее держать `.npy` + FAISS.

### Music4All

Music4All можно вернуть позже как content-based слой:

```text
жанры
теги
аудио-признаки
эмоциональные признаки
lyrics features
```

Тогда рекомендация станет гибридной:

```text
MPD Item2Vec + Music4All content features + user feedback
```

## 14. Ближайший практический порядок действий

1. Проверить backend после последнего разделения сервисов:

```bash
.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

2. Открыть документацию FastAPI:

```text
http://127.0.0.1:8000/docs
```

3. Проверить руками:
   - `GET /health`;
   - `GET /model`;
   - `GET /tracks/search`;
   - `POST /recommend/playlist`;
   - `POST /recommend/uris`.

4. Добавить CORS и batch endpoints.
5. Собрать минимальный frontend.
6. Подключить frontend к backend.
7. Прогнать сценарий:
   - найти треки;
   - собрать плейлист;
   - получить рекомендации;
   - добавить рекомендацию;
   - снова получить рекомендации.
8. После этого упаковать backend в Docker.

## 15. Критерий готовности первой версии

Первая версия считается готовой, если:

1. Backend стартует одной командой.
2. Модель загружается без ручных действий.
3. Поиск треков работает.
4. Пользователь может собрать плейлист.
5. Рекомендации возвращаются меньше чем за несколько секунд на обычном запросе.
6. В ответе есть не только треки, но и score-компоненты.
7. Frontend показывает рекомендации и позволяет добавить их в плейлист.
8. Проект можно перенести на сервер без сырых MPD-данных.

