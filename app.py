import json
import os
import time
from collections import defaultdict, deque

from flask import Flask, jsonify, request, send_from_directory
from google import genai
from google.genai import types
from werkzeug.middleware.proxy_fix import ProxyFix

# --- Settings (change via environment variables) ---
API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
FALLBACK_MODEL = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash")
MAX_REQUESTS_PER_HOUR = int(os.environ.get("MAX_REQUESTS_PER_HOUR", "20"))
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
VALID_BINS = {"recycling", "paper", "glass", "compost", "landfill", "dropoff"}

app = Flask(__name__, static_folder="static")
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
app.config["MAX_CONTENT_LENGTH"] = 6 * 1024 * 1024

client = (
    genai.Client(api_key=API_KEY, http_options=types.HttpOptions(timeout=12000))
    if API_KEY
    else None
)
hits = defaultdict(deque)

PROMPT = """You are a waste-sorting helper. Look at the attached photo and identify the single main item to throw away.
Reply with ONLY JSON, no markdown:
{"item":"short name","material":"what it is made of","ranked_bins":["best","next best"],"explanation":"one or two plain sentences","tip":"optional prep tip like rinse or remove cap, or empty string"}
ranked_bins must use only these ids, best first, ending with "landfill" as the last resort: recycling, paper, glass, compost, landfill, dropoff.
Rules: clean paper/cardboard -> paper then recycling. Food-soiled paper -> compost then landfill. Candy/chip wrappers, plastic film and multi-layer foil wrappers are usually landfill. Batteries and electronics -> dropoff. If unsure, say so in the explanation. If no trash item is visible, set item to "Nothing recognised" and ranked_bins to ["landfill"]."""


def too_many(ip):
    now = time.time()
    q = hits[ip]
    while q and now - q[0] > 3600:
        q.popleft()
    if len(q) >= MAX_REQUESTS_PER_HOUR:
        return True
    q.append(now)
    return False


def ask_ai(image_part):
    """Try the main model, then the backup model. Returns parsed JSON or raises."""
    models = [MODEL]
    if FALLBACK_MODEL and FALLBACK_MODEL != MODEL:
        models.append(FALLBACK_MODEL)
    last_error = None
    for name in models:
        try:
            resp = client.models.generate_content(
                model=name,
                contents=[image_part, PROMPT],
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            return json.loads(resp.text)
        except Exception as e:
            last_error = e
            app.logger.warning("Model %s failed: %s", name, e)
    raise last_error


@app.get("/")
def home():
    return send_from_directory("static", "index.html")


@app.post("/api/identify")
def identify():
    if client is None:
        return jsonify(error="Server is missing GEMINI_API_KEY."), 500
    if too_many(request.remote_addr):
        return jsonify(error="Too many photos this hour. Try again later."), 429

    f = request.files.get("photo")
    if not f or f.mimetype not in ALLOWED_TYPES:
        return jsonify(error="Please upload a JPEG, PNG or WebP photo."), 400

    try:
        image_part = types.Part.from_bytes(data=f.read(), mime_type=f.mimetype)
        data = ask_ai(image_part)
    except Exception as e:
        app.logger.exception("Gemini call failed: %s", e)
        return jsonify(error="The AI is busy right now. Please try again in a minute."), 502

    ranked = [b for b in data.get("ranked_bins", []) if b in VALID_BINS] or ["landfill"]
    return jsonify(
        item=str(data.get("item", "item"))[:80],
        material=str(data.get("material", ""))[:80],
        ranked_bins=ranked,
        explanation=str(data.get("explanation", ""))[:400],
        tip=str(data.get("tip", ""))[:300],
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
