# Data and model files

Large datasets and trained production model files are not stored in git.

For the full application, put exported Item2Vec model files here:

```text
data/models/item2vec_mpd_gensim/
  item_vectors_normalized.npy
  vocab.jsonl
  model_meta.json
```

Optional extra exported files such as `item_vectors.npy` or gensim model files can also live in the same directory, but inference only requires the normalized vectors, vocabulary, and metadata.

The repository keeps a tiny smoke model in:

```text
data/models/item2vec_mpd_gensim_smoke/
```

It is only for API smoke checks and development sanity tests. It is not representative of recommendation quality.
