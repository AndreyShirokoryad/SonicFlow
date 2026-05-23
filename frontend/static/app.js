const state = {
  playlist: [],
  playlistVisibleLimit: 300,
  recommendations: [],
  matches: [],
  searchQuery: "",
  searchRows: [],
  searchHasMore: false
};

const SEARCH_PAGE_SIZE = 10;
const MATCH_BATCH_SIZE = 1000;
const PLAYLIST_PAGE_SIZE = 300;

const config = window.APP_CONFIG || {};

const elements = {
  modelStatus: document.getElementById("model-status"),
  searchInput: document.getElementById("track-search"),
  searchButton: document.getElementById("search-button"),
  searchResults: document.getElementById("search-results"),
  playlistFile: document.getElementById("playlist-file"),
  sampleButton: document.getElementById("sample-button"),
  playlistList: document.getElementById("playlist-list"),
  clearPlaylist: document.getElementById("clear-playlist"),
  recommendButton: document.getElementById("recommend-button"),
  recommendationList: document.getElementById("recommendation-list"),
  message: document.getElementById("message"),
  matchSummary: document.getElementById("match-summary"),
  presetSelect: document.getElementById("preset-select"),
  topN: document.getElementById("top-n"),
  recentK: document.getElementById("recent-k"),
  minCount: document.getElementById("min-count"),
  githubLink: document.getElementById("github-link")
};

const sampleTracks = [
  { artist: "Nirvana", title: "Heart-Shaped Box" },
  { artist: "System Of A Down", title: "Lonely Day" },
  { artist: "Deftones", title: "Change" },
  { artist: "Linkin Park", title: "Numb" }
];

function setMessage(text, isError = false) {
  elements.message.textContent = text;
  elements.message.classList.toggle("error", isError);
}

function formatApiError(detail) {
  if (!detail) return "";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        const location = Array.isArray(item.loc) ? item.loc.join(".") : "";
        return [location, item.msg].filter(Boolean).join(": ");
      })
      .filter(Boolean)
      .join("; ");
  }
  if (typeof detail === "object") {
    return detail.message || detail.msg || JSON.stringify(detail);
  }
  return String(detail);
}

function spotifyUrl(trackUri) {
  if (!trackUri || !trackUri.startsWith("spotify:track:")) return "";
  return `https://open.spotify.com/track/${trackUri.replace("spotify:track:", "")}`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function playlistIdentity(track) {
  return track.track_uri || `${track.artist || track.artist_name}|${track.title || track.track_name}`;
}

function normalizePlaylistTrack(track) {
  return {
    track_uri: track.track_uri || null,
    artist_name: track.artist_name || track.artist || "",
    track_name: track.track_name || track.title || "",
    album_name: track.album_name || "",
    count: track.count || 0,
    matched: Boolean(track.track_uri),
    match_status: track.track_uri ? "search_result" : "unverified",
    confidence: track.track_uri ? 1 : 0
  };
}

function addTracksToPlaylist(tracks, { render = true, revealAdded = true, position = "bottom" } = {}) {
  const identities = new Set(state.playlist.map(playlistIdentity));
  const normalizedTracks = [];
  let duplicateCount = 0;

  tracks.forEach((track) => {
    const normalized = normalizePlaylistTrack(track);
    const identity = playlistIdentity(normalized);
    if (identities.has(identity)) {
      duplicateCount += 1;
      return;
    }
    identities.add(identity);
    normalizedTracks.push(normalized);
  });

  const addedIndices = normalizedTracks.map((_track, index) =>
    position === "top" ? index : state.playlist.length + index
  );
  if (position === "top") {
    state.playlist = normalizedTracks.concat(state.playlist);
  } else {
    state.playlist.push(...normalizedTracks);
  }
  if (revealAdded && addedIndices.length && position !== "top") {
    state.playlistVisibleLimit = Math.max(state.playlistVisibleLimit, state.playlist.length);
  }
  if (render && addedIndices.length) {
    renderPlaylist();
  }
  return {
    addedCount: addedIndices.length,
    duplicateCount,
    addedIndices
  };
}

function addToPlaylist(track) {
  const result = addTracksToPlaylist([track], { position: "top" });
  if (!result.addedCount) {
    setMessage("Этот трек уже есть в плейлисте.");
    return;
  }
  setMessage("");
}

function removeFromPlaylist(index) {
  state.playlist.splice(index, 1);
  state.playlistVisibleLimit = Math.min(state.playlistVisibleLimit, Math.max(state.playlist.length, PLAYLIST_PAGE_SIZE));
  renderPlaylist();
}

function moveTrack(index, direction) {
  const nextIndex = index + direction;
  if (nextIndex < 0 || nextIndex >= state.playlist.length) return;
  const [track] = state.playlist.splice(index, 1);
  state.playlist.splice(nextIndex, 0, track);
  renderPlaylist();
}

function renderPlaylist() {
  if (!state.playlist.length) {
    elements.playlistList.innerHTML = '<li class="empty-state">Добавь треки через поиск или импорт файла.</li>';
    return;
  }
  const visibleTracks = state.playlist.slice(0, state.playlistVisibleLimit);
  const hiddenCount = Math.max(0, state.playlist.length - visibleTracks.length);
  elements.playlistList.innerHTML = visibleTracks
    .map(
      (track, index) => `
        <li class="playlist-item">
          <span class="playlist-rank">${index + 1}</span>
          <div>
            <div class="track-title">${escapeHtml(track.track_name)}</div>
            <div class="track-meta">${escapeHtml(track.artist_name)}${track.album_name ? ` · ${escapeHtml(track.album_name)}` : ""}</div>
            <div class="playlist-match">
              ${renderMatchBadge(track)}
              ${track.count ? `<span class="track-count">MPD count: ${Number(track.count || 0).toLocaleString("ru-RU")}</span>` : ""}
            </div>
          </div>
          <div class="playlist-actions">
            <button class="small-button" type="button" data-action="up" data-index="${index}" aria-label="Поднять трек">↑</button>
            <button class="small-button" type="button" data-action="down" data-index="${index}" aria-label="Опустить трек">↓</button>
            <button class="small-button remove" type="button" data-action="remove" data-index="${index}">Удалить</button>
          </div>
        </li>
      `
    )
    .join("") +
    (hiddenCount
      ? `<li class="playlist-more"><button class="ghost-button" type="button" data-action="show-more-playlist">Показать ещё ${Math.min(PLAYLIST_PAGE_SIZE, hiddenCount)} из ${hiddenCount}</button></li>`
      : "");
}

function renderMatchBadge(track) {
  if (track.matched && track.track_uri) {
    return `<span class="match-pill found">найдено в MPD</span>`;
  }
  if (track.match_status === "not_found") {
    return `<span class="match-pill missing">нет в MPD</span>`;
  }
  if (track.match_status === "title_only_uncertain") {
    return `<span class="match-pill uncertain">неуверенное совпадение</span>`;
  }
  return `<span class="match-pill pending">не проверено</span>`;
}

function renderSearchResults(rows, hasMore = false) {
  if (!rows.length) {
    elements.searchResults.innerHTML = '<div class="empty-state">Ничего не найдено.</div>';
    return;
  }
  elements.searchResults.innerHTML =
    rows
    .map(
      (track, index) => `
        <div class="result-row">
          <div>
            <div class="track-title">${escapeHtml(track.track_name)}</div>
            <div class="track-meta">${escapeHtml(track.artist_name)}${track.album_name ? ` · ${escapeHtml(track.album_name)}` : ""}</div>
            <div class="track-count">MPD count: ${Number(track.count || 0).toLocaleString("ru-RU")}</div>
          </div>
          <div class="result-actions">
            <button class="small-button add" type="button" data-search-index="${index}">Добавить</button>
          </div>
        </div>
      `
    )
    .join("") +
    (hasMore
      ? '<button class="ghost-button load-more" id="load-more-search" type="button">Показать ещё</button>'
      : "");
  elements.searchResults.querySelectorAll("[data-search-index]").forEach((button) => {
    button.addEventListener("click", () => addToPlaylist(rows[Number(button.dataset.searchIndex)]));
  });
  const loadMore = document.getElementById("load-more-search");
  if (loadMore) {
    loadMore.addEventListener("click", () => searchTracks({ append: true }));
  }
}

async function apiJson(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    }
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(formatApiError(data.detail) || `HTTP ${response.status}`);
  }
  return data;
}

async function checkHealth() {
  try {
    const health = await apiJson("/health");
    if (health.model_loaded) {
      elements.modelStatus.textContent = `Модель: ${Number(health.vocab_size || 0).toLocaleString("ru-RU")} треков`;
      elements.modelStatus.classList.remove("error");
    } else {
      elements.modelStatus.textContent = "Модель не загружена";
      elements.modelStatus.classList.add("error");
    }
  } catch (error) {
    elements.modelStatus.textContent = "API недоступен";
    elements.modelStatus.classList.add("error");
  }
}

async function searchTracks({ append = false } = {}) {
  const query = elements.searchInput.value.trim();
  if (!query) return;
  elements.searchButton.disabled = true;
  if (!append) {
    state.searchQuery = query;
    state.searchRows = [];
    state.searchHasMore = false;
    elements.searchResults.innerHTML = '<div class="empty-state">Поиск...</div>';
  }
  try {
    const offset = append ? state.searchRows.length : 0;
    const rows = await apiJson(
      `/tracks/search?q=${encodeURIComponent(state.searchQuery || query)}&limit=${SEARCH_PAGE_SIZE + 1}&offset=${offset}`
    );
    const visibleRows = rows.slice(0, SEARCH_PAGE_SIZE);
    state.searchRows = append ? state.searchRows.concat(visibleRows) : visibleRows;
    state.searchHasMore = rows.length > SEARCH_PAGE_SIZE;
    renderSearchResults(state.searchRows, state.searchHasMore);
  } catch (error) {
    if (!append) elements.searchResults.innerHTML = "";
    setMessage(error.message, true);
  } finally {
    elements.searchButton.disabled = false;
  }
}

function parseCsvLine(line) {
  const cells = [];
  let cell = "";
  let inQuotes = false;
  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    const next = line[index + 1];
    if (char === '"' && next === '"') {
      cell += '"';
      index += 1;
    } else if (char === '"') {
      inQuotes = !inQuotes;
    } else if ((char === "," || char === ";") && !inQuotes) {
      cells.push(cell.trim());
      cell = "";
    } else {
      cell += char;
    }
  }
  cells.push(cell.trim());
  return cells;
}

function parsePlaylistText(text) {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (!lines.length) return [];

  const header = parseCsvLine(lines[0]).map((cell) => cell.toLowerCase());
  const artistIndex = header.findIndex((cell) => ["artist", "artist_name", "исполнитель"].includes(cell));
  const titleIndex = header.findIndex((cell) => ["title", "track", "track_name", "name", "трек", "название"].includes(cell));
  const hasHeader = artistIndex >= 0 && titleIndex >= 0;

  return lines
    .slice(hasHeader ? 1 : 0)
    .map((line) => {
      if (hasHeader) {
        const cells = parseCsvLine(line);
        return {
          artist_name: cells[artistIndex] || "",
          track_name: cells[titleIndex] || ""
        };
      }
      const dashMatch = line.split(/\s[-–—]\s/);
      if (dashMatch.length >= 2) {
        return {
          artist_name: dashMatch[0].trim(),
          track_name: dashMatch.slice(1).join(" - ").trim()
        };
      }
      const cells = parseCsvLine(line);
      if (cells.length >= 2) {
        return {
          artist_name: cells[0],
          track_name: cells[1]
        };
      }
      return {
        artist_name: "",
        track_name: line
      };
    })
    .filter((track) => track.track_name);
}

async function importPlaylistFile(file) {
  if (!file) return;
  const text = await file.text();
  const rows = parsePlaylistText(text);
  const previousLength = state.playlist.length;
  const result = addTracksToPlaylist(rows, { revealAdded: false });
  if (result.addedCount) {
    state.playlistVisibleLimit = Math.max(
      state.playlistVisibleLimit,
      Math.min(state.playlist.length, previousLength + PLAYLIST_PAGE_SIZE)
    );
    renderPlaylist();
  }
  const duplicateText = result.duplicateCount ? `, пропущено дублей: ${result.duplicateCount}` : "";
  if (!result.addedCount) {
    setMessage(`Новых треков не добавлено${duplicateText}.`);
    return;
  }
  setMessage(`Импортировано треков: ${result.addedCount}${duplicateText}. Проверяю совпадения в MPD...`);
  await syncPlaylistMatches({ indices: result.addedIndices });
}

function recommendationPayload() {
  const seedUris = state.playlist
    .filter((track) => track.matched && track.track_uri)
    .map((track) => track.track_uri);
  return {
    seed_uris: seedUris,
    top_n: Number(elements.topN.value || 20),
    recent_k: Number(elements.recentK.value || 5),
    min_count: Number(elements.minCount.value || 10),
    candidate_pool: 10000,
    preset: elements.presetSelect.value
  };
}

async function syncPlaylistMatches({ indices = null, onlyUnverified = false } = {}) {
  if (!state.playlist.length) return null;
  const matchIndices = indices
    ? indices
    : state.playlist
        .map((track, index) => ({ track, index }))
        .filter(({ track }) => !onlyUnverified || !track.match_status || track.match_status === "unverified")
        .map(({ index }) => index);

  if (!matchIndices.length) {
    renderMatchSummaryFromPlaylist();
    return null;
  }

  let processed = 0;
  let lastMatchData = null;
  for (let start = 0; start < matchIndices.length; start += MATCH_BATCH_SIZE) {
    const batchIndices = matchIndices.slice(start, start + MATCH_BATCH_SIZE);
    const tracks = batchIndices.map((index) => {
      const track = state.playlist[index];
      return {
        artist: track.artist_name,
        title: track.track_name
      };
    });
    const matchData = await apiJson("/recommend/match", {
      method: "POST",
      body: JSON.stringify({ tracks })
    });
    lastMatchData = matchData;
    const matches = matchData.matches || [];
    matches.forEach((match, matchIndex) => {
      const playlistIndex = batchIndices[matchIndex];
      const track = state.playlist[playlistIndex];
      if (!match) return;
      if (match.matched && match.track_uri) {
        state.playlist[playlistIndex] = {
          ...track,
          track_uri: match.track_uri,
          track_name: match.track_name || track.track_name,
          artist_name: match.artist_name || track.artist_name,
          album_name: match.album_name || track.album_name,
          count: match.count || track.count || 0,
          matched: true,
          match_status: match.status,
          confidence: match.confidence
        };
        return;
      }
      state.playlist[playlistIndex] = {
        ...track,
        matched: false,
        match_status: match.status,
        confidence: match.confidence || 0
      };
    });
    processed += batchIndices.length;
    if (matchIndices.length > MATCH_BATCH_SIZE) {
      setMessage(`Проверяю совпадения в MPD: ${processed}/${matchIndices.length}...`);
    }
  }
  renderPlaylist();
  renderMatchSummaryFromPlaylist();
  setMessage(`Проверено: найдено ${matchedPlaylistCount()}/${state.playlist.length} треков в MPD.`);
  return lastMatchData;
}

function matchedPlaylistCount() {
  return state.playlist.filter((track) => track.matched && track.track_uri).length;
}

function renderMatchSummaryFromPlaylist() {
  if (!state.playlist.length) {
    elements.matchSummary.classList.remove("visible");
    elements.matchSummary.textContent = "";
    return;
  }
  const total = state.playlist.length;
  const matched = matchedPlaylistCount();
  const uncertain = state.playlist.filter((track) => track.match_status === "title_only_uncertain").length;
  const pending = state.playlist.filter((track) => track.match_status === "unverified").length;
  elements.matchSummary.textContent = `Matched в MPD: ${matched}/${total}${uncertain ? `, uncertain: ${uncertain}` : ""}${pending ? `, pending: ${pending}` : ""}`;
  elements.matchSummary.classList.add("visible");
}

function renderRecommendations(rows) {
  if (!rows.length) {
    elements.recommendationList.innerHTML = '<div class="empty-state">Кандидатов не найдено. Попробуй снизить min count или добавить больше seed-треков.</div>';
    return;
  }
  elements.recommendationList.innerHTML = rows
    .map((track, index) => {
      const link = spotifyUrl(track.track_uri);
      const score = Math.round(Number(track.score || 0) * 100);
      return `
        <article class="recommendation-item">
          <div class="score-pill">#${track.rank || index + 1}</div>
          <div>
            <div class="track-title">${escapeHtml(track.track_name)}</div>
            <div class="track-meta">${escapeHtml(track.artist_name)}${track.album_name ? ` · ${escapeHtml(track.album_name)}` : ""}</div>
            <div class="reason">${escapeHtml(track.explanation || "близкий playlist-context в MPD")}</div>
            <div class="component-list">
              <span>score ${score}</span>
              <span>recent ${Number(track.recent_similarity || 0).toFixed(3)}</span>
              <span>whole ${Number(track.whole_playlist_similarity || 0).toFixed(3)}</span>
              <span>support ${Number(track.multi_seed_support || 0).toFixed(3)}</span>
              ${track.favorite_artist_affinity ? `<span>favorite ${Number(track.favorite_artist_affinity || 0).toFixed(3)}</span>` : ""}
              <span>count ${Number(track.count || 0).toLocaleString("ru-RU")}</span>
            </div>
          </div>
          <div class="recommendation-actions">
            <button class="small-button add" type="button" data-rec-index="${index}">Добавить</button>
            ${link ? `<a class="small-button" href="${link}" target="_blank" rel="noreferrer">Spotify</a>` : ""}
          </div>
        </article>
      `;
    })
    .join("");
  elements.recommendationList.querySelectorAll("[data-rec-index]").forEach((button) => {
    button.addEventListener("click", () => addToPlaylist(rows[Number(button.dataset.recIndex)]));
  });
}

async function requestRecommendations() {
  if (!state.playlist.length) {
    setMessage("Добавь хотя бы один seed-трек.", true);
    return;
  }
  elements.recommendButton.disabled = true;
  setMessage("Считаю рекомендации...");
  elements.recommendationList.innerHTML = "";
  try {
    await syncPlaylistMatches({ onlyUnverified: true });
    const payload = recommendationPayload();
    if (!payload.seed_uris.length) {
      throw new Error("В MPD не найдено ни одного трека из плейлиста. Рекомендации построить не из чего.");
    }
    const data = await apiJson("/recommend/uris", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    state.recommendations = data.recommendations || [];
    renderRecommendations(state.recommendations);
    setMessage(`Готово. Matched seed tracks: ${data.matched_seed_count}.`);
  } catch (error) {
    setMessage(error.message, true);
  } finally {
    elements.recommendButton.disabled = false;
  }
}

function bindEvents() {
  if (config.githubUrl) {
    elements.githubLink.href = config.githubUrl;
  }

  elements.searchButton.addEventListener("click", searchTracks);
  elements.searchInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") searchTracks();
  });

  elements.playlistFile.addEventListener("change", (event) => {
    importPlaylistFile(event.target.files?.[0]).catch((error) => setMessage(error.message, true));
  });

  elements.sampleButton.addEventListener("click", () => {
    const result = addTracksToPlaylist(
      sampleTracks.map((track) => ({ artist_name: track.artist, track_name: track.title })),
      { position: "top" }
    );
    if (!result.addedCount) setMessage("Эти треки уже есть в плейлисте.");
  });

  elements.clearPlaylist.addEventListener("click", () => {
    state.playlist = [];
    state.playlistVisibleLimit = PLAYLIST_PAGE_SIZE;
    state.recommendations = [];
    elements.recommendationList.innerHTML = "";
    renderMatchSummaryFromPlaylist();
    renderPlaylist();
    setMessage("");
  });

  elements.playlistList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) return;
    const index = Number(button.dataset.index);
    if (button.dataset.action === "remove") removeFromPlaylist(index);
    if (button.dataset.action === "up") moveTrack(index, -1);
    if (button.dataset.action === "down") moveTrack(index, 1);
    if (button.dataset.action === "show-more-playlist") {
      state.playlistVisibleLimit = Math.min(state.playlist.length, state.playlistVisibleLimit + PLAYLIST_PAGE_SIZE);
      renderPlaylist();
    }
  });

  elements.recommendButton.addEventListener("click", requestRecommendations);
}

bindEvents();
renderPlaylist();
checkHealth();
