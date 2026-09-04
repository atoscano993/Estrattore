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

# ==========================================
# 1. ROTTE TVNOW (DIRETTE E VELOCI)
# ==========================================
@app.route('/<channel_name>.m3u8')
def get_stream(channel_name):
    name_clean = channel_name.lower()
    
    if name_clean in TVNOW_MAP or name_clean.isdigit():
        stream_id = TVNOW_MAP.get(name_clean, channel_name)
        return resolve_tvnow_stream(stream_id)

    return f"Canale TVNow '{channel_name}' non valido", 404

@app.route('/tvnow/<channel_id>.m3u8')
def get_tvnow_by_id(channel_id):
    return resolve_tvnow_stream(channel_id)

def resolve_tvnow_stream(stream_id):
    """Funzione helper dedicata per risolvere gli ID TVNow"""
    try:
        api_url = f"https://chat.cfbu247.sbs/api/resolve-dlstream/{stream_id}"
        response = requests.get(api_url, headers=HEADERS_TVNOW, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            stream_url = data.get("m3u8") or data.get("proxyPlaylistUrl")
            if stream_url:
                return redirect(stream_url, code=302)
                
        return f"Flusso TVNow (ID: {stream_id}) non disponibile", 404
    except Exception as e:
        return f"Errore server TVNow: {e}", 500

# ==========================================
# 2. ROTTA HTSPORT (SOLO SORGENTI NATIVE)
# ==========================================
@app.route('/htsport/<page_name>.m3u8')
def get_htsport_dynamic(page_name):
    try:
        clean_page = page_name.replace(".m3u8", "")
        target_url = f"https://htsport.org/{clean_page}.htm"
        
        session = requests.Session()
        session.headers.update(HEADERS_HTSPORT)
        
        page_resp = session.get(target_url, timeout=10)
        if page_resp.status_code != 200:
            return f"Pagina {target_url} non trovata", 404
            
        html = page_resp.text

        # Cerca eventuali iframe sorgente nella pagina
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
                    
                    # Estrazione m3u8 in chiaro se presente
                    match_m3u8 = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', sub_text)
                    if match_m3u8:
                        return redirect(match_m3u8.group(1).replace(r'\/', '/'), code=302)

            except Exception:
                continue

        return "Nessun flusso m3u8 nativo estratto da HTSport", 404

    except Exception as e:
        return f"Errore HTSport: {e}", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
