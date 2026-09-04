import re
import requests
from flask import Flask, redirect

app = Flask(__name__)

# --- MAPPA CANALI DIRETTI TVNOW ---
TVNOW_MAP = {
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

HEADERS_TVNOW = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://tvnow247.top/",
    "Origin": "https://tvnow247.top"
}

HEADERS_HTSPORT = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://htsport.org/",
    "Origin": "https://htsport.org"
}


# --- 1. ROTTA PRINCIPALE VELOCE (TVNOW Diretta) ---
@app.route('/<channel_name>.m3u8')
def get_stream(channel_name):
    name_clean = channel_name.lower()
    
    # Cerca l'ID nel dizionario o verifica se l'URL contiene direttamente un ID numerico
    if name_clean in TVNOW_MAP or name_clean.isdigit():
        stream_id = TVNOW_MAP.get(name_clean, channel_name)
        try:
            api_url = f"https://chat.cfbu247.sbs/api/resolve-dlstream/{stream_id}"
            response = requests.get(api_url, headers=HEADERS_TVNOW, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                stream_url = data.get("m3u8") or data.get("proxyPlaylistUrl")
                if stream_url:
                    return redirect(stream_url, code=302)
            else:
                print(f"Errore HTTP TVNOW: {response.status_code}")
        except Exception as e:
            print(f"Errore TVNOW: {e}")

    return f"Flusso TVNow per il canale '{channel_name}' non disponibile", 404


# --- 2. ROTTA DIRETTA PER ID TVNOW ---
@app.route('/tvnow/<channel_id>.m3u8')
def get_tvnow_by_id(channel_id):
    try:
        api_url = f"https://chat.cfbu247.sbs/api/resolve-dlstream/{channel_id}"
        response = requests.get(api_url, headers=HEADERS_TVNOW, timeout=10)
        if response.status_code == 200:
            data = response.json()
            stream_url = data.get("m3u8") or data.get("proxyPlaylistUrl")
            if stream_url:
                return redirect(stream_url, code=302)
        return "Canale TVNOW non trovato", 404
    except Exception as e:
        return f"Errore server: {e}", 500


# --- 3. ROTTA DINAMICA HTSPORT (Scraping automatico TVNOW dalla pagina) ---
@app.route('/htsport/<page_name>.m3u8')
def get_htsport_dynamic(page_name):
    try:
        target_url = f"https://htsport.org/{page_name}.htm"
        page_resp = requests.get(target_url, headers=HEADERS_HTSPORT, timeout=7)
        
        if page_resp.status_code != 200:
            return f"Pagina {target_url} non trovata", 404
            
        html = page_resp.text

        # Cerca l'ID TVNow presente nel codice della pagina di HTSport
        match_tvnow = re.search(r'resolve-dlstream/(\d+)', html)
        if match_tvnow:
            stream_id = match_tvnow.group(1)
            api_url = f"https://chat.cfbu247.sbs/api/resolve-dlstream/{stream_id}"
            resp = requests.get(api_url, headers=HEADERS_TVNOW, timeout=5)
            if resp.status_code == 200:
                stream_url = resp.json().get("m3u8") or resp.json().get("proxyPlaylistUrl")
                if stream_url:
                    return redirect(stream_url, code=302)

        return "Nessun player TVNow trovato nella pagina", 404

    except Exception as e:
        return f"Errore Dynamic: {e}", 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
