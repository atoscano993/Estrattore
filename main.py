import re
import requests
from flask import Flask, Response, redirect

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

HEADERS_DEFAULT = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

HEADERS_EPIEMBEDS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://epiembeds.online/",
    "Origin": "https://epiembeds.online"
}

HEADERS_TVNOW = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://tvnow.best/",
    "Origin": "https://tvnow.best"
}


def decode_epiembeds_script(html_content):
    """Estrae l'array _uy4 dall'HTML di EpiEmbeds, lo decodifica e trova il link .m3u8"""
    match = re.search(r'var\s+_uy4\s*=\s*\[([0-9,\s]+)\]', html_content)
    if not match:
        return None
        
    raw_bytes = [int(x.strip()) for x in match.group(1).split(',')]
    decoded_chars = [chr(((b ^ 188) - 245 + 256) & 255) for b in raw_bytes]
    decoded_script = "".join(decoded_chars)
    
    m3u8_match = re.search(r'file:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', decoded_script)
    if m3u8_match:
        return m3u8_match.group(1)
        
    return None


# ==========================================
# ROTTA HTSPORT (EpiEmbeds)
# ==========================================
@app.route('/htsport/<page_name>.m3u8')
def get_htsport_dynamic(page_name):
    try:
        clean_page = page_name.replace(".m3u8", "")
        session = requests.Session()
        
        target_url = f"https://htsport.org/{clean_page}.htm"
        page_resp = session.get(target_url, headers=HEADERS_DEFAULT, timeout=10)
        if page_resp.status_code != 200:
            return "Pagina HTSport non trovata", 404

        match_embed = re.search(r'src=["\'](https?://epiembeds\.[^"\']+)["\']', page_resp.text, re.IGNORECASE)
        if not match_embed:
            return "Iframe EpiEmbeds non trovato", 404
        
        embed_url = match_embed.group(1)

        embed_resp = session.get(embed_url, headers={"Referer": target_url, "User-Agent": HEADERS_DEFAULT["User-Agent"]}, timeout=10)
        if embed_resp.status_code != 200:
            return "Impossibile caricare l'iframe EpiEmbeds", 404

        stream_url = decode_epiembeds_script(embed_resp.text)
        if not stream_url:
            return "Impossibile decodificare il flusso .m3u8 dall'iframe", 404

        m3u8_resp = requests.get(stream_url, headers=HEADERS_EPIEMBEDS, timeout=10)
        if m3u8_resp.status_code == 200:
            return Response(m3u8_resp.content, content_type='application/vnd.apple.mpegurl')
        
        return redirect(stream_url, code=302)

    except Exception as e:
        return f"Errore interno del server (HTSport): {str(e)}", 500


# ==========================================
# ROTTA TVNOW (Con supporto alla mappa ID)
# ==========================================
@app.route('/tvnow/<channel_id>.m3u8')
@app.route('/tvnow/id/<channel_id>.m3u8')
def get_tvnow_dynamic(channel_id):
    try:
        clean_channel = channel_id.replace(".m3u8", "").lower()
        
        # Mappatura: se viene passato ad es. "dazn1", usa l'ID "877". Altrimenti usa il valore originale.
        real_id = TVNOW_MAP.get(clean_channel, clean_channel)

        session = requests.Session()

        # Richiesta diretta all'embed di TVNow tramite l'ID numerico risolto
        target_url = f"https://tvnow.best/embed/{real_id}"
        resp = session.get(target_url, headers=HEADERS_TVNOW, timeout=10)
        
        if resp.status_code != 200:
            return f"Canale TVNow '{real_id}' non trovato", 404

        # Estrazione del link .m3u8
        m3u8_match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', resp.text)
        if not m3u8_match:
            return "Flusso .m3u8 non trovato nella pagina TVNow", 404

        stream_url = m3u8_match.group(1)

        # Proxy del flusso video
        m3u8_resp = requests.get(stream_url, headers=HEADERS_TVNOW, timeout=10)
        if m3u8_resp.status_code == 200:
            return Response(m3u8_resp.content, content_type='application/vnd.apple.mpegurl')

        return redirect(stream_url, code=302)

    except Exception as e:
        return f"Errore interno del server (TVNow): {str(e)}", 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
