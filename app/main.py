from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import ROOT_DIR
from app.routers.analyze import router as analyze_router


STATIC_DIR = ROOT_DIR / "static"


def create_app() -> FastAPI:
    application = FastAPI(
        title="Нейро-помощник Авито",
        description="MVP: анализ скриншотов объявления через OpenAI Responses API",
    )

    application.include_router(analyze_router, prefix="/api")

    if STATIC_DIR.is_dir():
        application.mount(
            "/static",
            StaticFiles(directory=str(STATIC_DIR)),
            name="static",
        )

    @application.get("/")
    async def index_page():
        index_path = STATIC_DIR / "index.html"
        if not index_path.is_file():
            raise HTTPException(status_code=404, detail="Страница не найдена.")
        return FileResponse(index_path)

    return application


app = create_app()
