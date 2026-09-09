import os
import re
import requests
from datetime import datetime
from urllib.parse import urljoin
from flask import Flask, redirect, Response, request

app = Flask(__name__)

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

def verify_stream_health(url, session=None):
    try:
        s = session or requests
        r = s.get(url, headers=HEADERS_DAMITV, timeout=4, stream=True)
        if r.status_code == 200:
            chunk = next(r.iter_content(chunk_size=512), b"").decode('utf-8', errors='ignore')
            if "#EXTM3U" in chunk or "#EXT-X-" in chunk or ".ts" in chunk:
                return True
        return False
    except Exception:
        return False

def extract_all_urls_from_json(data):
    """ Ricorsivamente estrae ogni stringa che assomiglia a un URL HTTP/HTTPS dal JSON """
    urls = []
    if isinstance(data, dict):
        for k, v in data.items():
            urls.extend(extract_all_urls_from_json(v))
    elif isinstance(data, list):
        for item in data:
            urls.extend(extract_all_urls_from_json(item))
    elif isinstance(data, str):
        if data.startswith("http://") or data.startswith("https://"):
            urls.append(data)
    return urls

def generate_server_variants(base_url):
    """ Genera varianti di dominio per testare i Server 1..6 di DamITV (es. messi, messi2, server4, ecc.) """
    variants = [base_url]
    parsed = urlparse(base_url)
    netloc = parsed.netloc

    # Prefissi o nomi di server comuni usati nei mirror HLS
    server_prefixes = ["messi1", "messi2", "messi3", "messi4", "messi5", "messi6", "s1", "s2", "s3", "s4", "cdn1", "cdn2"]
    
    for pref in server_prefixes:
        # Sostituisce ad esempio 'messi.damitv.st' con 'messi4.damitv.st'
        if "." in netloc:
            domain_parts = netloc.split(".")
            new_netloc = f"{pref}.{'.'.join(domain_parts[1:])}"
            new_url = urlunparse(parsed._replace(netloc=new_netloc))
            if new_url not in variants:
                variants.append(new_url)
                
    return variants

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
            if verify_stream_health(direct_live_url, session):
                return direct_live_url

        extract_url = f"https://damitv.st/papi/extract-url/{clean_id}"
        r_ext = session.get(extract_url, timeout=5)
        
        if r_ext.status_code != 200 and match_id != clean_id:
            extract_url = f"https://damitv.st/papi/extract-url/{match_id}"
            r_ext = session.get(extract_url, timeout=5)

        if r_ext.status_code == 200:
            data = r_ext.json()
            if data.get("success"):
                # 1. Estrarre TUTTI gli URL presenti nella risposta JSON
                candidates = extract_all_urls_from_json(data)
                unique_candidates = list(dict.fromkeys(candidates))

                # 2. Generare varianti per ogni URL trovato (es. messi1, messi2, messi4...)
                all_to_test = []
                for cand in unique_candidates:
                    all_to_test.extend(generate_server_variants(cand))
                
                all_to_test = list(dict.fromkeys(all_to_test))

                # 3. Testare sequenzialmente ogni server/variante finché non risponde #EXTM3U
                for stream_url in all_to_test:
                    if verify_stream_health(stream_url, session):
                        print(f"[SUCCESS STREAM FOUND]: {stream_url}")
                        return stream_url
                    else:
                        print(f"[DEAD/404 STREAM]: {stream_url}")

    except Exception as e:
        print(f"[DAMITV RESOLVE ERROR] {e}")
    
    return None

def find_damitv_match_by_team(team_key):
    try:
        keywords = SERIE_A_TEAMS.get(team_key, [team_key])
        today_str = datetime.now().strftime('%Y-%m-%d')

        for kw in keywords:
            candidates = [
                f"ucl/{today_str}/{kw}",
                f"seriea/{today_str}/{kw}",
                f"coppaitalia/{today_str}/{kw}",
                f"event/{kw}",
                f"live/{kw}"
            ]
            for cand in candidates:
                stream_url = resolve_damitv_stream(cand)
                if stream_url:
                    return stream_url

    except Exception as e:
        print(f"[SCRAPER ERROR] {team_key}: {e}")
    return None

@app.route('/')
def home():
    return "Estrattore attivo con Failover Automatico (TVNow + DamITV)", 200

@app.route('/proxy')
def proxy_m3u8():
    target_url = request.args.get('url')
    if not target_url:
        return "URL mancante", 400
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://damitv.st/",
        "Origin": "https://damitv.st",
        "Accept": "*/*",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site"
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
