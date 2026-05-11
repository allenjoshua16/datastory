# DataStory

AI-augmented data storytelling — turns raw datasets into executive-ready narratives with charts, powered by GPT-4 and a multi-agent pipeline.

---

## Architecture

```
frontend/   React + Vite + Tailwind → Vercel
backend/    FastAPI + 7 agents      → Render (Docker)
```

**Agent pipeline:**

```
Upload → Data Analysis → Visualization Gen → Code Gen ⟷ Code Exec → Story Gen → Story Exec → Report Gen
```

The Code Gen ↔ Code Exec feedback loop retries up to 3 times, feeding execution errors back into the LLM to self-correct.

---

## Local Development

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Add your OPENAI_API_KEY to .env

uvicorn main:app --reload
# API at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install

cp .env.example .env.local
# Set VITE_API_URL=http://localhost:8000

npm run dev
# App at http://localhost:5173
```

---

## Deploy

### Backend → Render

1. Push to GitHub
2. Create a new **Web Service** on [render.com](https://render.com)
3. Point to the `backend/` folder, select **Docker** runtime
4. Set environment variables:
   - `OPENAI_API_KEY` — your key
   - `CORS_ORIGINS` — `https://your-app.vercel.app`
   - `OPENAI_MODEL` — `gpt-4o`

### Frontend → Vercel

```bash
cd frontend
npx vercel
# Set VITE_API_URL = https://your-render-service.onrender.com
```

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/upload` | Upload file, start pipeline |
| GET | `/api/jobs/{id}/status` | Poll job status |
| GET | `/api/jobs/{id}/results` | Fetch final results |
| GET | `/api/jobs/{id}/report` | View HTML report |
| WS | `/api/ws/{id}` | Live progress stream |

---

## Project Structure

```
datastory/
├── backend/
│   ├── agents/
│   │   ├── orchestrator.py     # Coordinates all agents
│   │   ├── data_analysis.py    # EDA + metadata
│   │   ├── visualization_gen.py # Chart recommendations
│   │   ├── code_gen.py         # Plotly code writer
│   │   ├── code_exec.py        # Sandbox runner + feedback loop
│   │   ├── story_gen.py        # Narrative ideas
│   │   ├── story_exec.py       # Rank + expand stories
│   │   └── report_gen.py       # Jinja2 HTML report
│   ├── api/routes.py           # FastAPI endpoints
│   ├── core/
│   │   ├── schemas.py          # Pydantic models
│   │   ├── config.py           # Settings
│   │   └── job_store.py        # In-memory job state + WebSocket pub/sub
│   ├── templates/report.html.j2
│   ├── main.py
│   └── Dockerfile
└── frontend/
    ├── src/
    │   ├── components/         # UploadZone, PipelineProgress, StoryCard, ChartPanel
    │   ├── pages/Dashboard.jsx
    │   ├── hooks/useJob.js     # WebSocket state management
    │   └── lib/api.js          # Axios client
    └── vercel.json
```

---

## Extending

- **New agent**: Add a file to `backend/agents/`, call it from `orchestrator.py`
- **New chart type**: Add to `ChartType` literal in `schemas.py`
- **New audience mode**: Add to `AudienceMode` literal and `AUDIENCE_OPTIONS` in `UploadZone.jsx`
- **Swap LLM**: Change `openai_model` in `.env`; update client in any agent
- **Production job store**: Replace `core/job_store.py` with a Redis-backed implementation
