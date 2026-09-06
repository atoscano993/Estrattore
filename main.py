import os
import requests
from flask import Flask, redirect, Response

app = Flask(__name__)

# ==========================================
# CONFIGURAZIONE HEADERS STANDARD
# ==========================================
HEADERS_TVNOW = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://tvnow247.top/",
    "Origin": "https://tvnow247.top"
}

HEADERS_DAMITV = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://damitv.st/",
    "Origin": "https://damitv.st"
}

# ==========================================
# 1. CANALI AUTOMATICI (Mappatura ID)
# ==========================================
AUTOMATIC_CHANNELS = {
    "sport24": {"tvnow_id": "869", "damitv_id": "premium869"},
    "sportuno": {"tvnow_id": "461", "damitv_id": "premium461"},
    "sportcalcio": {"tvnow_id": "870", "damitv_id": "premium870"},
    "sportf1": {"tvnow_id": "577", "damitv_id": "premium577"},
    "sportmoto": {"tvnow_id": "575", "damitv_id": "premium575"},
    "sportmax": {"tvnow_id": "460", "damitv_id": "premium460"},
    "sporttennis": {"tvnow_id": "576", "damitv_id": "premium576"},
    "sportarena": {"tvnow_id": "462", "damitv_id": "premium462"},
    "dazn1": {"tvnow_id": "877", "damitv_id": "premium877"}
}

# ==========================================
# 2. CANALI MANUALI / HOT-SWAP (Con Header Iniettati)
# ==========================================
MANUAL_STREAMS = {
    "htsport_1": {
        "url": "https://1w4o2c.7m12bgo8dx9z.net:8443/hls/wiyfbikc.m3u8?s=INSERISCI_TOKEN&e=INSERISCI_EXPIRES",
        "referer": "https://motifguide.net/"
    },
    "forgemindly_1": {
        "url": "https://cdn7.zohanayaan.com:1686/hls/do47.m3u8?md5=INSERISCI_MD5&expires=INSERISCI_EXPIRES",
        "referer": "https://forgemindly.com/"
    }
}

# ==========================================
# FUNZIONI DI RESOLUTION
# ==========================================
def resolve_tvnow_stream(stream_id):
    try:
        api_url = f"https://chat.cfbu247.sbs/api/resolve-dlstream/{stream_id}"
        response = requests.get(api_url, headers=HEADERS_TVNOW, timeout=8)
        if response.status_code == 200:
            data = response.json()
            return data.get("m3u8") or data.get("proxyPlaylistUrl")
    except Exception as e:
        print(f"[TVNOW ERROR] ID {stream_id}: {e}")
    return None

def resolve_damitv_stream(damitv_id):
    try:
        url = f"https://messi.damitv.st/hls/{damitv_id}/index.m3u8"
        response = requests.head(url, headers=HEADERS_DAMITV, timeout=4)
        if response.status_code in [200, 302]:
            return url
    except Exception as e:
        print(f"[DAMITV ERROR] ID {damitv_id}: {e}")
    return None

# ==========================================
# ROTTE FLASK
# ==========================================
@app.route('/')
def home():
    return "Estrattore attivo (TVNow + DamITV + Manual Streams)", 200

@app.route('/<channel_name>')
def get_stream(channel_name):
    # Rimuove l'estensione .m3u8 se presente nell'URL chiamato
    name_clean = channel_name.replace(".m3u8", "").lower()

    # A. PRIMA VERIFICA: Canale manuale (Proxy con Header appropriati)
    if name_clean in MANUAL_STREAMS:
        stream_data = MANUAL_STREAMS[name_clean]
        print(f"[MANUAL] Servendo flusso manuale proxy per: {name_clean}")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": stream_data["referer"]
        }
        
        try:
            req = requests.get(stream_data["url"], headers=headers, timeout=10)
            if req.status_code == 200:
                return Response(req.content, content_type='application/vnd.apple.mpegurl')
            else:
                return f"Errore sorgente manuale: HTTP {req.status_code}", req.status_code
        except Exception as e:
            return f"Errore connessione sorgente: {e}", 500

    # B. SECONDA VERIFICA: Mappa automatica (TVNow -> DamITV Failover)
    if name_clean in AUTOMATIC_CHANNELS:
        ch_info = AUTOMATIC_CHANNELS[name_clean]
        
        # 1. Tentativo TVNow
        if ch_info.get("tvnow_id"):
            tvnow_url = resolve_tvnow_stream(ch_info["tvnow_id"])
            if tvnow_url:
                print(f"[TVNOW SUCCESS] Canale: {name_clean}")
                return redirect(tvnow_url, code=302)

        # 2. Tentativo DamITV
        if ch_info.get("damitv_id"):
            damitv_url = resolve_damitv_stream(ch_info["damitv_id"])
            if damitv_url:
                print(f"[DAMITV SUCCESS] Canale: {name_clean}")
                return redirect(damitv_url, code=302)

    # C. TERZA VERIFICA: Invio diretto di ID numerico TVNow
    if name_clean.isdigit():
        direct_url = resolve_tvnow_stream(name_clean)
        if direct_url:
            return redirect(direct_url, code=302)

    return f"Canale '{channel_name}' non disponibile o non trovato sui provider", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# 2. CANALI MANUALI / HOT-SWAP
# Incolla qui i link estrapolati a mano (HTSport, Forgemindly, ecc.)
# ==========================================
MANUAL_STREAMS = {
    "htsport_1": "https://1w4o2c.7m12bgo8dx9z.net:8443/hls/wiyfbikc.m3u8?s=INSERISCI_TOKEN&e=INSERISCI_EXPIRES",
    "forgemindly_1": "https://cdn7.zohanayaan.com:1686/hls/do47.m3u8?md5=INSERISCI_MD5&expires=INSERISCI_EXPIRES"
}

# ==========================================
# FUNZIONI DI RESOLUTION
# ==========================================
def resolve_tvnow_stream(stream_id):
    """Risolve tramite API TVNow"""
    try:
        api_url = f"https://chat.cfbu247.sbs/api/resolve-dlstream/{stream_id}"
        response = requests.get(api_url, headers=HEADERS_TVNOW, timeout=8)
        if response.status_code == 200:
            data = response.json()
            stream_url = data.get("m3u8") or data.get("proxyPlaylistUrl")
            if stream_url:
                return stream_url
    except Exception as e:
        print(f"[TVNOW ERROR] ID {stream_id}: {e}")
    return None

def resolve_damitv_stream(damitv_id):
    """Risolve/Verifica sorgente DamITV"""
    try:
        url = f"https://messi.damitv.st/hls/{damitv_id}/index.m3u8"
        response = requests.head(url, headers=HEADERS_DAMITV, timeout=4)
        if response.status_code in [200, 302]:
            return url
    except Exception as e:
        print(f"[DAMITV ERROR] ID {damitv_id}: {e}")
    return None

# ==========================================
# ROTTE FLASK
# ==========================================
@app.route('/')
def home():
    return "Estrattore attivo (TVNow + DamITV + Manual Streams)", 200

# Endpoint unificato per il tuo file .m3u
@app.route('/<channel_name>.m3u8')
def get_stream(channel_name):
    name_clean = channel_name.lower()

    # A. PRIMA VERIFICA: Canale manuale in HOT-SWAP
    if name_clean in MANUAL_STREAMS:
        print(f"[MANUAL] Servendo flusso manuale: {name_clean}")
        return redirect(MANUAL_STREAMS[name_clean], code=302)

    # B. SECONDA VERIFICA: Mappa automatica (TVNow -> DamITV Failover)
    if name_clean in AUTOMATIC_CHANNELS:
        ch_info = AUTOMATIC_CHANNELS[name_clean]
        
        # 1. Tentativo TVNow
        if ch_info.get("tvnow_id"):
            tvnow_url = resolve_tvnow_stream(ch_info["tvnow_id"])
            if tvnow_url:
                print(f"[TVNOW SUCCESS] Canale: {name_clean}")
                return redirect(tvnow_url, code=302)

        # 2. Tentativo DamITV
        if ch_info.get("damitv_id"):
            damitv_url = resolve_damitv_stream(ch_info["damitv_id"])
            if damitv_url:
                print(f"[DAMITV SUCCESS] Canale: {name_clean}")
                return redirect(damitv_url, code=302)

    # C. TERZA VERIFICA: Invio diretto di ID numerico TVNow
    if name_clean.isdigit():
        direct_url = resolve_tvnow_stream(name_clean)
        if direct_url:
            return redirect(direct_url, code=302)

    return f"Canale '{channel_name}' non disponibile o non trovato sui provider", 404

# Endpoint diretto TVNow per ID
@app.route('/tvnow/<channel_id>.m3u8')
def get_tvnow_by_id(channel_id):
    stream_url = resolve_tvnow_stream(channel_id)
    if stream_url:
        return redirect(stream_url, code=302)
    return f"ID TVNow '{channel_id}' non disponibile", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
