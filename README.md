# Prompt vs Context

One question, four stages: **"Snacks sales ean drop aachu?"** (Why did Snacks sales drop?)

| Stage | What the AI gets | Result |
|---|---|---|
| 1 Weak prompt | Just the question | 🔴 Guess: "Market conditions-nala irukkalam." |
| 2 Better prompt | Role, task, format, rules. No data | 🟠 Honest, but stuck: "I don't know…" |
| 3 Right context | Same prompt + 3 sources | 🟢 Fact: promo ended 30 Sep 2026, Snacks dropped ~18% |
| 4 Too much context | Same prompt + all 50 tables | 🔴 Wrong table, wrong number (−30.7% from `sales_backup_2023`) |

## Run it

The demo is **frontend only**. All data and the 4 AI answers are saved as JSON in `frontend/public/data/`. No backend, no AI model, no API key.

```bash
cd frontend
npm install
npm run dev       # open http://localhost:5173
```

(or `./start.sh` from the project root)

## Deploy to Vercel

Import the repo in Vercel, set **Root Directory** to `frontend` (preset: Vite), and deploy.

## Regenerating the data (optional, only if you edit scenario.json)

The Python backend is only a tool to rebuild the JSON files. After editing `backend/data/scenario.json`:

```bash
cd backend
python scripts/seed.py            # rebuild the database
python scripts/captures.py status # check the captured answers still match
python scripts/export_static.py   # rewrite frontend/public/data/*.json
```

Backend setup (Python 3.11+). The venv lives on the Linux disk because `/mnt/c` is slow under WSL:

```bash
python3 -m venv ~/.venvs/contextweb
~/.venvs/contextweb/bin/pip install -r backend/requirements.txt
cd backend
~/.venvs/contextweb/bin/python scripts/seed.py      # builds data/demo.db (50 tables)
~/.venvs/contextweb/bin/uvicorn app.main:app --reload
```

Frontend (second terminal):

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173  (Vite proxies /api to :8000)
```

Tests: `cd backend && ~/.venvs/contextweb/bin/python -m pytest -q`

## How the AI answers work

The app never calls a model. Each stage's answer was **captured once** from an AI model (Claude) given the exact prompt + context that stage shows, and saved in `backend/data/captured_answers.json`. Each capture stores a fingerprint of its context. If the data changes, the capture is marked *stale* and the engine's own computed answer is shown instead.

Stage 3 and 4 numbers are always computed from SQLite with pandas. Nothing like "18%" is hardcoded.

## Change the sample data

Everything comes from **`backend/data/scenario.json`**: question, categories, prices, promo dates, uplift, decoy tables, report text, prompt text.

```bash
cd backend
python scripts/seed.py              # rebuild; fails loudly if the Snacks drop is not 17.5–18.5%
python scripts/captures.py status   # which captured answers still match the data
python scripts/captures.py export   # writes each stage's exact prompt + context to data/contexts/
python scripts/captures.py save 3 answer.txt   # store a new AI answer (keys: 1, 2, 3, 4:most_rows, 4:newest_dates)
```

To re-capture: export, paste `data/contexts/stage-3.txt` into an AI model, save its reply to a file, run `save`.

Stage 4 trap: the "biggest table" trap picks `sales_backup_2023`; the "newest dates" trap picks `sales_test`. Switch it in the UI on stage 4, or change `stage4.default_trap` in scenario.json.

## How to record the reel

1. Open the site (Vercel URL or `npm run dev`) in Chrome.
2. For 9:16, open DevTools device mode (Ctrl+Shift+M) and pick a phone such as 390×844, or use a narrow window.
3. Press **Space** to run a stage and wait for the badge. Press **→** for the next stage. Repeat for all 4.
4. Stage 4: let the 50-table dump finish so the red table shows.
5. Closing shot: click **Compare** to see all 4 answers side by side.
6. **Reset** starts over. Animations respect your system's reduce-motion setting.

## Structure

```
backend/
  app/        main.py (API) · engine.py (one function per stage) · models.py (Pydantic) · db.py
              captures.py (captured answers) · metrics.py (the before/after calculation) · scenario.py
  data/       scenario.json (edit me) · captured_answers.json · demo.db (generated)
  scripts/    seed.py · captures.py
  tests/      seed, engine and API tests
frontend/src/ api/ (typed client) · components/ · hooks/ · styles/
```
