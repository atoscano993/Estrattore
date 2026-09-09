import os
import re
import requests
from datetime import datetime
from urllib.parse import urljoin
from flask import Flask, redirect, Response, request

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

AUTOMATIC_CHANNELS = {
    "sport24": {"tvnow_id": "869", "damitv_id": "869"},
    "sportuno": {"tvnow_id": "461", "damitv_id": "461"},
    "sportcalcio": {"tvnow_id": "870", "damitv_id": "870"},
    "sportf1": {"tvnow_id": "577", "damitv_id": "577"},
    "sportmoto": {"tvnow_id": "575", "damitv_id": "575"},
    "sportmax": {"tvnow_id": "460", "damitv_id": "460"},
    "sporttennis": {"tvnow_id": "576", "damitv_id": "576"},
    "sportarena": {"tvnow_id": "462", "damitv_id": "462"},
    "dazn1": {"tvnow_id": "877", "damitv_id": "877"}
}

SERIE_A_TEAMS = {
    "atalanta": ["atalanta", "ata"],
    "bologna": ["bologna", "bol"],
    "cagliari": ["cagliari", "cag"],
"como": [
        "como", "com",
        "com-rbl", "rbl-com", "com-lei", "lei-com", # Leipzig
        "fey-com", "com-fey", # Feyenoord
        "com-mun", "mun-com", # Manchester United
        "len-com", "com-len", # Lens
        "com-aek", "aek-com", # AEK Athens
        "bet-com", "com-bet", # Real Betis
        "com-psg", "psg-com", # Paris Saint-Germain
        "bar-com", "com-bar"  # Barcelona
    ],
    "fiorentina": ["fiorentina", "fio"],
    "frosinone": ["frosinone", "fro"],
    "genoa": ["genoa", "gen"],
    "inter": [
        "inter", "int", 
        "rma-int", "int-rma", # Real Madrid
        "int-bru", "bru-int", # Club Brugge
        "int-shk", "shk-int", # Shakhtar Donetsk
        "fey-int", "int-fey", # Feyenoord
        "int-stu", "stu-int", # Stuttgart
        "bvb-int", "int-bvb", "dor-int", "int-dor", # Borussia Dortmund
        "int-liv", "liv-int", # Liverpool
        "slo-int", "int-slo"  # Slovan Bratislava
    ],
    "juventus": ["juventus", "juve", "juv"],
    "lazio": ["lazio", "laz"],
    "lecce": ["lecce", "lec"],
    "milan": ["milan", "mil"],
    "monza": ["monza", "mon"],
    "napoli": [
        "napoli", "nap",
        "nap-ars", "ars-nap", # Arsenal
        "vil-nap", "nap-vil", # Villarreal
        "nap-bod", "bod-nap", # Bodø/Glimt
        "por-nap", "nap-por", # Porto
        "mci-nap", "nap-mci", # Manchester City
        "nap-bru", "bru-nap", # Club Brugge
        "sab-nap", "nap-sab", # Sabah
        "nap-vik", "vik-nap"  # Viking
    ],
    "parma": ["parma", "par"],
"roma": [
        "roma", "rom",
        "fen-rom", "rom-fen", # Fenerbahçe
        "rom-rma", "rma-rom", # Real Madrid
        "rom-slo", "slo-rom", # Slovan Bratislava
        "mun-rom", "rom-mun", # Manchester United
        "psg-rom", "rom-psg", # Paris Saint-Germain
        "rom-spo", "spo-rom", "rom-scp", "scp-rom", # Sporting CP
        "aek-rom", "rom-aek", # AEK Athens
        "rom-lil", "lil-rom"  # Lille
    ],
    "sassuolo": ["sassuolo", "sas"],
    "torino": ["torino", "tor"],
    "udinese": ["udinese", "udi"],
    "venezia": ["venezia", "ven"]
}

# ==========================================
# FUNZIONI DI RESOLUTION CON FAILOVER
# ==========================================
def verify_stream_health(url):
    try:
        r = requests.head(url, headers=HEADERS_DAMITV, timeout=3)
        if r.status_code == 200:
            return True
        r_get = requests.get(url, headers=HEADERS_DAMITV, timeout=3, stream=True)
        return r_get.status_code == 200
    except Exception:
        return False

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
    try:
        clean_id = damitv_id.lstrip('/')
        match_id = clean_id.split('/')[-1] if '/' in clean_id else clean_id

        session = requests.Session()
        session.headers.update(HEADERS_DAMITV)

        token = ""
        expire = ""
        try:
            r_sess = session.get("https://damitv.st/papi/ad-session", timeout=5)
            if r_sess.status_code == 200:
                sid = r_sess.json().get("s", "")
                if sid:
                    r_ver = session.get(f"https://damitv.st/papi/ad-verify?s={sid}", timeout=5)
                    if r_ver.status_code == 200:
                        data_ver = r_ver.json()
                        token = data_ver.get("t", "")
                        expire = data_ver.get("e", "")
        except Exception as e:
            print(f"[DAMITV TOKEN WARN] {e}")

        if clean_id.isdigit() and token:
            direct_live_url = f"https://messi.damitv.st/papi/tv/live/{clean_id}.m3u8?tk={token}&e={expire}"
            if verify_stream_health(direct_live_url):
                return direct_live_url

        extract_url = f"https://damitv.st/papi/extract-url/{clean_id}"
        r_ext = session.get(extract_url, timeout=5)
        
        if r_ext.status_code != 200 and match_id != clean_id:
            extract_url = f"https://damitv.st/papi/extract-url/{match_id}"
            r_ext = session.get(extract_url, timeout=5)

        if r_ext.status_code == 200:
            data = r_ext.json()
            if data.get("success"):
                candidates = []
                if isinstance(data.get("streams"), list):
                    candidates.extend(data.get("streams"))
                if isinstance(data.get("hlsUrls"), list):
                    candidates.extend(data.get("hlsUrls"))
                if data.get("hlsUrl"):
                    candidates.append(data.get("hlsUrl"))
                if data.get("backupHlsUrl"):
                    candidates.append(data.get("backupHlsUrl"))

                unique_candidates = list(dict.fromkeys(candidates))

                for stream_url in unique_candidates:
                    if verify_stream_health(stream_url):
                        return stream_url
                
                if unique_candidates:
                    return unique_candidates[0]

    except Exception as e:
        print(f"[DAMITV RESOLVE ERROR] {e}")
    
    return None

def find_damitv_match_by_team(team_key):
    try:
        keywords = SERIE_A_TEAMS.get(team_key, [team_key])
        today_str = datetime.now().strftime('%Y-%m-%d')

        # 1. GENERAZIONE SLUG BRUTEFORCE (PROVA DATA E VARIANTI SQUADRE)
        for kw in keywords:
            candidates = [
                f"ucl/{today_str}/{kw}",
                f"seriea/{today_str}/{kw}",
                f"coppaitalia/{today_str}/{kw}",
                f"ucl/{today_str}/rma-{kw}",
                f"ucl/{today_str}/{kw}-rma",
                f"event/{kw}",
                f"live/{kw}"
            ]
            for cand in candidates:
                stream_url = resolve_damitv_stream(cand)
                if stream_url:
                    return stream_url

        # 2. SCRAPING DELLA PAGINA PRINCIPALE / SCHEDULE
        for page_url in ["https://damitv.st/", "https://damitv.st/schedule/"]:
            res = requests.get(page_url, headers=HEADERS_DAMITV, timeout=5)
            if res.status_code == 200:
                html_content = res.text.lower()
                # Cerca link o ID che contengono sia l'estensione/categoria sia le keywords
                matches = re.findall(r'href=["\']([^"\'\s>]+)["\']', html_content, re.IGNORECASE)
                for link in matches:
                    for kw in keywords:
                        if kw in link:
                            clean_slug = link.strip("/").lstrip("?")
                            if "id=" in clean_slug:
                                clean_slug = clean_slug.split("id=")[-1]
                            stream_url = resolve_damitv_stream(clean_slug)
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
    return "Estrattore attivo con Failover Automatico (TVNow + DamITV)", 200

@app.route('/debug-dami')
def debug_dami():
    target_id = request.args.get('id', 'seriea/2026-09-07/cag-lec')
    stream_found = resolve_damitv_stream(target_id)
    if stream_found:
        return f"<h3>Stream Estratto (Failover OK):</h3><p>URL: {stream_found}</p><p><a href='/proxy?url={requests.utils.quote(stream_found)}'>Testa tramite Proxy</a></p>"
    return f"Impossibile estrarre uno stream attivo per '{target_id}'.", 500

@app.route('/proxy')
def proxy_m3u8():
    target_url = request.args.get('url')
    if not target_url:
        return "URL mancante", 400
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://damitv.st/",
        "Origin": "https://damitv.st",
        "Accept": "*/*"
    }

    try:
        res = requests.get(target_url, headers=headers, timeout=12, stream=True)
        if res.status_code == 200:
            content_type = res.headers.get('Content-Type', '')
            
            if ".m3u8" in target_url or "mpegurl" in content_type or "apple" in content_type:
                lines = res.text.splitlines()
                new_lines = []
                
                for line in lines:
                    line_str = line.strip()
                    if line_str and not line_str.startswith('#'):
                        full_url = urljoin(target_url, line_str)
                        line_str = f"/proxy?url={requests.utils.quote(full_url)}"
                    new_lines.append(line_str)
                
                rewritten_m3u8 = "\n".join(new_lines)
                response = Response(rewritten_m3u8, mimetype='application/vnd.apple.mpegurl')
                response.headers["Access-Control-Allow-Origin"] = "*"
                response.headers["Access-Control-Allow-Headers"] = "*"
                return response
            
            response = Response(res.iter_content(chunk_size=1024*64), content_type=content_type or 'video/mp2t')
            response.headers["Access-Control-Allow-Origin"] = "*"
            return response
        else:
            return f"Errore remoto: {res.status_code}", res.status_code
    except Exception as e:
        return f"Errore Proxy: {e}", 500
        
@app.route('/event/<path:event_slug>')
def get_direct_event(event_slug):
    clean_slug = event_slug.replace(".m3u8", "")
    stream_url = resolve_damitv_stream(clean_slug)
    if stream_url:
        return redirect(f"/proxy?url={requests.utils.quote(stream_url)}", code=302)
    return f"Impossibile estrarre lo stream per '{clean_slug}'", 404

@app.route('/<channel_name>')
def get_stream(channel_name):
    name_clean = channel_name.replace(".m3u8", "").lower()

    if name_clean in SERIE_A_TEAMS:
        stream_url = find_damitv_match_by_team(name_clean)
            
        if stream_url:
            return redirect(f"/proxy?url={requests.utils.quote(stream_url)}", code=302)

    if name_clean in AUTOMATIC_CHANNELS:
        ch_info = AUTOMATIC_CHANNELS[name_clean]
        if ch_info.get("tvnow_id"):
            tvnow_url = resolve_tvnow_stream(ch_info["tvnow_id"])
            if tvnow_url:
                return redirect(tvnow_url, code=302)
        if ch_info.get("damitv_id"):
            damitv_url = resolve_damitv_stream(ch_info["damitv_id"])
            if damitv_url:
                return redirect(f"/proxy?url={requests.utils.quote(damitv_url)}", code=302)

    if name_clean.isdigit():
        direct_url = resolve_tvnow_stream(name_clean)
        if direct_url:
            return redirect(direct_url, code=302)

    return f"Nessun evento disponibile per '{channel_name}'", 503

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

SERIE_A_TEAMS = {
    "atalanta": ["atalanta", "ata"],
    "bologna": ["bologna", "bol"],
    "cagliari": ["cagliari", "cag"],
"como": [
        "como", "com",
        "com-rbl", "rbl-com", "com-lei", "lei-com", # Leipzig
        "fey-com", "com-fey", # Feyenoord
        "com-mun", "mun-com", # Manchester United
        "len-com", "com-len", # Lens
        "com-aek", "aek-com", # AEK Athens
        "bet-com", "com-bet", # Real Betis
        "com-psg", "psg-com", # Paris Saint-Germain
        "bar-com", "com-bar"  # Barcelona
    ],
    "fiorentina": ["fiorentina", "fio"],
    "frosinone": ["frosinone", "fro"],
    "genoa": ["genoa", "gen"],
    "inter": [
        "inter", "int", 
        "rma-int", "int-rma", # Real Madrid
        "int-bru", "bru-int", # Club Brugge
        "int-shk", "shk-int", # Shakhtar Donetsk
        "fey-int", "int-fey", # Feyenoord
        "int-stu", "stu-int", # Stuttgart
        "bvb-int", "int-bvb", "dor-int", "int-dor", # Borussia Dortmund
        "int-liv", "liv-int", # Liverpool
        "slo-int", "int-slo"  # Slovan Bratislava
    ],
    "juventus": ["juventus", "juve", "juv"],
    "lazio": ["lazio", "laz"],
    "lecce": ["lecce", "lec"],
    "milan": ["milan", "mil"],
    "monza": ["monza", "mon"],
    "napoli": [
        "napoli", "nap",
        "nap-ars", "ars-nap", # Arsenal
        "vil-nap", "nap-vil", # Villarreal
        "nap-bod", "bod-nap", # Bodø/Glimt
        "por-nap", "nap-por", # Porto
        "mci-nap", "nap-mci", # Manchester City
        "nap-bru", "bru-nap", # Club Brugge
        "sab-nap", "nap-sab", # Sabah
        "nap-vik", "vik-nap"  # Viking
    ],
    "parma": ["parma", "par"],
"roma": [
        "roma", "rom",
        "fen-rom", "rom-fen", # Fenerbahçe
        "rom-rma", "rma-rom", # Real Madrid
        "rom-slo", "slo-rom", # Slovan Bratislava
        "mun-rom", "rom-mun", # Manchester United
        "psg-rom", "rom-psg", # Paris Saint-Germain
        "rom-spo", "spo-rom", "rom-scp", "scp-rom", # Sporting CP
        "aek-rom", "rom-aek", # AEK Athens
        "rom-lil", "lil-rom"  # Lille
    ],
    "sassuolo": ["sassuolo", "sas"],
    "torino": ["torino", "tor"],
    "udinese": ["udinese", "udi"],
    "venezia": ["venezia", "ven"]
}

# ==========================================
# FUNZIONI DI RESOLUTION CON FAILOVER
# ==========================================
def verify_stream_health(url):
    try:
        r = requests.head(url, headers=HEADERS_DAMITV, timeout=3)
        if r.status_code == 200:
            return True
        r_get = requests.get(url, headers=HEADERS_DAMITV, timeout=3, stream=True)
        return r_get.status_code == 200
    except Exception:
        return False

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
    try:
        clean_id = damitv_id.lstrip('/')
        match_id = clean_id.split('/')[-1] if '/' in clean_id else clean_id

        session = requests.Session()
        session.headers.update(HEADERS_DAMITV)

        token = ""
        expire = ""
        try:
            r_sess = session.get("https://damitv.st/papi/ad-session", timeout=5)
            if r_sess.status_code == 200:
                sid = r_sess.json().get("s", "")
                if sid:
                    r_ver = session.get(f"https://damitv.st/papi/ad-verify?s={sid}", timeout=5)
                    if r_ver.status_code == 200:
                        data_ver = r_ver.json()
                        token = data_ver.get("t", "")
                        expire = data_ver.get("e", "")
        except Exception as e:
            print(f"[DAMITV TOKEN WARN] {e}")

        # Se è un canale ID numerico diretto
        if clean_id.isdigit() and token:
            direct_live_url = f"https://messi.damitv.st/papi/tv/live/{clean_id}.m3u8?tk={token}&e={expire}"
            if verify_stream_health(direct_live_url):
                return direct_live_url

        extract_url = f"https://damitv.st/papi/extract-url/{clean_id}"
        r_ext = session.get(extract_url, timeout=5)
        
        if r_ext.status_code != 200 and match_id != clean_id:
            extract_url = f"https://damitv.st/papi/extract-url/{match_id}"
            r_ext = session.get(extract_url, timeout=5)

        if r_ext.status_code == 200:
            data = r_ext.json()
            if data.get("success"):
                candidates = []
                if isinstance(data.get("streams"), list):
                    candidates.extend(data.get("streams"))
                if isinstance(data.get("hlsUrls"), list):
                    candidates.extend(data.get("hlsUrls"))
                if data.get("hlsUrl"):
                    candidates.append(data.get("hlsUrl"))
                if data.get("backupHlsUrl"):
                    candidates.append(data.get("backupHlsUrl"))

                unique_candidates = list(dict.fromkeys(candidates))

                # SCANSIONE A CASCATA REALE:
                # Testa tutti i link uno ad uno finché non ne trova uno con risposta HTTP 200 (evita i 404)
                for stream_url in unique_candidates:
                    if verify_stream_health(stream_url):
                        print(f"[STREAM OK FOUND]: {stream_url}")
                        return stream_url
                    else:
                        print(f"[STREAM DEAD 404]: {stream_url}")

    except Exception as e:
        print(f"[DAMITV RESOLVE ERROR] {e}")
    
    return None
def find_damitv_match_by_team(team_key):
    try:
        keywords = SERIE_A_TEAMS.get(team_key, [team_key])
        
        # 1. RICERCA TRAMITE API DI SEARCH INTERNA
        for kw in keywords:
            search_api = f"https://damitv.st/papi/search?q={kw}"
            try:
                res = requests.get(search_api, headers=HEADERS_DAMITV, timeout=4)
                if res.status_code == 200:
                    data = res.json()
                    events = data.get("events", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                    for ev in events:
                        slug = ev.get("id") or ev.get("slug") or ev.get("url", "")
                        if slug:
                            stream_url = resolve_damitv_stream(slug)
                            if stream_url:
                                return stream_url
            except Exception:
                pass

        # 2. SCRAPING DI FALLBACK CON REGEX SU MODELLI SLUG COMUNI
        schedule_url = "https://damitv.st/schedule/"
        res = requests.get(schedule_url, headers=HEADERS_DAMITV, timeout=6)
        if res.status_code == 200:
            html_content = res.text.lower()
            found_urls = re.findall(r'["\']([^"\'\s>]*?(?:seriea|ucl|coppaitalia|event)[^"\'\s>]*)["\']', html_content, re.IGNORECASE)
            
            for url_str in found_urls:
                for kw in keywords:
                    if kw in url_str:
                        slug = url_str.split("id=")[-1] if "id=" in url_str else url_str
                        slug = slug.strip("/").lstrip("?")
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
    return "Estrattore attivo con Failover Automatico (TVNow + DamITV)", 200

@app.route('/debug-dami')
def debug_dami():
    target_id = request.args.get('id', 'seriea/2026-09-07/cag-lec')
    stream_found = resolve_damitv_stream(target_id)
    if stream_found:
        return f"<h3>Stream Estratto (Failover OK):</h3><p>URL: {stream_found}</p><p><a href='/proxy?url={requests.utils.quote(stream_found)}'>Testa tramite Proxy</a></p>"
    return f"Impossibile estrarre uno stream attivo per '{target_id}'.", 500

@app.route('/proxy')
def proxy_m3u8():
    target_url = request.args.get('url')
    if not target_url:
        return "URL mancante", 400
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://damitv.st/",
        "Origin": "https://damitv.st",
        "Accept": "*/*"
    }

    try:
        res = requests.get(target_url, headers=headers, timeout=12, stream=True)
        if res.status_code == 200:
            content_type = res.headers.get('Content-Type', '')
            
            if ".m3u8" in target_url or "mpegurl" in content_type or "apple" in content_type:
                lines = res.text.splitlines()
                new_lines = []
                
                for line in lines:
                    line_str = line.strip()
                    if line_str and not line_str.startswith('#'):
                        full_url = urljoin(target_url, line_str)
                        line_str = f"/proxy?url={requests.utils.quote(full_url)}"
                    new_lines.append(line_str)
                
                rewritten_m3u8 = "\n".join(new_lines)
                response = Response(rewritten_m3u8, mimetype='application/vnd.apple.mpegurl')
                response.headers["Access-Control-Allow-Origin"] = "*"
                response.headers["Access-Control-Allow-Headers"] = "*"
                return response
            
            response = Response(res.iter_content(chunk_size=1024*64), content_type=content_type or 'video/mp2t')
            response.headers["Access-Control-Allow-Origin"] = "*"
            return response
        else:
            return f"Errore remoto: {res.status_code}", res.status_code
    except Exception as e:
        return f"Errore Proxy: {e}", 500
        
@app.route('/event/<path:event_slug>')
def get_direct_event(event_slug):
    clean_slug = event_slug.replace(".m3u8", "")
    stream_url = resolve_damitv_stream(clean_slug)
    if stream_url:
        return redirect(f"/proxy?url={requests.utils.quote(stream_url)}", code=302)
    return f"Impossibile estrarre lo stream per '{clean_slug}'", 404

@app.route('/<channel_name>')
def get_stream(channel_name):
    name_clean = channel_name.replace(".m3u8", "").lower()

    if name_clean in SERIE_A_TEAMS:
        stream_url = find_damitv_match_by_team(name_clean)
            
        if stream_url:
            return redirect(f"/proxy?url={requests.utils.quote(stream_url)}", code=302)

    if name_clean in AUTOMATIC_CHANNELS:
        ch_info = AUTOMATIC_CHANNELS[name_clean]
        if ch_info.get("tvnow_id"):
            tvnow_url = resolve_tvnow_stream(ch_info["tvnow_id"])
            if tvnow_url:
                return redirect(tvnow_url, code=302)
        if ch_info.get("damitv_id"):
            damitv_url = resolve_damitv_stream(ch_info["damitv_id"])
            if damitv_url:
                return redirect(f"/proxy?url={requests.utils.quote(damitv_url)}", code=302)

    if name_clean.isdigit():
        direct_url = resolve_tvnow_stream(name_clean)
        if direct_url:
            return redirect(direct_url, code=302)

    return f"Nessun evento disponibile per '{channel_name}'", 503

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
