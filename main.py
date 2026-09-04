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


# --- 3. ROTTA DINAMICA HTSPORT (UNIVERSALE PER TVNOW & WIDEIPTV) ---
@app.route('/htsport/<page_name>.m3u8')
def get_htsport_dynamic(page_name):
    try:
        target_url = f"https://htsport.org/{page_name}.htm"
        page_resp = requests.get(target_url, headers=HEADERS_HTSPORT, timeout=10)
        
        if page_resp.status_code != 200:
            return f"Pagina {target_url} non trovata (HTTP {page_resp.status_code})", 404
            
        html = page_resp.text

        # 1. CASO A: Il player è TVNow/CFBU
        match_tvnow = re.search(r'(?:resolve-dlstream/|id=)(\d+)', html)
        if match_tvnow:
            stream_id = match_tvnow.group(1)
            api_url = f"https://chat.cfbu247.sbs/api/resolve-dlstream/{stream_id}"
            resp = requests.get(api_url, headers=HEADERS_TVNOW, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                stream_url = data.get("m3u8") or data.get("proxyPlaylistUrl")
                if stream_url:
                    return redirect(stream_url, code=302)

        # 2. CASO B: Il player è WideIPTV
        match_wide = re.search(r'src=["\'](https?://wideiptv\.top/player/[^"\']+)["\']', html)
        if match_wide:
            player_url = match_wide.group(1)
            player_resp = requests.get(player_url, headers=HEADERS_HTSPORT, timeout=10)
            if player_resp.status_code == 200:
                match_stream = re.search(r'streamUrl:\s*["\']([^"\']+)["\']', player_resp.text)
                if match_stream:
                    stream_url = match_stream.group(1).replace(r'\/', '/')
                    return redirect(stream_url, code=302)

        # 3. CASO C: Iframe generico
        iframe_src = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if iframe_src:
            sub_url = iframe_src.group(1)
            if not sub_url.startswith("http"):
                sub_url = f"https://htsport.org/{sub_url.lstrip('/')}"
            
            sub_resp = requests.get(sub_url, headers=HEADERS_HTSPORT, timeout=10)
            if sub_resp.status_code == 200:
                match_sub_tvnow = re.search(r'resolve-dlstream/(\d+)', sub_resp.text)
                if match_sub_tvnow:
                    stream_id = match_sub_tvnow.group(1)
                    api_url = f"https://chat.cfbu247.sbs/api/resolve-dlstream/{stream_id}"
                    resp = requests.get(api_url, headers=HEADERS_TVNOW, timeout=10)
                    if resp.status_code == 200:
                        data = resp.json()
                        stream_url = data.get("m3u8") or data.get("proxyPlaylistUrl")
                        if stream_url:
                            return redirect(stream_url, code=302)

        return "Nessun player compatibile estratto dalla pagina HTSport", 404

    except Exception as e:
        return f"Errore Dynamic: {e}", 500


# --- 4. ROTTA DI DEBUG TEMPORANEA ---
@app.route('/debug/<page_name>')
def debug_page(page_name):
    try:
        url = f"https://htsport.org/{page_name}.htm"
        resp = requests.get(url, headers=HEADERS_HTSPORT, timeout=10)
        return f"<h3>Status Code: {resp.status_code}</h3><textarea style='width:100%;height:500px;'>{resp.text}</textarea>"
    except Exception as e:
        return f"Errore: {e}"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
