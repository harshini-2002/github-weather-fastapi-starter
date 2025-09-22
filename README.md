
# GitHub User & City Weather API (FastAPI)

Two simple GET endpoints powered by FastAPI:

- `GET /get_github_user?username=:username` → Returns selected fields from the GitHub Users API
- `GET /get_weather/:city` → Returns current weather (°C) for a city via OpenWeather

Port defaults to `3400` in the run command below.

---

## 1) Prerequisites

- **Python 3.10+**
- An **OpenWeather API key** (free). Put it in `.env` (see below).

> No GitHub token is required unless you hit unauthenticated rate limits.

---

## 2) Setup & Run

```bash
# 1) Clone or download this project, then cd into it
cd github-weather-fastapi-starter

# 2) (Recommended) Create and activate a virtual environment
python -m venv .venv
 .venv\Scripts\Activate.ps1

# 3) Install dependencies
pip install -r requirements.txt

# 4) Configure your OpenWeather API key
cp .env.example .env
# Edit .env and set OPENWEATHER_API_KEY=...

# 5) Run the API (port 3400)
uvicorn app.main:app --reload --port 3400
```

Now open http://localhost:3400/docs for interactive Swagger UI.

---

## 3) Endpoints & Examples

### A. GitHub User

```
GET http://localhost:3400/get_github_user?username=octocat
```

**Successful response (example):**
```json
{
  "login": "octocat",
  "name": "The Octocat",
  "public_repos": 8,
  "followers": 100,
  "following": 0
}
```

**Errors:**
- `404` if the user does not exist
- `429` if you exceed GitHub's unauthenticated rate limit
- Other GitHub API errors are surfaced with appropriate codes

### B. City Weather

```
GET http://localhost:3400/get_weather/London
```

**Successful response (example):**
```json
{
  "city": "London",
  "temperature": 13.5,
  "weather_description": "light rain"
}
```

**Errors:**
- `404` if the city is invalid / not found
- `502` for upstream or network errors to OpenWeather
- `500` if the API key is missing or the response shape was unexpected

---

## 4) How it works

- `/get_github_user` calls `https://api.github.com/users/{username}` and returns:
  `login`, `name`, `public_repos`, `followers`, `following`.
  - Handles `404` user not found.
  - Converts GitHub's rate limit `403` into `429` if the limit is exceeded.

- `/get_weather/:city` makes two calls to OpenWeather:
  1) **Geocoding** → `http://api.openweathermap.org/geo/1.0/direct?q={city}&appid={API_KEY}&limit=1`
  2) **Weather** → `https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units=metric&appid={API_KEY}`
  - Returns `city`, `temperature` (°C), and `weather_description`.
  - Robust error handling for bad city, missing key, or upstream issues.

---

## 5) Step-by-step: Create a new GitHub repo and push

### Option A — Using the GitHub website
1. Go to **https://github.com/new** and create a **Public** repo (e.g., `github-weather-fastapi-starter`). Do **not** add a README or .gitignore (we already have them).
2. Back in your terminal at the project root:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: FastAPI GitHub + Weather endpoints"
   git branch -M main
   git remote add origin https://github.com/<YOUR_USERNAME>/<YOUR_REPO>.git
   git push -u origin main
   ```

---

## 6) Quick testing (curl)

```bash
# GitHub user
curl "http://localhost:3400/get_github_user?username=octocat"

# Weather
curl "http://localhost:3400/get_weather/London"
```

---

## 7) Notes & Tips

- If you hit GitHub's unauthenticated rate limit, wait a bit and try again, or run with a token by exporting:
  ```bash
  export GITHUB_TOKEN=your_token  # (not required by this app, but you could add auth headers yourself)
  ```
- To change the port, modify the `uvicorn` command:
  ```bash
  uvicorn app.main:app --reload --port 8080
  ```

Happy building!
