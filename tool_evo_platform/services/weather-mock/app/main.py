from typing import Optional

from fastapi import FastAPI, Query

app = FastAPI(title="Weather Mock Service")


@app.get("/weather")
async def get_weather(
    city: str = Query(...),
    country: Optional[str] = Query(None),
):
    """
    Dummy weather endpoint for testing the Tool Gateway.
    """
    desc_parts = [f"Fake sunny weather in {city}"]
    if country:
        desc_parts.append(f"({country})")
    description = " ".join(desc_parts)

    return {
        "temperatureC": 26.5,
        "description": description,
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
