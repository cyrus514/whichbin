# Which Bin?

Upload a photo of trash, tick the bins you have, and get told where it goes.
Python (Flask) backend + Google Gemini for the photo recognition.

## 1. Get a free API key
1. Go to https://aistudio.google.com and sign in with a Google account.
2. Click "Get API key" and create one. Copy it. Never put it in the HTML or on GitHub.

## 2. Run it on your computer
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
export GEMINI_API_KEY="paste-key-here"   # Windows (PowerShell): $env:GEMINI_API_KEY="paste-key-here"
python app.py
```
Open http://127.0.0.1:5000

## 3. Put it online for free (Render)
1. Create a free account on https://github.com and upload this folder as a new repository.
   (`.gitignore` already keeps secrets out.)
2. Create a free account on https://render.com, click New > Web Service, and connect the repo.
3. Settings:
   - Runtime: Python
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`
   - Instance type: Free
4. Under Environment, add `GEMINI_API_KEY` with your key.
5. Deploy. You get a link like `https://which-bin.onrender.com`.
   Free instances sleep when idle, so the first visit can take about a minute.

## Optional settings (environment variables)
- `GEMINI_MODEL`: model name. Default is `gemini-3.6-flash`. If you see model errors,
  check the current name and free limits in AI Studio and update this.
- `MAX_REQUESTS_PER_HOUR`: photos per visitor per hour (default 20). Keeps you under the free quota.

## Custom domain
Buy a domain from any registrar, then add it in Render under Settings > Custom Domains
and follow the DNS instructions.
