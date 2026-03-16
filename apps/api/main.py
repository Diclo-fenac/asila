from fastapi import FastAPI

app = FastAPI(title="Asila API")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
