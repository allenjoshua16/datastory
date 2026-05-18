DataStory

AI‑augmented data storytelling that turns raw datasets into polished, executive‑ready narratives with charts.
Built on a multi‑agent pipeline powered by GPT‑4 and a modern web interface, DataStory lets you upload a file, choose an audience mode and receive an interactive report tailored to your needs.

Features
Upload & Privacy
File formats: Upload comma‑separated values or Excel workbooks (.csv, .xlsx, .xls, .xlsm) up to 200 MB.
Privacy by design: files are processed in‑session only and are not stored on the server.
Audience modes: choose among Executive, Analyst, Investor or General to tailor the narrative style.
Preprocessing options: decide whether to clean the data (fix missing values, remove duplicates, detect outliers, clean column names and extract date features) or analyze it as‑is.
Multi‑Agent Pipeline

When a dataset is uploaded, DataStory orchestrates a pipeline of GPT‑powered agents:

Upload – the raw file is received and optionally cleaned.
Data analysis – exploratory data analysis and metadata extraction.
Visualization generation – recommends appropriate chart types and specs.
Code generation ↔ execution – writes Plotly code, executes it in a sandbox and self‑corrects using a feedback loop that retries up to three times.
Story generation – drafts narrative summaries tailored to the selected audience.
Story execution – ranks and expands the narratives.
Report generation – compiles the narratives, charts and metadata into an interactive dashboard.

Users can monitor the job via a WebSocket stream or HTTP polling, and once complete they receive:

An interactive Dashboard with a metadata overview, chart gallery and narrative cards.
A downloadable cleaned CSV (when preprocessing is selected).
A full HTML report (static or in a new tab).
A live progress feed via WebSocket for real‑time status updates.
Architecture

The repository is split into a React/Vite front‑end and a FastAPI back‑end. Deployment is optimized for serverless hosting: the front‑end on Vercel and the back‑end as a Docker service on Render. The overall architecture looks like this:

frontend/   React + Vite + Tailwind → Vercel
backend/    FastAPI + 7 agents      → Render (Docker)

The agent pipeline flows from Upload → Data Analysis → Visualization Gen → Code Gen ↔ Code Exec → Story Gen → Story Exec → Report Gen.

Getting Started
Running Locally
Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Add your OPENAI_API_KEY to .env

uvicorn main:app --reload
# API at http://localhost:8000
# Docs at http://localhost:8000/docs
Frontend
cd frontend
npm install

cp .env.example .env.local
# Set VITE_API_URL=http://localhost:8000

npm run dev
# App at http://localhost:5173
Deployment
Backend → Render
Commit and push your code to GitHub.
Create a Web Service on render.com.
Point it at the backend/ folder and select the Docker runtime.
Set environment variables:
OPENAI_API_KEY – your OpenAI API key.
CORS_ORIGINS – the allowed front‑end origin (e.g. https://your-app.vercel.app).
OPENAI_MODEL – the model to use (default gpt-4o).
Frontend → Vercel
cd frontend
npx vercel
# During setup set VITE_API_URL = https://your-render-service.onrender.com
API Reference

The back‑end exposes a simple REST/WS API:

Method	Path	Description
POST	/api/upload	Upload a file and start a job
GET	/api/jobs/{id}/status	Poll the current job status
GET	/api/jobs/{id}/results	Fetch the final results
GET	/api/jobs/{id}/report	View the rendered HTML report
WS	/api/ws/{id}	Subscribe to live progress updates
Project Structure
datastory/
├── backend/
│   ├── agents/             # Orchestration and GPT agents (analysis, viz, code, story, report):contentReference[oaicite:12]{index=12}
│   ├── api/routes.py       # FastAPI endpoints
│   ├── core/               # Schemas, config, in‑memory job store:contentReference[oaicite:13]{index=13}
│   ├── templates/report.html.j2
│   ├── main.py
│   └── Dockerfile
└── frontend/
    ├── src/
    │   ├── components/     # UploadZone, PipelineProgress, StoryCard, ChartPanel:contentReference[oaicite:14]{index=14}
    │   ├── pages/Dashboard.jsx
    │   ├── hooks/useJob.js # WebSocket state management
    │   └── lib/api.js      # Axios client
    └── vercel.json
Extending
Add new agents: drop a Python file into backend/agents/ and register it in orchestrator.py.
Support new chart types: update the ChartType literal in schemas.py.
Introduce new audience modes: extend the AudienceMode literal in the back‑end and add a corresponding entry to AUDIENCE_OPTIONS in UploadZone.jsx.
Swap language model: change openai_model in your environment and update the OpenAI client used by each agent.
Production job store: replace the in‑memory job store (core/job_store.py) with a Redis‑backed implementation for horizontal scalability.
Contributing

Contributions are welcome! If you spot a bug, have a feature request or wish to improve the narrative models, feel free to open an issue or submit a pull request.

License

This project currently has no declared license in the repository. If you plan to extend or redistribute it, please contact the repository owner or add an appropriate license file.
