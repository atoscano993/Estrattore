import re
import os
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

@app.route('/')
def home():
    return "Estrattore attivo", 200

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

# --- 3. ROTTA DINAMICA HTSPORT (CON DECODER PER DAZN1HD) ---
@app.route('/htsport/<page_name>.m3u8')
def get_htsport_dynamic(page_name):
    try:
        clean_page = page_name.replace(".m3u8", "")
        target_url = f"https://htsport.org/{clean_page}.htm"
        
        session = requests.Session()
        session.headers.update(HEADERS_HTSPORT)
        
        page_resp = session.get(target_url, timeout=10)
        if page_resp.status_code != 200:
            return f"Pagina {target_url} non trovata (HTTP {page_resp.status_code})", 404
            
        html = page_resp.text

        # Cerca ID TVNow
        match_tvnow = re.search(r'(?:resolve-dlstream/|id=)(\d+)', html)
        if match_tvnow:
            stream_id = match_tvnow.group(1)
            api_url = f"https://chat.cfbu247.sbs/api/resolve-dlstream/{stream_id}"
            resp = session.get(api_url, headers=HEADERS_TVNOW, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                stream_url = data.get("m3u8") or data.get("proxyPlaylistUrl")
                if stream_url:
                    return redirect(stream_url, code=302)

        # Cerca IFRAME
        iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if not iframes:
            iframes = re.findall(r'(?:src|href)=["\']([^"\']*(?:embed|player|frame|live)[^"\']*)["\']', html, re.IGNORECASE)

        for iframe_src in iframes:
            if iframe_src.startswith("//"):
                sub_url = f"https:{iframe_src}"
            elif not iframe_src.startswith("http"):
                sub_url = f"https://htsport.org/{iframe_src.lstrip('/')}"
            else:
                sub_url = iframe_src

            try:
                sub_headers = HEADERS_HTSPORT.copy()
                sub_headers["Referer"] = target_url
                sub_resp = session.get(sub_url, headers=sub_headers, timeout=8)
                
                if sub_resp.status_code == 200:
                    sub_text = sub_resp.text
                    
                    # 1. m3u8 in chiaro
                    match_m3u8 = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', sub_text)
                    if match_m3u8:
                        return redirect(match_m3u8.group(1).replace(r'\/', '/'), code=302)

                    # 2. Decodifica Hex per Clappr (Dazn1HD)
                    hex_matches = re.findall(r'["\']([0-9a-fA-F]{30,})["\']', sub_text)
                    for hex_str in hex_matches:
                        try:
                            decoded = bytes.fromhex(hex_str).decode('utf-8', errors='ignore')
                            match_dec_m3u8 = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', decoded)
                            if match_dec_m3u8:
                                return redirect(match_dec_m3u8.group(1).replace(r'\/', '/'), code=302)
                        except Exception:
                            continue

                    # 3. ID TVNow nidificato
                    match_sub_tvnow = re.search(r'(?:resolve-dlstream/|id=)(\d+)', sub_text)
                    if match_sub_tvnow:
                        stream_id = match_sub_tvnow.group(1)
                        api_url = f"https://chat.cfbu247.sbs/api/resolve-dlstream/{stream_id}"
                        resp = session.get(api_url, headers=HEADERS_TVNOW, timeout=10)
                        if resp.status_code == 200:
                            data = resp.json()
                            stream_url = data.get("m3u8") or data.get("proxyPlaylistUrl")
                            if stream_url:
                                return redirect(stream_url, code=302)
            except Exception:
                continue

        return "Nessun flusso m3u8 estratto dalla pagina HTSport", 404

    except Exception as e:
        return f"Errore Dynamic HTSport: {e}", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
