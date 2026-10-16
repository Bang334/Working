import urllib.request
import json

keys = [
    'AQ.Ab8RN6I9UkBtwBqGAQOYJoDpmOrlmbFIQrjtNpCWwo8I-TaoAw',
    'AQ.Ab8RN6J8SSHfE1F-bntNbQpm-TLVfEij9lBWzSGZmWTBK9HOxQ',
    'AIzaSyDIGsxjjDNtk6_fvp_fpPKFBX-etiimtv4'
]

models = [
    'gemini-3.8-flash',
    'gemini-3.7-flash',
    'gemini-3.5-flash',
    'gemini-2.5-flash',
    'gemini-2.5-flash-lite'
]

payload = {
    'contents': [{'parts': [{'text': 'Reply JSON with key message: ok'}]}],
    'generationConfig': {'temperature': 0.1, 'responseMimeType': 'application/json'}
}
body = json.dumps(payload).encode()

for k_idx, k in enumerate(keys):
    for m in models:
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={k}'
        req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode())
                txt = data['candidates'][0]['content']['parts'][0]['text']
                print(f"Key {k_idx} ({k[:10]}...) + {m} => SUCCESS: {txt.strip()}")
                break
        except urllib.error.HTTPError as e:
            print(f"Key {k_idx} + {m} => HTTP {e.code}")
        except Exception as e:
            print(f"Key {k_idx} + {m} => {type(e).__name__}")
