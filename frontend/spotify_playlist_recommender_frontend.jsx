import React, { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Upload, Music2, Sparkles, ListMusic, ExternalLink, FileText, CheckCircle2, PlayCircle, ArrowRight, Disc3 } from "lucide-react";

const mockRecommendations = [
  {
    artist: "Tame Impala",
    title: "The Less I Know The Better",
    reason: "Близкий вайб по энергии и психоделическому звучанию",
    url: "https://open.spotify.com/track/6K4t31amVTZDgR3sKmwUJJ"
  },
  {
    artist: "Gorillaz",
    title: "On Melancholy Hill",
    reason: "Похоже по мягкой электронике и мелодичной атмосфере",
    url: "https://open.spotify.com/track/0q6LuUqGLUiCPP1cbdwFs3"
  },
  {
    artist: "The Weeknd",
    title: "Blinding Lights",
    reason: "Подходит по темпу, поп-структуре и синтезаторному звучанию",
    url: "https://open.spotify.com/track/0VjIjW4GlUZAMYd2vXMi3b"
  },
  {
    artist: "Daft Punk",
    title: "Instant Crush",
    reason: "Совпадает по электронному груву и плотности аранжировки",
    url: "https://open.spotify.com/track/2cGxRwrMyEAp8dEbuZaVv6"
  },
  {
    artist: "Arctic Monkeys",
    title: "Do I Wanna Know?",
    reason: "Хорошо дополняет плейлист по настроению и гитарному ритму",
    url: "https://open.spotify.com/track/5FVd6KXrgO9B3JPmC8OPst"
  }
];

const sampleTracks = ["Billie Eilish — bad guy", "The Neighbourhood — Sweater Weather", "Glass Animals — Heat Waves"];

const githubUrl = "https://github.com/your-username/playlist-recommender";

function Header({ page, setPage }) {
  return (
    <header className="sticky top-0 z-40 border-b border-emerald-400/10 bg-[#07120d]/85 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <button onClick={() => setPage("home")} className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#1DB954] shadow-lg shadow-emerald-500/20">
            <Disc3 className="h-5 w-5 text-black" />
          </div>
          <div className="text-left">
            <div className="text-lg font-bold tracking-tight text-white">Playlist Recommender</div>
            <div className="text-xs text-emerald-200/60">music recommendations</div>
          </div>
        </button>

        <nav className="hidden items-center gap-2 rounded-full border border-emerald-400/10 bg-white/[0.03] p-1 md:flex">
          <button
            onClick={() => setPage("home")}
            className={`rounded-full px-5 py-2 text-sm font-medium transition ${page === "home" ? "bg-[#1DB954] text-black" : "text-emerald-100/70 hover:bg-white/[0.06] hover:text-white"}`}
          >
            Главная
          </button>
          <button
            onClick={() => setPage("recommend")}
            className={`rounded-full px-5 py-2 text-sm font-medium transition ${page === "recommend" ? "bg-[#1DB954] text-black" : "text-emerald-100/70 hover:bg-white/[0.06] hover:text-white"}`}
          >
            Рекомендации
          </button>
        </nav>

        <div className="hidden items-center gap-3 md:flex">
          <a
            href={githubUrl}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 rounded-full border border-emerald-300/20 bg-white/[0.03] px-5 py-2 text-sm font-bold text-emerald-50 transition hover:bg-white/[0.07]"
          >
            GitHub
            <ExternalLink className="h-4 w-4" />
          </a>
          <button
            onClick={() => setPage("recommend")}
            className="inline-flex items-center gap-2 rounded-full bg-white px-5 py-2 text-sm font-bold text-black transition hover:bg-emerald-100"
          >
            Попробовать
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </header>
  );
}

function HomePage({ setPage }) {
  const stats = [
    { label: "форматы", value: "CSV / TXT" },
    { label: "этапа анализа", value: "4" },
    { label: "выдача", value: "Top-N" }
  ];

  return (
    <main className="relative overflow-hidden bg-[#07120d] text-white">
      <div className="absolute left-[-15%] top-[-20%] h-[520px] w-[520px] rounded-full bg-[#1DB954]/20 blur-[120px]" />
      <div className="absolute bottom-[-15%] right-[-10%] h-[420px] w-[420px] rounded-full bg-emerald-700/20 blur-[110px]" />

      <section className="relative mx-auto grid min-h-[calc(100vh-73px)] max-w-7xl items-center gap-12 px-6 py-20 lg:grid-cols-[1.05fr_0.95fr]">
        <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>

          <h1 className="max-w-3xl text-5xl font-black leading-[0.95] tracking-tight text-white md:text-7xl">
            Найди треки, которые идеально продолжат твой плейлист
          </h1>

          <p className="mt-7 max-w-2xl text-lg leading-8 text-emerald-50/65">
            Загрузи плейлист в формате CSV или TXT, сервис распарсит список треков, найдет знакомые композиции в базе и подберет рекомендации на основе плейлистов других пользователей.
          </p>

          <div className="mt-9 flex flex-col gap-4 sm:flex-row">
            <button
              onClick={() => setPage("recommend")}
              className="group inline-flex items-center justify-center gap-3 rounded-full bg-[#1DB954] px-7 py-4 text-base font-extrabold text-black shadow-2xl shadow-emerald-500/20 transition hover:scale-[1.02] hover:bg-[#22d760]"
            >
              Получить рекомендации
              <PlayCircle className="h-5 w-5 transition group-hover:translate-x-0.5" />
            </button>
            <a
              href={githubUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center justify-center gap-3 rounded-full border border-emerald-300/20 bg-white/[0.03] px-7 py-4 text-base font-bold text-emerald-50 transition hover:bg-white/[0.07]"
            >
              GitHub репозиторий
              <ExternalLink className="h-5 w-5" />
            </a>
          </div>

          <div className="mt-12 grid max-w-xl grid-cols-3 gap-3">
            {stats.map((item) => (
              <div key={item.label} className="rounded-3xl border border-emerald-400/10 bg-white/[0.035] p-4 backdrop-blur">
                <div className="text-2xl font-black text-white">{item.value}</div>
                <div className="mt-1 text-xs uppercase tracking-[0.2em] text-emerald-200/45">{item.label}</div>
              </div>
            ))}
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.7, delay: 0.1 }} className="relative">
          <div className="absolute inset-0 rotate-6 rounded-[2rem] bg-[#1DB954]/20 blur-2xl" />
          <div className="relative rounded-[2rem] border border-emerald-300/15 bg-[#0d1f16]/90 p-5 shadow-2xl shadow-black/40 backdrop-blur-xl">
            <div className="rounded-[1.5rem] bg-black/30 p-5">
              <div className="mb-6 flex items-center justify-between">
                <div>
                  <div className="text-sm text-emerald-200/50">Current playlist</div>
                  <div className="mt-1 text-2xl font-black">Late night mix</div>
                </div>
                <div className="rounded-full bg-[#1DB954] p-3">
                  <Music2 className="h-6 w-6 text-black" />
                </div>
              </div>

              <div className="space-y-3">
                {sampleTracks.map((track, index) => (
                  <div key={track} className="flex items-center gap-4 rounded-2xl border border-emerald-400/10 bg-white/[0.04] p-4">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-400/10 text-sm font-bold text-emerald-200">{index + 1}</div>
                    <div className="min-w-0 flex-1 truncate text-sm text-emerald-50/85">{track}</div>
                    <CheckCircle2 className="h-5 w-5 text-[#1DB954]" />
                  </div>
                ))}
              </div>

              <div className="mt-5 rounded-3xl border border-[#1DB954]/20 bg-[#1DB954]/10 p-5">
                <div className="mb-4 flex items-center gap-2 text-sm font-bold text-[#1DB954]">
                  <Sparkles className="h-4 w-4" />
                  Recommended next
                </div>
                <div className="space-y-2">
                  {mockRecommendations.slice(0, 3).map((track) => (
                    <div key={track.title} className="flex items-center justify-between gap-4 rounded-2xl bg-black/20 px-4 py-3">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-bold text-white">{track.title}</div>
                        <div className="truncate text-xs text-emerald-100/45">{track.artist}</div>
                      </div>
                      <ExternalLink className="h-4 w-4 shrink-0 text-emerald-200/50" />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </section>
    </main>
  );
}

function PipelineStep({ icon: Icon, title, text, active }) {
  return (
    <div className={`rounded-3xl border p-5 transition ${active ? "border-[#1DB954]/40 bg-[#1DB954]/10" : "border-emerald-400/10 bg-white/[0.03]"}`}>
      <div className={`mb-4 flex h-11 w-11 items-center justify-center rounded-2xl ${active ? "bg-[#1DB954] text-black" : "bg-emerald-300/10 text-emerald-200"}`}>
        <Icon className="h-5 w-5" />
      </div>
      <div className="font-bold text-white">{title}</div>
      <div className="mt-2 text-sm leading-6 text-emerald-50/55">{text}</div>
    </div>
  );
}

function RecommendPage() {
  const [fileName, setFileName] = useState("");
  const [isAnalyzed, setIsAnalyzed] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  const status = useMemo(() => {
    if (isAnalyzed) return "Рекомендации готовы";
    if (fileName) return "Файл загружен";
    return "Ожидается плейлист";
  }, [fileName, isAnalyzed]);

  const handleFile = (file) => {
    if (!file) return;
    setFileName(file.name);
    setIsAnalyzed(false);
  };

  const handleAnalyze = () => {
    if (!fileName) return;
    setIsAnalyzed(true);
  };

  return (
    <main className="min-h-[calc(100vh-73px)] bg-[#07120d] px-6 py-10 text-white">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-emerald-400/15 bg-white/[0.03] px-4 py-2 text-sm text-emerald-200/70">
              <ListMusic className="h-4 w-4" />
              Recommendation pipeline
            </div>
            <h1 className="text-4xl font-black tracking-tight md:text-6xl">Загрузи плейлист</h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-emerald-50/60">
              Поддерживаются TXT и CSV. После анализа сайт покажет список рекомендованных треков и ссылки на Spotify.
            </p>
          </div>

          <div className="rounded-full border border-emerald-400/10 bg-white/[0.04] px-5 py-3 text-sm text-emerald-100/70">
            Статус: <span className="font-bold text-[#1DB954]">{status}</span>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <section className="rounded-[2rem] border border-emerald-400/10 bg-[#0b1a12] p-6 shadow-2xl shadow-black/30">
            <div
              onDragOver={(event) => {
                event.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(event) => {
                event.preventDefault();
                setIsDragging(false);
                handleFile(event.dataTransfer.files?.[0]);
              }}
              className={`relative flex min-h-[300px] flex-col items-center justify-center rounded-[1.5rem] border-2 border-dashed p-8 text-center transition ${isDragging ? "border-[#1DB954] bg-[#1DB954]/10" : "border-emerald-300/15 bg-black/20"}`}
            >
              <div className="mb-5 flex h-20 w-20 items-center justify-center rounded-full bg-[#1DB954]/15">
                <Upload className="h-9 w-9 text-[#1DB954]" />
              </div>
              <h2 className="text-2xl font-black">Перетащи файл сюда</h2>
              <p className="mt-3 max-w-sm text-sm leading-6 text-emerald-50/55">
                Или выбери файл вручную. Внутри могут быть строки вида “artist - track”, “artist, track” или экспортированный CSV.
              </p>

              <label className="mt-7 cursor-pointer rounded-full bg-[#1DB954] px-6 py-3 text-sm font-extrabold text-black transition hover:bg-[#22d760]">
                Выбрать CSV/TXT
                <input
                  type="file"
                  accept=".csv,.txt,text/csv,text/plain"
                  className="hidden"
                  onChange={(event) => handleFile(event.target.files?.[0])}
                />
              </label>

              {fileName && (
                <div className="mt-6 flex max-w-full items-center gap-3 rounded-2xl border border-emerald-400/10 bg-white/[0.05] px-4 py-3 text-sm text-emerald-50/80">
                  <FileText className="h-4 w-4 shrink-0 text-[#1DB954]" />
                  <span className="truncate">{fileName}</span>
                </div>
              )}
            </div>

            <button
              onClick={handleAnalyze}
              disabled={!fileName}
              className="mt-5 flex w-full items-center justify-center gap-3 rounded-full bg-white px-6 py-4 text-base font-black text-black transition enabled:hover:bg-emerald-100 disabled:cursor-not-allowed disabled:bg-white/10 disabled:text-white/30"
            >
              Запросить рекомендации
              <Sparkles className="h-5 w-5" />
            </button>
          </section>

          <section className="grid gap-6">
            <div className="grid gap-4 md:grid-cols-3">
              <PipelineStep icon={Upload} title="Загрузка" text="Пользователь отправляет CSV или TXT файл с плейлистом." active={Boolean(fileName)} />
              <PipelineStep icon={Music2} title="Анализ" text="Сервис парсит треки и ищет совпадения в музыкальной базе." active={Boolean(fileName)} />
              <PipelineStep icon={Sparkles} title="Рекомендации" text="Алгоритм подбирает треки на основе плейлистов других пользователей." active={isAnalyzed} />
            </div>

            <div className="rounded-[2rem] border border-emerald-400/10 bg-[#0b1a12] p-6 shadow-2xl shadow-black/30">
              <div className="mb-5 flex items-center justify-between gap-4">
                <div>
                  <h2 className="text-2xl font-black">Результат</h2>
                  <p className="mt-1 text-sm text-emerald-50/50">Список треков со ссылками на Spotify</p>
                </div>
                <div className="rounded-full bg-[#1DB954]/10 px-4 py-2 text-sm font-bold text-[#1DB954]">
                  {isAnalyzed ? `${mockRecommendations.length} tracks` : "empty"}
                </div>
              </div>

              {!isAnalyzed ? (
                <div className="flex min-h-[330px] flex-col items-center justify-center rounded-[1.5rem] border border-emerald-400/10 bg-black/20 p-8 text-center">
                  <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-white/[0.04]">
                    <ListMusic className="h-7 w-7 text-emerald-100/50" />
                  </div>
                  <h3 className="text-xl font-black">Пока нет рекомендаций</h3>
                  <p className="mt-3 max-w-sm text-sm leading-6 text-emerald-50/45">
                    Загрузи файл и нажми кнопку анализа. Здесь появится топ треков для продолжения плейлиста.
                  </p>
                </div>
              ) : (
                <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="space-y-3">
                  {mockRecommendations.map((track, index) => (
                    <a
                      key={`${track.artist}-${track.title}`}
                      href={track.url}
                      target="_blank"
                      rel="noreferrer"
                      className="group flex items-center gap-4 rounded-3xl border border-emerald-400/10 bg-white/[0.035] p-4 transition hover:border-[#1DB954]/40 hover:bg-[#1DB954]/10"
                    >
                      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-black/30 text-sm font-black text-emerald-200 group-hover:bg-[#1DB954] group-hover:text-black">
                        {index + 1}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-base font-black text-white">{track.title}</div>
                        <div className="truncate text-sm text-emerald-100/55">{track.artist}</div>
                        <div className="mt-1 line-clamp-1 text-xs text-emerald-50/35">{track.reason}</div>
                      </div>
                      <div className="hidden rounded-full border border-emerald-400/10 px-4 py-2 text-xs font-bold text-emerald-100/55 transition group-hover:border-[#1DB954]/30 group-hover:text-[#1DB954] sm:block">
                        Spotify
                      </div>
                      <ExternalLink className="h-5 w-5 shrink-0 text-emerald-100/40 group-hover:text-[#1DB954]" />
                    </a>
                  ))}
                </motion.div>
              )}
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}

export default function PlaylistRecommenderFrontend() {
  const [page, setPage] = useState("home");

  return (
    <div className="min-h-screen bg-[#07120d] font-sans text-white">
      <Header page={page} setPage={setPage} />
      {page === "home" ? <HomePage setPage={setPage} /> : <RecommendPage />}
    </div>
  );
}
