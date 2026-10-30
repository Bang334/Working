import urllib.request
import urllib.error
import json

import os
from pathlib import Path

# Load keys safely from database/local_gemini_keys.json or environment
_keys_path = Path(__file__).resolve().parent.parent / "database" / "local_gemini_keys.json"
keys = []
if _keys_path.exists():
    try:
        keys = json.loads(_keys_path.read_text(encoding="utf-8"))
    except Exception:
        keys = []

if not keys and os.environ.get("GEMINI_API_KEY"):
    keys = [os.environ["GEMINI_API_KEY"]]

models = [
    'gemini-3.5-flash',
    'gemini-3.5-flash-lite',
    'gemini-2.5-flash',
    'gemini-2.5-flash-lite',
    'gemini-3.1-flash-lite',
    'gemini-flash-lite-latest'
]

payload = {
    'contents': [{'parts': [{'text': 'Reply JSON with key message: ok'}]}],
    'generationConfig': {'temperature': 0.1, 'responseMimeType': 'application/json'}
}
body = json.dumps(payload).encode()

for k_idx, k in enumerate(keys):
    print(f"\n--- Testing Key {k_idx + 1} ({k[:15]}...{k[-6:]}) ---")
    for m in models:
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={k}'
        req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                txt = data['candidates'][0]['content']['parts'][0]['text']
                print(f"  + Model {m} => SUCCESS: {txt.strip()}")
        except urllib.error.HTTPError as e:
            print(f"  - Model {m} => HTTP {e.code}")
        except Exception as e:
            print(f"  - Model {m} => {type(e).__name__}: {e}")
