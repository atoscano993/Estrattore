import os
import re
import requests
from flask import Flask, redirect, Response, jsonify

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
    "Origin": "https://damitv.st",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
}

# ==========================================
# 1. CANALI AUTOMATICI H24 (TVNow / DamITV)
# ==========================================
AUTOMATIC_CHANNELS = {
    "sport24": {"tvnow_id": "869", "damitv_id": "sky-sport-24"},
    "sportuno": {"tvnow_id": "461", "damitv_id": "sky-sport-uno"},
    "sportcalcio": {"tvnow_id": "870", "damitv_id": "sky-sport-calcio"},
    "sportf1": {"tvnow_id": "577", "damitv_id": "sky-sport-f1"},
    "sportmoto": {"tvnow_id": "575", "damitv_id": "sky-sport-motogp"},
    "sportmax": {"tvnow_id": "460", "damitv_id": "sky-sport-max"},
    "sporttennis": {"tvnow_id": "576", "damitv_id": "sky-sport-tennis"},
    "sportarena": {"tvnow_id": "462", "damitv_id": "sky-sport-arena"},
    "dazn1": {"tvnow_id": "877", "damitv_id": "dazn-1"}
}

# ==========================================
# 2. DIZIONARIO SQUADRE SERIE A
# ==========================================
SERIE_A_TEAMS = {
    "atalanta": ["atalanta", "ata"],
    "bologna": ["bologna", "bol"],
    "cagliari": ["cagliari", "cag"],
    "como": ["como"],
    "fiorentina": ["fiorentina", "fio"],
    "frosinone": ["frosinone", "fro"],
    "genoa": ["genoa", "gen"],
    "inter": ["inter", "int"],
    "juventus": ["juventus", "juve", "juv"],
    "lazio": ["lazio", "laz"],
    "lecce": ["lecce", "lec"],
    "milan": ["milan", "mil"],
    "monza": ["monza", "mon"],
    "napoli": ["napoli", "nap"],
    "parma": ["parma", "par"],
    "roma": ["roma", "rom"],
    "sassuolo": ["sassuolo", "sas"],
    "torino": ["torino", "tor"],
    "udinese": ["udinese", "udi"],
    "venezia": ["venezia", "ven"]
}

# ==========================================
# 3. CANALI MANUALI / HOT-SWAP (Modifica qui i tuoi flussi)
# ==========================================
MANUAL_STREAMS = {
    "live_1": {
        "url": "https://xameleon.phantemlis.top/one/secure/4202dae3386d85ab82acc9be1eb0fa0a/1788799130/premium877/index.m3u8",
        "referer": "https://hamis.romponalis.st/",
        "origin": "https://hamis.romponalis.st"
    },
    "live_2": {
        "url": "https://gr676m.l948728p57nx.net:8443/hls/g8yy3cfv128h5.m3u8?s=HPc9CMpPnr4_Whd8Il_FGA&e=1788810115",
        "referer": "https://cuttingfame.net/",
        "origin": "https://cuttingfame.net"
    }
}

# ==========================================
# FUNZIONI DI RESOLUTION E SCRAPING
# ==========================================
def resolve_tvnow_stream(stream_id):
    """Risolve tramite API TVNow"""
    try:
        api_url = f"https://chat.cfbu247.sbs/api/resolve-dlstream/{stream_id}"
        response = requests.get(api_url, headers=HEADERS_TVNOW, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("m3u8") or data.get("proxyPlaylistUrl")
    except Exception as e:
        print(f"[TVNOW ERROR] ID {stream_id}: {e}")
    return None

def resolve_damitv_stream(damitv_id):
    """Estrae l'm3u8 nativo dall'embed di DamITV"""
    try:
        if "/" in damitv_id:
            embed_url = f"https://damitv.st/embed/?id={damitv_id}"
        else:
            embed_url = f"https://damitv.st/embed/channel/?id={damitv_id}"

        res = requests.get(embed_url, headers=HEADERS_DAMITV, timeout=6)
        if res.status_code == 200:
            match = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', res.text)
            if match:
                return match.group(1).replace(r'\/', '/')

            match_rel = re.search(r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', res.text)
            if match_rel:
                return match_rel.group(1).replace(r'\/', '/')
    except Exception as e:
        print(f"[DAMITV ERROR] Slug/ID {damitv_id}: {e}")
    return None

def find_damitv_match_by_team(team_key):
    """Scraper per il palinsesto DamITV"""
    try:
        keywords = SERIE_A_TEAMS.get(team_key, [team_key])
        schedule_url = "https://damitv.st/schedule/"
        
        res = requests.get(schedule_url, headers=HEADERS_DAMITV, timeout=6)
        if res.status_code == 200:
            html_content = res.text.lower()
            found_urls = re.findall(r'(?:href=["\']|id=)([^"\'\s>]*(?:seriea|embed|event)[^"\'\s>]*)', html_content, re.IGNORECASE)
            
            for url_str in found_urls:
                for kw in keywords:
                    if kw in url_str:
                        slug = url_str.split("id=")[-1].strip("/").lstrip("?")
                        print(f"[SCRAPER SUCCESS] Trovato evento per {team_key}: {slug}")
                        return slug
    except Exception as e:
        print(f"[SCRAPER ERROR] Errore palinsesto per {team_key}: {e}")
    return None

# ==========================================
# ROTTE FLASK
# ==========================================
@app.route('/')
def home():
    return "Estrattore attivo (TVNow + DamITV + Eventi Live Serie A + Manual Streams)", 200

@app.route('/<channel_name>')
def get_stream(channel_name):
    name_clean = channel_name.replace(".m3u8", "").lower()

    # A. Canali Manuali (Hot-Swap)
    if name_clean in MANUAL_STREAMS:
        stream_data = MANUAL_STREAMS[name_clean]
        
        url_clean = stream_data["url"].strip()
        referer_clean = stream_data["referer"].strip()
        origin_clean = stream_data.get("origin", referer_clean).strip()

        if "http" not in url_clean:
            return "Token manuale non impostato o invalido", 400
            
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": referer_clean,
            "Origin": origin_clean
        }
        try:
            req = requests.get(url_clean, headers=headers, timeout=10)
            if req.status_code == 200:
                return Response(req.content, content_type='application/vnd.apple.mpegurl')
            return f"Errore sorgente manuale: HTTP {req.status_code}", req.status_code
        except Exception as e:
            return f"Errore connessione sorgente: {e}", 500

    # B. Partita Squadra Serie A (Scraping automatico)
    if name_clean in SERIE_A_TEAMS:
        event_slug = find_damitv_match_by_team(name_clean)
        if event_slug:
            stream_url = resolve_damitv_stream(event_slug)
            if stream_url:
                print(f"[MATCH SUCCESS] Servendo la diretta per {name_clean}")
                return redirect(stream_url, code=302)

    # C. Canali Automatici H24 (TVNow -> DamITV Failover)
    if name_clean in AUTOMATIC_CHANNELS:
        ch_info = AUTOMATIC_CHANNELS[name_clean]
        
        # 1. TVNow
        if ch_info.get("tvnow_id"):
            tvnow_url = resolve_tvnow_stream(ch_info["tvnow_id"])
            if tvnow_url:
                return redirect(tvnow_url, code=302)

        # 2. DamITV
        if ch_info.get("damitv_id"):
            damitv_url = resolve_damitv_stream(ch_info["damitv_id"])
            if damitv_url:
                return redirect(damitv_url, code=302)

    # D. ID Numerico TVNow Diretto
    if name_clean.isdigit():
        direct_url = resolve_tvnow_stream(name_clean)
        if direct_url:
            return redirect(direct_url, code=302)

    return f"Nessun evento o canale disponibile per '{channel_name}'", 503

# Rotta di riserva per inserire lo slug dell'evento manualmente dall'URL
@app.route('/event/<path:event_slug>')
def get_direct_event(event_slug):
    clean_slug = event_slug.replace(".m3u8", "")
    stream_url = resolve_damitv_stream(clean_slug)
    if stream_url:
        return redirect(stream_url, code=302)
    return f"Impossibile estrarre lo stream per l'evento '{clean_slug}'", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
