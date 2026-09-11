import os
import requests
from flask import Flask, redirect

app = Flask(__name__)

# Header catturati direttamente dal DevTools del browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
    "Referer": "https://barecrop.net/",
    "Origin": "https://barecrop.net"
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
    """Chiama l'API JSON diretta del player per evitare i blocchi web"""
    print(f"--> Avvio risoluzione per ID: {stream_id}")
    
    # Endpoint API dell'infrastruttura di riproduzione
    api_url = f"https://chat.cfbu247.sbs/api/resolve-dlstream/{stream_id}"
    
    try:
        # Timeout rigido di 3 secondi per evitare il 502 di Render
        response = requests.get(api_url, headers=HEADERS, timeout=3)
        print(f"--> Risposta API Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            # Estrae l'URL m3u8 dal JSON di risposta
            stream_url = data.get("m3u8") or data.get("proxyPlaylistUrl") or data.get("url")
            print(f"--> Stream trovato: {stream_url}")
            return stream_url
        else:
            print(f"--> Errore API: Status {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("--> TIMEOUT: L'API ha impiegato più di 3 secondi")
    except Exception as e:
        print(f"--> ERRORE Chiamata API: {e}")
        
    return None

@app.after_request
def add_header(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['ngrok-skip-browser-warning'] = 'true'
    return response

@app.route('/')
def home():
    return "Proxy DLive API attivo.", 200

@app.route('/<path:channel_name>')
def get_stream(channel_name):
    # Pulisce la richiesta rimuovendo slashes ed estensioni
    name_clean = channel_name.replace(".m3u8", "").replace("/", "").lower()
    print(f"\n[RICHIESTA] Canale: {name_clean}")

    if name_clean in AUTOMATIC_CHANNELS:
        dlive_id = AUTOMATIC_CHANNELS[name_clean]
        stream_url = resolve_dlive_stream(dlive_id)
        
        if stream_url:
            print(f"[ESITO] Redirect a -> {stream_url}")
            return redirect(stream_url, code=302)
        else:
            print("[ESITO] Impossibile ottenere il link stream")
            return f"Errore nell'estrazione dello stream per {channel_name}", 502

    print(f"[ESITO] Canale {name_clean} non in lista")
    return f"Canale '{channel_name}' non trovato", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
