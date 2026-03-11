# Manga Translator

A desktop batch processor for manga translation powered by local AI.

## Stack
- **Frontend**: Electron + React + Tailwind CSS
- **Backend**: Python 3.12 + FastAPI
- **Intelligence**: LM Studio (local LLM server)
- **Vision**: YOLOv10 + Manga-OCR
- **Art**: LaMa inpainting

## Project Structure

```
manga-translator/
├── .github/workflows/   # CI/CD pipelines
├── frontend/            # Electron + React UI
├── backend/             # Python FastAPI backend
├── shared/              # Shared schemas & types
└── docs/                # Architecture & design notes
```

## Getting Started

### Prerequisites
- Node.js 20+
- Python 3.12+
- LM Studio running on port 1234

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Development Workflow

| Branch | Purpose |
|--------|---------|
| `main` | Stable, always deployable |
| `dev` | Working branch, merges into main per phase |
| `feature/xxx` | Short-lived feature branches |

## Phases

- [x] **Phase 0** — Scaffolding & CI
- [ ] **Phase 1** — Project Management UI
- [ ] **Phase 2** — Vision Pipeline (OCR/Detection)
- [ ] **Phase 3** — Translation Worker (LM Studio)
- [ ] **Phase 4** — Art Worker (Inpainting/Typesetting)
- [ ] **Phase 5** — Review Gallery
- [ ] **Phase 6** — Hardening & Performance