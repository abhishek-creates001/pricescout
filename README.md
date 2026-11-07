# PriceScout

React (Vite) frontend + Python (Flask) backend.

## Run (two terminals in VS Code)

**Backend**
```
cd backend
python -m venv .venv
.venv\Scripts\activate        # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py                 # http://127.0.0.1:5000
```

**Frontend** (needs Node.js 18+)
```
cd frontend
npm install
npm run dev                   # http://localhost:5173
```
Open http://localhost:5173. Vite proxies /api to the Flask server.

## Going live
Add real store providers in `backend/app.py` (see `ApiProvider`) and append them to `PROVIDERS`.
