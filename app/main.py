
from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Path
from pydantic import BaseModel
import httpx

try:
    # Load .env if present (no-op if file missing)
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # dotenv is optional; ignoring import issues if not installed
    pass


class GitHubUserResponse(BaseModel):
    login: str
    name: Optional[str] = None
    public_repos: int
    followers: int
    following: int


class WeatherResponse(BaseModel):
    city: str
    temperature: float
    weather_description: str


app = FastAPI(title="GitHub User & City Weather API", version="1.0.0")


@app.on_event("startup")
async def _startup() -> None:
    # Reuse a single client across requests for performance
    app.state.client = httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, connect=5.0, read=10.0),
        headers={
            "User-Agent": "github-weather-fastapi-example/1.0",
            "Accept": "application/vnd.github+json",
        },
        follow_redirects=True,
    )


@app.on_event("shutdown")
async def _shutdown() -> None:
    try:
        await app.state.client.aclose()
    except Exception:
        pass


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.get("/get_github_user", response_model=GitHubUserResponse)
async def get_github_user(username: str = Query(..., min_length=1, description="GitHub username")):
    """
    GET /get_github_user?username=:username
    Calls GitHub Users API and returns a subset of fields.
    Error handling:
      - 404 if user not found
      - 429 if rate limit exceeded
    """
    url = f"https://api.github.com/users/{username}"
    try:
        r = await app.state.client.get(url)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Network error talking to GitHub: {e}") from e

    # Handle common error shapes
    if r.status_code == 404:
        raise HTTPException(status_code=404, detail="GitHub user not found")

    if r.status_code == 403:
        remaining = r.headers.get("X-RateLimit-Remaining")
        msg = ""
        try:
            msg = (r.json().get("message") or "").lower()
        except Exception:
            pass
        if remaining == "0" or "rate limit" in msg:
            raise HTTPException(status_code=429, detail="GitHub API rate limit exceeded. Try again later or add a token.")
        # Some other 403
        raise HTTPException(status_code=403, detail="GitHub API returned 403 Forbidden.")

    if r.is_error:
        raise HTTPException(status_code=r.status_code, detail=f"GitHub API error ({r.status_code}).")

    data = r.json()
    try:
        return GitHubUserResponse(
            login=data.get("login"),
            name=data.get("name"),
            public_repos=int(data.get("public_repos", 0)),
            followers=int(data.get("followers", 0)),
            following=int(data.get("following", 0)),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected response shape from GitHub: {e}") from e


@app.get("/get_weather/{city}", response_model=WeatherResponse)
async def get_weather(city: str = Path(..., description="City name (e.g., London)")):
    """
    GET /get_weather/:city
    Uses OpenWeather to geocode the city to coordinates, then fetches current weather.
    Returns temperature in Celsius.
    Error handling:
      - 404 if city invalid
      - 5xx for upstream API/network issues
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OpenWeather API key not configured. Set OPENWEATHER_API_KEY env var or .env file.",
        )

    # 1) Geocode city -> lat/lon
    geocode_url = "http://api.openweathermap.org/geo/1.0/direct"
    params = {"q": city, "appid": api_key, "limit": 1}
    try:
        geo_resp = await app.state.client.get(geocode_url, params=params)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Network error talking to OpenWeather Geocoding API: {e}") from e

    if geo_resp.is_error:
        raise HTTPException(status_code=geo_resp.status_code, detail="OpenWeather geocoding API error.")

    places = geo_resp.json()
    if not isinstance(places, list) or len(places) == 0:
        raise HTTPException(status_code=404, detail="Invalid city name or city not found.")

    first = places[0]
    lat = first.get("lat")
    lon = first.get("lon")
    resolved_name = first.get("name") or city

    if lat is None or lon is None:
        raise HTTPException(status_code=502, detail="Geocoding returned no coordinates.")

    # 2) Current weather using lat/lon
    weather_url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"lat": lat, "lon": lon, "appid": api_key, "units": "metric"}
    try:
        w_resp = await app.state.client.get(weather_url, params=params)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Network error talking to OpenWeather Weather API: {e}") from e

    if w_resp.is_error:
        raise HTTPException(status_code=w_resp.status_code, detail="OpenWeather weather API error.")

    payload = w_resp.json()
    try:
        temp_c = float(payload["main"]["temp"])
        description = str(payload["weather"][0]["description"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected response shape from OpenWeather: {e}") from e

    return WeatherResponse(city=resolved_name, temperature=temp_c, weather_description=description)
