from fastapi import FastAPI

app = FastAPI(title="Enterprise AI-SDLC Template")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
