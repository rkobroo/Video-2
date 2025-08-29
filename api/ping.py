from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def ping():
    return {"status": "ok"}

handler = app

