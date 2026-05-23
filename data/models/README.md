# Model directory

Put the full exported model in:

```text
data/models/item2vec_mpd_gensim/
```

Required files:

```text
item_vectors_normalized.npy
vocab.jsonl
model_meta.json
```

For a quick smoke check without the full model, use the included tiny model:

```bash
MODEL_DIR=data/models/item2vec_mpd_gensim_smoke .venv/bin/python scripts/smoke_api.py
```
