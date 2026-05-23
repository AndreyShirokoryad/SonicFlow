from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles

from backend.app.api.health import router as health_router
from backend.app.api.recommendations import router as recommendations_router
from backend.app.api.tracks import router as tracks_router
from backend.app.config import settings
from backend.app.services.item2vec_service import Item2VecService


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = PROJECT_ROOT / "frontend" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    service = Item2VecService(settings.model_dir, enable_faiss=settings.enable_faiss)
    app.state.recommender = service
    app.state.startup_error = None
    try:
        service.load()
    except Exception as exc:
        app.state.startup_error = str(exc)
        if settings.require_model_on_startup:
            raise
    yield


app = FastAPI(
    title="PlaylistAnalyze Backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(tracks_router)
app.include_router(recommendations_router)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _render_html(filename: str) -> HTMLResponse:
    path = STATIC_DIR / filename
    html = path.read_text(encoding="utf-8")
    html = html.replace("%PUBLIC_BASE_URL%", settings.public_base_url.rstrip("/"))
    html = html.replace("%GITHUB_URL%", settings.github_url)
    return HTMLResponse(html)


@app.get("/", include_in_schema=False)
def frontend() -> HTMLResponse:
    return _render_html("index.html")


@app.get("/documentation", include_in_schema=False)
def documentation() -> HTMLResponse:
    return _render_html("documentation.html")


@app.get("/robots.txt", include_in_schema=False)
def robots_txt() -> PlainTextResponse:
    base_url = settings.public_base_url.rstrip("/")
    return PlainTextResponse(
        "\n".join(
            [
                "User-agent: *",
                "Allow: /",
                f"Sitemap: {base_url}/sitemap.xml",
            ]
        )
        + "\n"
    )


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap_xml() -> Response:
    base_url = settings.public_base_url.rstrip("/")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{base_url}/</loc>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>{base_url}/documentation</loc>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
</urlset>
"""
    return Response(content=xml, media_type="application/xml")
