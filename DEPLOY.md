# Deployment Guide — 3 Steps to Live

## Step 1 — Supabase (Database)

1. Go to https://supabase.com → New Project → name it `coolshift`
2. Once created, go to **SQL Editor** → paste contents of `supabase/migrations/001_initial.sql` → Run
3. Paste `supabase/migrations/002_views.sql` → Run
4. Go to **Settings → API** → copy:
   - `Project URL` → your `SUPABASE_URL`
   - `anon public` key → your `SUPABASE_ANON_KEY`

---

## Step 2 — Backend on Railway (Python API)

1. Go to https://railway.app → New Project → Deploy from GitHub repo
2. Select the `coolshift/backend` folder (or push only `backend/` as a separate repo)
3. Railway auto-detects the Dockerfile
4. Add environment variable: `ALLOWED_ORIGINS=https://your-vercel-app.vercel.app`
5. Deploy → copy the Railway public URL (e.g. `https://coolshift-api.up.railway.app`)

---

## Step 3 — Frontend on Vercel (Next.js)

1. Go to https://vercel.com → New Project → import from GitHub
2. Select the `coolshift/frontend` folder
3. Add **Environment Variables**:
   ```
   NEXT_PUBLIC_API_URL = https://coolshift-api.up.railway.app
   NEXT_PUBLIC_SUPABASE_URL = https://xxxx.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY = eyJhbGciOi...
   ```
4. Deploy → your app is live at `https://coolshift.vercel.app`

---

## Local Dev (no cloud needed)

```bash
# Terminal 1 — Backend
cd backend
venv\Scripts\activate        # Windows
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm run dev                  # http://localhost:3000
```

## Verify Everything Works

1. Open `http://localhost:3000`
2. Upload `04_CoolShift_Public_Dataset_and_Templates.xlsx`
3. Select scenario `PUB-A`, days `7`
4. Click **Run Optimization**
5. Should see dashboard with cost savings, charts, comfort compliance
6. Click Export → download CSV (672 rows for 7 days × 96 intervals)
7. Go to Export tab → Generate Custom Scenario (pulls live Karachi weather)
