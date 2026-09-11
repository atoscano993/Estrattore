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
    target_url = f"https://dlive.sx/stream-{stream_id}.php"
    print(f"--> [1] Invio richiesta a: {target_url}")
    
    try:
        res = requests.get(target_url, headers=HEADERS, timeout=8)
        print(f"--> [2] Risposta ricevuta da dlive, Status Code: {res.status_code}")
        
        if res.status_code != 200:
            print(f"--> [ERRORE] dlive.sx ha risposto con codice {res.status_code} (probabile blocco Cloudflare/IP Render)")
            return None

        # Cerca il link m3u8 diretto nell'HTML
        match = re.search(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', res.text)
        if match:
            found_url = match.group(0)
            print(f"--> [3] Trovato m3u8 diretto: {found_url}")
            return found_url
        
        # Cerca link dell'iframe se non lo trova subito
        iframe_match = re.search(r'src=["\']([^"\']+)["\']', res.text)
        if iframe_match:
            iframe_url = iframe_match.group(1)
            if iframe_url.startswith('//'):
                iframe_url = 'https:' + iframe_url
            elif iframe_url.startswith('/'):
                iframe_url = 'https://dlive.sx' + iframe_url
                
            print(f"--> [3] Trovato iframe: {iframe_url}. Provo ad analizzarlo...")
            res_iframe = requests.get(iframe_url, headers={"User-Agent": HEADERS["User-Agent"], "Referer": target_url}, timeout=8)
            
            m3u8_match = re.search(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', res_iframe.text)
            if m3u8_match:
                found_url = m3u8_match.group(0)
                print(f"--> [4] Trovato m3u8 dentro iframe: {found_url}")
                return found_url

        print("--> [ERRORE] Nessun link .m3u8 trovato nell'HTML o nell'iframe")

    except Exception as e:
        print(f"--> [EXCEPTION ERROR] ID {stream_id}: {e}")
        
    return None

@app.after_request
def add_header(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['ngrok-skip-browser-warning'] = 'true'
    return response

@app.route('/')
def home():
    return "Proxy DLive attivo.", 200

@app.route('/<path:channel_name>')
def get_stream(channel_name):
    # Pulisce la richiesta togliendo .m3u8 e slash finali
    name_clean = channel_name.replace(".m3u8", "").replace("/", "").lower()
    print(f"\n--- Nuova richiesta per canale: {name_clean} ---")

    if name_clean in AUTOMATIC_CHANNELS:
        dlive_id = AUTOMATIC_CHANNELS[name_clean]
        stream_url = resolve_dlive_stream(dlive_id)
        
        if stream_url:
            print(f"--> [SUCCESS] Redirecting a {stream_url}")
            return redirect(stream_url, code=302)
        else:
            print("--> [FAIL] Chiamata fallita, restituisco 502")
            return f"Impossibile estrarre lo stream per '{channel_name}'", 502

    print(f"--> [FAIL] Canale {name_clean} non presente nella lista")
    return f"Canale '{channel_name}' non trovato", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
