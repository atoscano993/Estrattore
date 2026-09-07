import os
import re
import requests
from flask import Flask, redirect

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
# 1. CANALI AUTOMATICI H24
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
# FUNZIONI RESOLUTION & SCRAPING
# ==========================================
def resolve_tvnow_stream(stream_id):
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
    """Estrae l'm3u8 da DamITV effettuando prima l'estrazione delle API o dei dati JSON interni"""
    try:
        clean_id = damitv_id.lstrip('/')
        
        # 1. Costruzione URL embed
        if clean_id.startswith("http"):
            embed_url = clean_id
        elif "/" in clean_id:
            embed_url = f"https://damitv.st/embed/?id={clean_id}"
        else:
            embed_url = f"https://damitv.st/embed/channel/?id={clean_id}"

        res = requests.get(embed_url, headers=HEADERS_DAMITV, timeout=6)
        if res.status_code == 200:
            html = res.text

            # --- METODO 1: Chiamata diretta all'API JSON interna se presente ---
            # DamITV passa spesso dati in JSON o endpoint /api/
            api_matches = re.findall(r'fetch\(["\']([^"\']+)["\']', html)
            for api_path in api_matches:
                if not api_path.startswith("http"):
                    api_path = "https://damitv.st" + (api_path if api_path.startswith("/") else "/" + api_path)
                try:
                    api_res = requests.get(api_path, headers=HEADERS_DAMITV, timeout=5)
                    if api_res.status_code == 200:
                        data = api_res.json()
                        stream_found = data.get("hlsUrl") or data.get("sdUrl") or data.get("url") or data.get("m3u8")
                        if stream_found:
                            return stream_found
                except Exception:
                    pass

            # --- METODO 2: Estrazione diretta di oggetti JSON / HLS dall'HTML ---
            # Cerca chiavi hlsUrl/sdUrl/file/source
            hls_matches = re.findall(r'["\'](?:hlsUrl|sdUrl|file|source|url)["\']\s*:\s*["\']([^"\']+)["\']', html, re.IGNORECASE)
            for match_url in hls_matches:
                clean_url = match_url.replace(r'\/', '/')
                if "http" in clean_url or ".m3u8" in clean_url:
                    return clean_url

            # --- METODO 3: Fallback Regex per qualsiasi URL http che finisce in .m3u8 ---
            match_m3u8 = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', html)
            if match_m3u8:
                return match_m3u8.group(1).replace(r'\/', '/')

            # --- METODO 4: Verifica Iframe Nidificato ---
            iframe_match = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if iframe_match:
                sub_url = iframe_match.group(1)
                if sub_url.startswith('//'):
                    sub_url = 'https:' + sub_url
                elif sub_url.startswith('/'):
                    sub_url = 'https://damitv.st' + sub_url
                
                # Ricorsione sull'iframe interno
                return resolve_damitv_stream(sub_url)

    except Exception as e:
        print(f"[DAMITV RESOLVE ERROR] ID {damitv_id}: {e}")
    return None

def find_damitv_match_by_team(team_key):
    """Cerca nel palinsesto di DamITV tutti i match corrispondenti alle keyword della squadra"""
    try:
        keywords = SERIE_A_TEAMS.get(team_key, [team_key])
        schedule_url = "https://damitv.st/schedule/"
        res = requests.get(schedule_url, headers=HEADERS_DAMITV, timeout=6)
        if res.status_code == 200:
            html_content = res.text.lower()
            # Cerca pattern che contengono href o id con parametri
            found_urls = re.findall(r'(?:href=["\']|id=)([^"\'\s>]*?(?:seriea|embed|event)[^"\'\s>]*)', html_content, re.IGNORECASE)
            
            for url_str in found_urls:
                for kw in keywords:
                    if kw in url_str:
                        # Estrae lo slug pulito (es: seriea/2026-09-07/cag-lec)
                        if "id=" in url_str:
                            slug = url_str.split("id=")[-1]
                        else:
                            slug = url_str
                        
                        slug = slug.strip("/").lstrip("?")
                        print(f"[SCRAPER SUCCESS] Trovato candidato per {team_key}: {slug}")
                        
                        # Verifica se dallo slug si ottiene uno stream m3u8 valido
                        stream_url = resolve_damitv_stream(slug)
                        if stream_url:
                            return stream_url
    except Exception as e:
        print(f"[SCRAPER ERROR] {team_key}: {e}")
    return None

# ==========================================
# ROTTE FLASK
# ==========================================
@app.route('/')
def home():
    return "Estrattore attivo (TVNow + DamITV)", 200

@app.route('/<channel_name>')
def get_stream(channel_name):
    name_clean = channel_name.replace(".m3u8", "").lower()

    # 1. Partita Squadra Serie A
    if name_clean in SERIE_A_TEAMS:
        stream_url = find_damitv_match_by_team(name_clean)
        if stream_url:
            print(f"[MATCH SUCCESS] Reindirizzamento diretto a: {stream_url}")
            return redirect(stream_url, code=302)

    # 2. Canali Automatici H24 (TVNow -> DamITV Failover)
    if name_clean in AUTOMATIC_CHANNELS:
        ch_info = AUTOMATIC_CHANNELS[name_clean]
        if ch_info.get("tvnow_id"):
            tvnow_url = resolve_tvnow_stream(ch_info["tvnow_id"])
            if tvnow_url:
                return redirect(tvnow_url, code=302)
        if ch_info.get("damitv_id"):
            damitv_url = resolve_damitv_stream(ch_info["damitv_id"])
            if damitv_url:
                return redirect(damitv_url, code=302)

    # 3. ID Numerico TVNow Diretto
    if name_clean.isdigit():
        direct_url = resolve_tvnow_stream(name_clean)
        if direct_url:
            return redirect(direct_url, code=302)

    return f"Nessun evento disponibile per '{channel_name}'", 503

@app.route('/event/<path:event_slug>')
def get_direct_event(event_slug):
    clean_slug = event_slug.replace(".m3u8", "")
    stream_url = resolve_damitv_stream(clean_slug)
    if stream_url:
        return redirect(stream_url, code=302)
    return f"Impossibile estrarre lo stream per '{clean_slug}'", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
