# Learnwise

This repository contains the Learnwise projects:

- `learnwise-frontend/` — React/Vite application.
- `learnwise-backend/` — Django backend project.

## Backend setup (important)

Always activate the project virtual environment before running backend commands:

```powershell
Set-Location .\learnwise-backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

If the venv doesn't exist, create it first:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Configure `.env` (copy from `.env.example` if available) with at least:
- `DB_CONNECTION=mysql` (or `sqlite`)
- `USE_S3=True` for Supabase Storage (optional, defaults to local disk)

Run the frontend from its directory:

```powershell
Set-Location .\learnwise-frontend
npm install
npm run dev
```

The backend integration contract is documented in
`learnwise-frontend/docs/frontend-backend-contract.md`.
