from fastapi import FastAPI

app = FastAPI(title="PawPilot", version="0.0.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
