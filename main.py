import os
import re
import requests
from flask import Flask, redirect, request

app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
    "Referer": "https://dlive.sx/"
}

# Mappatura Canali
AUTOMATIC_CHANNELS = {
    "sport24": "869",
    "sportuno": "461",
    "sportcalcio": "870",
    "sportf1": "577",
    "sportmoto": "575",
    "sportmax": "460",
    "sporttennis": "576",
    "sportarena": "462",
    "dazn1": "877"
}

def resolve_dlive_stream(stream_id):
    """Estrae l'URL m3u8 direttamente dalla pagina dello stream dlive"""
    try:
        # Step 1: Chiamata a stream-ID.php
        target_url = f"https://dlive.sx/stream-{stream_id}.php"
        res = requests.get(target_url, headers=HEADERS, timeout=5)
        
        if res.status_code == 200:
            # Cerca qualsiasi URL m3u8 presente nel codice HTML/JS
            match = re.search(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', res.text)
            if match:
                return match.group(0)
            
            # Step 2: Se c'è un iframe (es. barecrop), estrae il link del player
            iframe_match = re.search(r'src=["\']([^"\']+)["\']', res.text)
            if iframe_match:
                iframe_url = iframe_match.group(1)
                if iframe_url.startswith('//'):
                    iframe_url = 'https:' + iframe_url
                
                # Legge l'iframe per trovare l'm3u8
                res_iframe = requests.get(iframe_url, headers={"User-Agent": HEADERS["User-Agent"], "Referer": target_url}, timeout=5)
                m3u8_match = re.search(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', res_iframe.text)
                if m3u8_match:
                    return m3u8_match.group(0)

    except Exception as e:
        print(f"[DLIVE SCRAPE ERROR] ID {stream_id}: {e}")
    return None

@app.after_request
def add_header(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['ngrok-skip-browser-warning'] = 'true'
    return response

@app.route('/')
def home():
    return "Proxy DLive (Direct Scrape) attivo.", 200

@app.route('/<channel_name>')
def get_stream(channel_name):
    name_clean = channel_name.replace(".m3u8", "").lower()

    if name_clean in AUTOMATIC_CHANNELS:
        dlive_id = AUTOMATIC_CHANNELS[name_clean]
        stream_url = resolve_dlive_stream(dlive_id)
        
        if stream_url:
            print(f"[SUCCESS] {name_clean} -> {stream_url}")
            return redirect(stream_url, code=302)
        else:
            return f"Impossibile estrarre lo stream per '{channel_name}'", 502

    return f"Canale '{channel_name}' non trovato", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
