# Playlist Recommender Project

## 1. Идея проекта

Проект: веб-сервис, где пользователь может собрать плейлист из большого набора треков, получить аналитику по этому плейлисту и рекомендации следующих треков для добавления.

Главная цель проекта — не просто рекомендовать похожие треки по среднему embedding'у, а попробовать учитывать более глубокие закономерности:

- общую похожесть треков;
- жанры и теги;
- музыкальные признаки;
- связность плейлиста;
- выбивающиеся треки;
- динамику последних добавленных треков;
- потенциальные переходы между музыкальными состояниями;
- в будущем — поведение пользователей и плейлистовые co-occurrence-сигналы.

На первом этапе проект учебный, поэтому важно, чтобы он был реалистичным по ресурсам и мог запускаться в Docker на сервере.

## 2. Что пользователь должен уметь делать

Минимальная версия сайта:

1. Искать треки по названию или артисту.
2. Добавлять треки в свой плейлист.
3. Менять порядок треков.
4. Удалять треки из плейлиста.
5. Получать аналитику плейлиста.
6. Получать рекомендации треков для добавления.
7. Видеть объяснение рекомендаций.

Пример объяснения рекомендации:

```text
Трек предложен, потому что:
- похож на последние добавленные треки;
- совпадает по тегам: melancholic, indie, atmospheric;
- попадает в близкий музыкальный кластер;
- не является почти полным дубликатом уже выбранных треков.
```

## 3. Основной датасет

Основной датасет для первой версии:

```text
Music4All-Onion v2
```

Ссылка:

```text
https://zenodo.org/records/15394646
```

Почему выбран он:

- не нужно хранить MP3;
- есть признаки треков;
- есть embeddings;
- есть теги и жанры;
- есть listening records для будущего collaborative filtering;
- можно скачивать не весь датасет, а только нужные файлы;
- проще для учебного проекта, чем полный Spotify Million Playlist Dataset.

Важно: Music4All-Onion v2 не является датасетом готовых плейлистов. Это датасет признаков треков и пользовательских прослушиваний. Поэтому на первом этапе рекомендации будут content-based, а не playlist-continuation на реальных плейлистах.

## 4. Дополнительный датасет на будущее

Дополнительный датасет, который можно добавить позже:

```text
Spotify Million Playlist Dataset
```

Он полезен для задачи:

```text
по первым трекам плейлиста предсказать следующие треки
```

Но для старта он тяжелее:

- много JSON-файлов;
- большой объем данных;
- нет audio features;
- придется извлекать сигнал только из co-occurrence в плейлистах;
- потребуется отдельная обработка и, возможно, матчинг с Music4All по Spotify ID, названию и артисту.

Идеальная будущая архитектура:

```text
Music4All-Onion = признаки, теги, жанры, embeddings, listening history
Spotify MPD = реальные плейлисты и co-occurrence
```

## 5. Файлы Music4All-Onion v2

Для первой версии не нужно качать все 19.9 GB.

### Минимальный набор

```text
id_genres_tf-idf.tsv.bz2
id_tags_dict.tsv.bz2
id_tags_tf-idf.tsv.bz2
id_ivec256.tsv.bz2
id_musicnn.tsv.bz2
id_mfcc_stats.tsv.bz2
```

Этого достаточно для:

- похожести треков;
- content-based рекомендаций;
- жанровой аналитики;
- tag-based аналитики;
- кластеризации;
- поиска выбросов;
- первичной динамики плейлиста.

### Что добавить позже

```text
userid_trackid_count.tsv.bz2
id_lyrics_sentiment_functionals.tsv.bz2
id_vad_bow.tsv.bz2
id_gems.tsv.bz2
id_essentia.tsv.bz2
```

### Что не качать на старте

```text
id_jukebox.tsv.bz2
id_incp.tsv.bz2
id_resnet.tsv.bz2
id_vgg19.tsv.bz2
userid_trackid_timestamp.tsv.bz2
id_blf_logfluc.tsv.bz2
id_compare_audspec_stats.tsv.bz2
```

Причина: эти файлы тяжелые и не нужны для первой рабочей версии.

## 6. Назначение основных файлов

### `id_genres_tf-idf.tsv.bz2`

TF-IDF-вектор жанров для треков.

Использование:

- топ жанров плейлиста;
- genre similarity;
- жанровая связность плейлиста;
- жанровое разнообразие.

### `id_tags_dict.tsv.bz2`

Человекочитаемые Last.fm-теги и веса.

Использование:

- отображение тегов пользователю;
- объяснение рекомендаций;
- топ тегов плейлиста;
- mood/style summary.

### `id_tags_tf-idf.tsv.bz2`

TF-IDF-вектор тегов.

Использование:

- similarity по тегам;
- поиск похожих треков;
- tag-based recommendation;
- анализ настроения и стиля.

### `id_ivec256.tsv.bz2`

256-dimensional audio embedding на основе MFCC/i-vector.

Использование:

- основной embedding для трека;
- поиск похожих треков;
- кластеризация;
- cohesion/diversity;
- outlier detection;
- recommendations.

### `id_musicnn.tsv.bz2`

Компактные neural audio features из musicnn.

Использование:

- альтернативный или дополнительный audio embedding;
- content-based similarity;
- сравнение качества с `id_ivec256`.

### `id_mfcc_stats.tsv.bz2`

Статистики MFCC.

Использование:

- анализ тембра;
- дополнительный аудио-сигнал;
- можно использовать позже, не обязательно в первой версии.

### `userid_trackid_count.tsv.bz2`

Агрегированные прослушивания:

```text
user_id, track_id, play_count
```

Использование:

- collaborative filtering;
- item-item similarity по пользователям;
- ALS/BPR/LightFM в будущих версиях.

### `userid_trackid_timestamp.tsv.bz2`

События прослушивания с timestamp.

Использование:

- sequential recommendation;
- session-based recommendation;
- анализ реальной последовательности прослушиваний.

Для первой версии не использовать, потому что файл тяжелый.

## 7. Формат файлов

Файлы `.tsv.bz2` не нужно вручную распаковывать.

Их можно читать напрямую:

```python
import pandas as pd

df = pd.read_csv(
    "data/raw/id_ivec256.tsv.bz2",
    sep="\t",
    compression="bz2"
)
```

Если нет header:

```python
import pandas as pd

df = pd.read_csv(
    "data/raw/id_ivec256.tsv.bz2",
    sep="\t",
    compression="bz2",
    header=None
)
```

После чтения лучше сохранить обработанные данные в более быстрый формат:

- Postgres для метаданных, тегов, жанров, плейлистов;
- pgvector для embeddings;
- optional `.npy`/`.parquet` для offline экспериментов.

## 8. Важный нюанс по metadata

Music4All-Onion v2 в основном содержит признаки и listening records. Для нормального интерфейса нужны человекочитаемые данные:

```text
track_id -> title
track_id -> artist
track_id -> album
```

Нужно найти и подключить базовые metadata Music4All:

```text
id_information.csv
id_metadata.csv
```

или аналогичные файлы из базового Music4All.

Без metadata сайт сможет работать технически, но пользователю будут видны только internal track_id, что плохо.

## 9. Архитектура проекта

Планируемая архитектура:

```text
React frontend
        ↓
FastAPI backend
        ↓
Postgres + pgvector
```

Данные не должны быть частью Docker image.

Правильно:

```text
Docker image = код приложения
Postgres volume = база данных
data/raw = исходные датасеты
data/processed = промежуточные артефакты
```

Неправильно:

```text
запихивать 20 GB датасета внутрь Docker image
```

## 10. Структура репозитория

```text
playlist-recommender/
  backend/
    app/
      main.py
      db.py
      schemas.py
      api/
        tracks.py
        playlists.py
        recommendations.py
        analysis.py
      services/
        track_service.py
        recommendation_service.py
        analysis_service.py
        data_import_service.py
    Dockerfile
    requirements.txt

  frontend/
    src/
      api/
      components/
      pages/
      store/
    Dockerfile
    package.json
    vite.config.ts

  db/
    init/
      001_extensions.sql
      002_schema.sql
      003_indexes.sql

  scripts/
    inspect_raw_files.py
    import_metadata.py
    import_features.py
    import_tags.py
    import_genres.py
    build_neighbors.py
    build_clusters.py
    evaluate_recommender.py

  data/
    raw/
    processed/

  docker-compose.yml
  .env.example
  README.md
```

## 11. Docker Compose

```yaml
services:
  db:
    image: pgvector/pgvector:pg18
    container_name: playlist_db
    environment:
      POSTGRES_DB: playlist_recommender
      POSTGRES_USER: playlist
      POSTGRES_PASSWORD: playlist
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./db/init:/docker-entrypoint-initdb.d

  backend:
    build: ./backend
    container_name: playlist_backend
    environment:
      DATABASE_URL: postgresql+asyncpg://playlist:playlist@db:5432/playlist_recommender
    ports:
      - "8000:8000"
    depends_on:
      - db

  frontend:
    build: ./frontend
    container_name: playlist_frontend
    ports:
      - "3000:80"
    depends_on:
      - backend

volumes:
  postgres_data:
```

## 12. Postgres extensions

`db/init/001_extensions.sql`

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

`vector` нужен для embedding search.

`pg_trgm` нужен для поиска по названию и артисту с опечатками.

## 13. Схема базы данных

`db/init/002_schema.sql`

```sql
CREATE TABLE tracks (
    id TEXT PRIMARY KEY,
    title TEXT,
    artist TEXT,
    album TEXT,
    spotify_id TEXT,
    duration_ms INTEGER,
    popularity REAL,
    metadata JSONB
);

CREATE TABLE track_features (
    track_id TEXT PRIMARY KEY REFERENCES tracks(id) ON DELETE CASCADE,
    ivec256 vector(256),
    musicnn vector,
    mfcc_stats JSONB,
    gems JSONB,
    lyrics_sentiment JSONB
);

CREATE TABLE track_tags (
    track_id TEXT REFERENCES tracks(id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    weight REAL NOT NULL,
    PRIMARY KEY (track_id, tag)
);

CREATE TABLE track_genres (
    track_id TEXT REFERENCES tracks(id) ON DELETE CASCADE,
    genre TEXT NOT NULL,
    weight REAL NOT NULL,
    PRIMARY KEY (track_id, genre)
);

CREATE TABLE playlists (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE playlist_tracks (
    playlist_id BIGINT REFERENCES playlists(id) ON DELETE CASCADE,
    track_id TEXT REFERENCES tracks(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    added_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (playlist_id, track_id)
);

CREATE TABLE track_neighbors (
    track_id TEXT REFERENCES tracks(id) ON DELETE CASCADE,
    neighbor_track_id TEXT REFERENCES tracks(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    score REAL NOT NULL,
    rank INTEGER NOT NULL,
    PRIMARY KEY (track_id, neighbor_track_id, source)
);

CREATE TABLE listening_counts (
    user_id TEXT NOT NULL,
    track_id TEXT REFERENCES tracks(id) ON DELETE CASCADE,
    play_count INTEGER NOT NULL,
    PRIMARY KEY (user_id, track_id)
);

CREATE TABLE track_clusters (
    track_id TEXT PRIMARY KEY REFERENCES tracks(id) ON DELETE CASCADE,
    cluster_id INTEGER NOT NULL,
    model_name TEXT NOT NULL
);
```

## 14. Индексы

`db/init/003_indexes.sql`

```sql
CREATE INDEX tracks_title_trgm_idx ON tracks USING gin (title gin_trgm_ops);
CREATE INDEX tracks_artist_trgm_idx ON tracks USING gin (artist gin_trgm_ops);

CREATE INDEX track_tags_tag_idx ON track_tags (tag);
CREATE INDEX track_genres_genre_idx ON track_genres (genre);

CREATE INDEX track_features_ivec256_hnsw_idx
ON track_features
USING hnsw (ivec256 vector_cosine_ops);

CREATE INDEX track_neighbors_track_source_idx
ON track_neighbors (track_id, source, rank);

CREATE INDEX playlist_tracks_playlist_position_idx
ON playlist_tracks (playlist_id, position);
```

## 15. Backend stack

Backend:

```text
FastAPI
SQLAlchemy async
asyncpg
Pydantic
NumPy
Pandas
Scikit-learn
```

`backend/requirements.txt`

```text
fastapi
uvicorn[standard]
sqlalchemy[asyncio]
asyncpg
pydantic
numpy
pandas
scikit-learn
python-dotenv
```

## 16. Backend DB connection

`backend/app/db.py`

```python
import os
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_session():
    async with SessionLocal() as session:
        yield session
```

## 17. API endpoints

### Tracks

```text
GET /tracks/search?q=...
GET /tracks/{track_id}
GET /tracks/{track_id}/similar
```

### Playlists

```text
POST /playlists
GET /playlists/{playlist_id}
POST /playlists/{playlist_id}/tracks
DELETE /playlists/{playlist_id}/tracks/{track_id}
PATCH /playlists/{playlist_id}/tracks/reorder
```

### Analysis

```text
POST /playlists/analyze
```

Input:

```json
{
  "track_ids": ["track_1", "track_2", "track_3"]
}
```

Output:

```json
{
  "top_tags": [
    {"tag": "melancholic", "weight": 0.71},
    {"tag": "indie", "weight": 0.58}
  ],
  "top_genres": [
    {"genre": "rock", "weight": 0.62}
  ],
  "cohesion": 0.74,
  "diversity": 0.31,
  "outliers": [
    {
      "track_id": "track_3",
      "reason": "low similarity to other playlist tracks"
    }
  ]
}
```

### Recommendations

```text
POST /playlists/recommend
```

Input:

```json
{
  "track_ids": ["track_1", "track_2", "track_3"],
  "limit": 20
}
```

Output:

```json
{
  "recommendations": [
    {
      "track_id": "track_42",
      "title": "Song",
      "artist": "Artist",
      "score": 0.84,
      "reasons": [
        "similar to recent tracks",
        "matching tags",
        "same cluster"
      ]
    }
  ]
}
```

## 18. Frontend

Frontend:

```text
React
Vite
TypeScript
```

Основные экраны:

1. Поиск треков.
2. Конструктор плейлиста.
3. Аналитика плейлиста.
4. Рекомендации.
5. Страница трека.

Компоненты:

```text
TrackSearch
TrackCard
PlaylistBuilder
PlaylistTrackList
PlaylistAnalysisPanel
RecommendationList
TagCloud
GenreDistribution
CohesionScore
OutlierList
```

## 19. Data preprocessing

Не запускать тяжелую обработку при старте backend.

Плохо:

```text
docker compose up
→ backend читает .bz2
→ backend считает embeddings
→ сервер перегружается
```

Хорошо:

```text
python scripts/import_metadata.py
python scripts/import_features.py
python scripts/import_tags.py
python scripts/import_genres.py
python scripts/build_neighbors.py
docker compose up
```

## 20. Импорт признаков

Пример чтения `.tsv.bz2`:

```python
import pandas as pd

df = pd.read_csv(
    "data/raw/id_ivec256.tsv.bz2",
    sep="\t",
    compression="bz2"
)
```

При импорте нужно:

1. Определить, есть ли header.
2. Найти колонку `track_id`.
3. Преобразовать вектор в список float.
4. Записать в `track_features.ivec256`.

Для больших файлов желательно читать чанками:

```python
import pandas as pd

chunks = pd.read_csv(
    "data/raw/id_ivec256.tsv.bz2",
    sep="\t",
    compression="bz2",
    chunksize=5000
)

for chunk in chunks:
    pass
```

## 21. Поиск похожих треков через pgvector

Пример SQL:

```sql
SELECT
    t.id,
    t.title,
    t.artist,
    1 - (f.ivec256 <=> q.embedding) AS score
FROM track_features f
JOIN tracks t ON t.id = f.track_id
CROSS JOIN (
    SELECT ivec256 AS embedding
    FROM track_features
    WHERE track_id = $1
) q
WHERE f.track_id <> $1
ORDER BY f.ivec256 <=> q.embedding
LIMIT $2;
```

## 22. Предрасчет соседей

Для слабого сервера лучше предрассчитать ближайших соседей.

Таблица:

```text
track_neighbors
```

Для каждого трека сохранить top-50 или top-100 соседей:

```text
track_id
neighbor_track_id
source
score
rank
```

Варианты `source`:

```text
ivec256
musicnn
tags
genres
hybrid
```

Для рекомендаций сайт сможет быстро брать соседей уже из таблицы, без heavy vector search.

## 23. Первая версия рекомендаций

На первом этапе использовать content-based recommender.

Пусть пользователь выбрал плейлист:

```text
P = [t1, t2, t3, t4, t5]
```

Candidate generation:

1. Взять соседей каждого трека из `track_neighbors`.
2. Объединить кандидатов.
3. Убрать треки, которые уже есть в плейлисте.
4. Посчитать итоговый score.
5. Вернуть top-N.

Формула:

```text
score(candidate) =
  0.35 * recent_similarity
+ 0.25 * whole_playlist_similarity
+ 0.20 * tag_genre_match
+ 0.10 * novelty
+ 0.10 * trajectory_fit
```

### `recent_similarity`

Похожесть кандидата на последние 3-5 треков.

Идея: последние треки лучше отражают текущее состояние плейлиста.

### `whole_playlist_similarity`

Похожесть кандидата на общий плейлист.

На старте можно считать через средний embedding, но позже заменить на top-k similarity.

### `tag_genre_match`

Совпадение тегов и жанров с плейлистом.

### `novelty`

Штраф за слишком популярные или слишком очевидные треки.

На первом этапе можно заменить на простой popularity penalty, если есть popularity.

### `trajectory_fit`

Сигнал динамики.

На первом этапе можно сделать просто:

```text
кандидат похож на последние треки сильнее, чем на весь плейлист
```

Позже можно использовать кластеры и динамику признаков.

## 24. Не использовать только средний embedding

Средний embedding можно использовать как baseline, но он слабый.

Проблемы среднего:

- теряет кластеры внутри плейлиста;
- не видит чередование настроения;
- не видит выбросы;
- не видит порядок треков;
- не различает плейлист из двух противоположных блоков и плейлист из средних треков.

Более интересные методы:

```text
symmetric top-k set similarity
cluster-based similarity
trajectory-aware similarity
centrality-weighted representation
Markov transitions between clusters
```

## 25. Top-k similarity вместо среднего

Для кандидата считать похожесть не к среднему плейлиста, а к нескольким ближайшим трекам плейлиста:

```text
candidate_score =
    average top-k similarity(candidate, tracks_in_playlist)
```

Пример:

```text
candidate похож на 3 трека из плейлиста
→ хороший кандидат

candidate похож только на среднее, но ни на один конкретный трек
→ сомнительный кандидат
```

Это лучше для мультимодальных плейлистов.

## 26. Аналитика плейлиста

### Top tags

Из `track_tags`:

```text
melancholic
indie
atmospheric
female vocal
electronic
```

### Top genres

Из `track_genres`:

```text
rock
electronic
ambient
folk
```

### Cohesion

Насколько треки связаны между собой:

```text
cohesion = average pairwise similarity
```

Высокая cohesion означает, что плейлист цельный.

### Diversity

Насколько плейлист разнообразен:

```text
diversity = average pairwise distance
```

### Outliers

Для каждого трека:

```text
centrality(track) = average similarity(track, other_tracks)
```

Треки с низкой centrality — выбросы.

### Clusters

Кластеризовать треки по embedding.

Пример результата:

```text
cluster 1: melancholic / indie / acoustic
cluster 2: electronic / energetic / dance
```

### Transition analysis

Если порядок треков важен:

```text
track_1 -> track_2 -> track_3
```

Можно анализировать:

- меняются ли кластеры;
- есть ли чередование;
- растет или падает энергия;
- насколько часто плейлист меняет состояние.

## 27. Идея динамики и sequence-рекомендаций

Будущая цель:

```text
предсказывать следующий трек, учитывая не только похожесть, но и динамику плейлиста
```

Примеры динамики:

```text
спокойный -> энергичный -> спокойный -> энергичный
melancholic -> upbeat -> melancholic -> upbeat
intro -> growth -> peak -> outro
```

В реальных данных это будет шумно, поэтому лучше не искать буквальную синусоиду, а использовать более устойчивые признаки:

```text
trend
volatility
autocorrelation
change points
cluster transitions
transition entropy
```

## 28. Cluster transition model

Более устойчивая версия sequence-подхода:

1. Кластеризовать все треки по embeddings.
2. Представить плейлист как последовательность кластеров.

```text
[t1, t2, t3, t4]
↓
[cluster_2, cluster_2, cluster_5, cluster_3]
```

3. Учить переходы:

```text
P(next_cluster | previous_cluster)
```

или:

```text
P(next_cluster | previous_2_clusters)
```

4. Рекомендовать треки из предсказанного следующего кластера.

Это проще и устойчивее, чем сразу предсказывать конкретный track_id.

## 29. Spotify MPD как будущий источник playlist continuation

Если позже добавить Spotify MPD, подходы будут другие.

В Spotify MPD нет audio features, поэтому сигнал будет только из плейлистов:

```text
какие треки люди кладут вместе
```

Актуальные методы:

```text
co-occurrence
PMI / PPMI
ItemKNN
Item2Vec
ALS
BPR
LightGCN
graph random walk
sequence models
```

Для Spotify MPD аналитика будет не музыкальная, а структурная:

- насколько треки часто встречаются вместе;
- какие треки центральные;
- какие выбиваются;
- насколько плейлист похож на реальные плейлисты;
- насколько треки mainstream по частотности.

## 30. Music4All vs Spotify MPD

### Music4All-Onion

Подходит для:

```text
feature analysis
content-based recommendations
tags / genres / audio features
playlist analytics
clustering
outlier detection
collaborative filtering later
```

### Spotify MPD

Подходит для:

```text
playlist continuation
co-occurrence recommendations
Item2Vec
sequence prediction
graph-based recommendations
```

### Гибридная система

В будущем:

```text
score(candidate) =
  0.40 * content_score
+ 0.35 * playlist_cooccurrence_score
+ 0.25 * collaborative_score
```

Но для этого нужно сматчить треки между датасетами.

## 31. Matching Music4All и Spotify MPD

Если в Music4All есть Spotify ID, лучший join:

```text
spotify_id
```

Если Spotify ID нет:

```text
normalize(title) + normalize(artist) + duration_ms
```

Проблемы fuzzy matching:

- remaster;
- radio edit;
- live version;
- explicit/clean;
- feat.;
- одинаковые названия;
- разные варианты написания артиста.

На первом этапе не делать гибрид. Сначала сделать Music4All-only.

## 32. ML или не ML

Первая версия может быть без обучения тяжелых моделей.

Не ML / simple algorithms:

```text
cosine similarity
Jaccard
top-k nearest neighbors
manual scoring
cohesion/diversity
outlier detection
precomputed neighbors
```

Легкое ML:

```text
KMeans
HDBSCAN
PCA
UMAP
ItemKNN
```

Более серьезное ML:

```text
ALS
BPR
LightFM
Item2Vec
GRU4Rec
SASRec
Transformer
Learning-to-rank
```

Рекомендуемый путь:

```text
1. Simple content-based recommender
2. Clustering and trajectory analysis
3. Collaborative filtering
4. Sequence-aware recommendation
5. Hybrid model
```

## 33. Evaluation

Даже для учебного проекта нужны метрики.

Для content-based рекомендаций можно начать с qualitative evaluation:

- рекомендации выглядят похожими;
- теги совпадают;
- нет явных мусорных треков;
- плейлист становится связнее.

Позже, если использовать listening counts:

```text
train/test split по user-track interactions
```

Метрики:

```text
Recall@K
Precision@K
NDCG@K
MAP@K
MRR
Coverage
Diversity
Novelty
```

Для sequence-рекомендаций:

```text
prefix -> next item
```

Метрики:

```text
HitRate@K
Recall@K
NDCG@K
MRR
```

## 34. План реализации

### Этап 1

- Поднять Docker Compose с Postgres + pgvector.
- Создать схему БД.
- Импортировать metadata.
- Импортировать `id_ivec256`.
- Сделать поиск треков.
- Сделать похожие треки через pgvector.

### Этап 2

- Импортировать tags и genres.
- Сделать аналитику плейлиста.
- Сделать top tags/top genres.
- Сделать cohesion/diversity.
- Сделать outlier detection.

### Этап 3

- Предрасчитать `track_neighbors`.
- Сделать endpoint `/playlists/recommend`.
- Сделать простые объяснения рекомендаций.

### Этап 4

- Сделать React frontend.
- Реализовать поиск.
- Реализовать playlist builder.
- Реализовать страницу аналитики.
- Реализовать рекомендации.

### Этап 5

- Добавить кластеризацию.
- Добавить cluster-based аналитику.
- Добавить transition analysis.
- Добавить trajectory-aware scoring.

### Этап 6

- Добавить `userid_trackid_count`.
- Сделать collaborative filtering.
- Сравнить content-based и collaborative рекомендации.

### Этап 7

- Попробовать Spotify MPD subset.
- Сделать co-occurrence model.
- Сделать Item2Vec.
- Попробовать гибрид.

## 35. Минимальный MVP

MVP считается готовым, если:

1. Docker Compose запускает backend, frontend и Postgres.
2. В базе есть треки с metadata.
3. В базе есть embeddings.
4. На сайте можно найти трек.
5. Можно собрать плейлист.
6. Можно получить аналитику:
   - top tags;
   - top genres;
   - cohesion;
   - diversity;
   - outliers.
7. Можно получить рекомендации.
8. Каждая рекомендация имеет хотя бы простое объяснение.

## 36. Важные технические решения

### Не хранить raw dataset в Docker image

Данные должны быть в volume или импортированы в Postgres.

### Не обрабатывать `.bz2` при старте приложения

Импорт и preprocessing запускаются отдельными скриптами.

### Начать с `id_ivec256`

Это хороший первый embedding.

### Добавить `id_musicnn` как альтернативу

Можно сравнить качество рекомендаций.

### Использовать pgvector

Для поиска похожих треков и будущих экспериментов.

### Использовать `track_neighbors`

Для быстрых online-рекомендаций.

### Не начинать с тяжелого ML

Сначала сделать простой content-based baseline.

## 37. Задачи для Codex

### Backend

1. Создать FastAPI проект.
2. Подключить async SQLAlchemy.
3. Создать модели или SQL-запросы для таблиц.
4. Реализовать `/tracks/search`.
5. Реализовать `/tracks/{track_id}`.
6. Реализовать `/tracks/{track_id}/similar`.
7. Реализовать `/playlists/analyze`.
8. Реализовать `/playlists/recommend`.

### Database

1. Создать SQL migration/init scripts.
2. Подключить `vector`.
3. Подключить `pg_trgm`.
4. Создать индексы.
5. Проверить HNSW index для `ivec256`.

### Data scripts

1. Написать `inspect_raw_files.py`.
2. Написать `import_metadata.py`.
3. Написать `import_features.py`.
4. Написать `import_tags.py`.
5. Написать `import_genres.py`.
6. Написать `build_neighbors.py`.
7. Написать `build_clusters.py`.

### Frontend

1. Создать React + Vite проект.
2. Сделать страницу поиска.
3. Сделать конструктор плейлиста.
4. Сделать аналитику.
5. Сделать рекомендации.
6. Добавить отображение reasons.

### Recommendation service

1. Реализовать похожие треки по `track_neighbors`.
2. Реализовать fallback через pgvector.
3. Реализовать scoring.
4. Убирать уже выбранные треки.
5. Возвращать top-N.
6. Генерировать reasons.

## 38. Первичная формула recommendation scoring

```text
score(candidate) =
  0.35 * recent_similarity
+ 0.25 * whole_playlist_similarity
+ 0.20 * tag_genre_match
+ 0.10 * novelty
+ 0.10 * trajectory_fit
```

На первом этапе можно упростить:

```text
score(candidate) =
  0.50 * neighbor_score
+ 0.30 * tag_match
+ 0.20 * genre_match
```

## 39. Первичная формула анализа

```text
cohesion = average pairwise cosine similarity
diversity = 1 - cohesion
track_centrality = average similarity to other tracks
outlier_score = 1 - track_centrality
```

## 40. Риски

### Нет metadata

Нужно отдельно найти базовый Music4All metadata.

### Большие файлы

Не читать все сразу, использовать chunk processing.

### pgvector dimension

Если `musicnn` или другой embedding имеет неизвестную размерность, сначала нужно проверить первые строки.

### Слишком медленный vector search

Использовать `track_neighbors`.

### Качество рекомендаций может быть субъективным

Добавить explanations и несколько источников score.

### Данные шумные

Не делать слишком сложные выводы про настроение на первом этапе.

## 41. Что не делать в первой версии

Не делать сразу:

```text
Spotify MPD full import
Transformer
GRU4Rec
SASRec
LightGCN
сложный fuzzy matching
импорт из Spotify API
хранение MP3
real-time heavy vector search для каждого запроса
```

## 42. Итоговая формулировка проекта

Проект — это веб-сервис для сборки и анализа плейлистов с content-based рекомендациями треков.

Первая версия использует Music4All-Onion v2: теги, жанры и audio embeddings. Система показывает аналитику плейлиста, ищет похожие треки и предлагает рекомендации с объяснениями.

Архитектура строится вокруг FastAPI, React, Postgres и pgvector. Тяжелая обработка датасета выполняется offline-скриптами. В будущем проект можно расширить collaborative filtering по listening records, sequence-aware рекомендациями и гибридизацией со Spotify Million Playlist Dataset.
