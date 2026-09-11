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
        target_url = f"https://dlive.sx/stream-{stream_id}.php"
        print(f"[DEBUG] Richiesta a: {target_url}")
        
        res = requests.get(target_url, headers=HEADERS, timeout=8)
        print(f"[DEBUG] Status Code: {res.status_code}")
        print(f"[DEBUG] Primi 300 caratteri risposta: {res.text[:300]}")
        
        if res.status_code == 200:
            # 1. Cerca direttamente l'm3u8
            match = re.search(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', res.text)
            if match:
                return match.group(0)
            
            # 2. Cerca eventuali iframe nell'HTML
            iframe_matches = re.findall(r'src=["\']([^"\']+)["\']', res.text)
            print(f"[DEBUG] Iframe trovati: {iframe_matches}")
            
            for iframe_url in iframe_matches:
                if "http" not in iframe_url:
                    if iframe_url.startswith('//'):
                        iframe_url = 'https:' + iframe_url
                    elif iframe_url.startswith('/'):
                        iframe_url = 'https://dlive.sx' + iframe_url
                    else:
                        iframe_url = 'https://dlive.sx/' + iframe_url

                print(f"[DEBUG] Analizzo iframe: {iframe_url}")
                try:
                    res_iframe = requests.get(iframe_url, headers={"User-Agent": HEADERS["User-Agent"], "Referer": target_url}, timeout=8)
                    m3u8_match = re.search(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', res_iframe.text)
                    if m3u8_match:
                        return m3u8_match.group(0)
                except Exception as err_iframe:
                    print(f"[DEBUG] Errore iframe {iframe_url}: {err_iframe}")

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
