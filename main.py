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

HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site"
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
# UTILITY STREAM
# ==========================================
def verify_stream_health(url, session):
    try:
        parsed = urlparse(url)
        headers = HEADERS_BASE.copy()
        if "indianservers" in parsed.netloc or "embedindia" in parsed.netloc:
            headers["Referer"] = "https://embedindia.st/"
            headers["Origin"] = "https://embedindia.st"
        else:
            headers["Referer"] = "https://damitv.st/"
            headers["Origin"] = "https://damitv.st"

        r = session.get(url, headers=headers, timeout=4, stream=True, allow_redirects=True)
        if r.status_code == 200:
            chunk = next(r.iter_content(chunk_size=512), b"").decode('utf-8', errors='ignore')
            if "#EXTM3U" in chunk or "#EXT-X-" in chunk or ".ts" in chunk or len(chunk) > 20:
                return True
        return False
    except Exception:
        return False

def extract_all_urls_from_json(data):
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
    variants = [base_url]
    parsed = urlparse(base_url)
    netloc = parsed.netloc

    prefixes = ["shiva", "netanyahu", "brahma", "vishnu", "messi1", "messi2", "messi3", "s1", "s2"]
    for pref in prefixes:
        if "." in netloc:
            domain_parts = netloc.split(".")
            new_netloc = f"{pref}.{'.'.join(domain_parts[1:])}"
            new_url = urlunparse(parsed._replace(netloc=new_netloc))
            if new_url not in variants:
                variants.append(new_url)
    return variants

# ==========================================
# RESOLVER CORE
# ==========================================
def resolve_tvnow_stream(stream_id):
    try:
        api_url = f"https://chat.cfbu247.sbs/api/resolve-dlstream/{stream_id}"
        response = requests.get(api_url, headers=HEADERS_TVNOW, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("m3u8") or data.get("proxyPlaylistUrl")
    except Exception as e:
        print(f"[TVNOW ERROR] {e}")
    return None

def resolve_damitv_stream(damitv_id):
    try:
        clean_id = damitv_id.lstrip('/')
        session = requests.Session()
        
        headers_damitv = HEADERS_BASE.copy()
        headers_damitv["Referer"] = "https://damitv.st/"
        headers_damitv["Origin"] = "https://damitv.st"
        session.headers.update(headers_damitv)

        # 1. Inizializzazione sessione e token
        token, expire = "", ""
        try:
            r_sess = session.get("https://damitv.st/papi/ad-session", timeout=4)
            if r_sess.status_code == 200:
                sid = r_sess.json().get("s", "")
                if sid:
                    r_ver = session.get(f"https://damitv.st/papi/ad-verify?s={sid}", timeout=4)
                    if r_ver.status_code == 200:
                        data_v = r_ver.json()
                        token = data_v.get("t", "")
                        expire = data_v.get("e", "")
        except Exception as e:
            print(f"[TOKEN WARN] {e}")

        # 2. Interrogazione API Extract URL
        extract_urls = [
            f"https://damitv.st/papi/extract-url/{clean_id}",
            f"https://damitv.st/papi/extract-url/event/{clean_id}"
        ]

        found_candidates = []
        for ext_url in extract_urls:
            try:
                r_ext = session.get(ext_url, timeout=4)
                if r_ext.status_code == 200:
                    data = r_ext.json()
                    if data.get("success"):
                        extracted = extract_all_urls_from_json(data)
                        found_candidates.extend(extracted)
            except Exception:
                pass

        # 3. Se non trova link JSON, genera le strutture dinamiche usate da IndianServers
        if not found_candidates and token and expire:
            event_name = clean_id.split('/')[-1]
            found_candidates.extend([
                f"https://shiva.indianservers.st/secure/{token}/{expire}/1788969600/{event_name}/tracks-v1a1/mono.ts.m3u8",
                f"https://netanyahu.indianservers.st/secure/{token}/{expire}/1788969600/{event_name}/tracks-v1a1/mono.ts.m3u8",
                f"https://messi.damitv.st/papi/tv/live/{clean_id}.m3u8?tk={token}&e={expire}"
            ])

        # 4. Generazione varianti e test health
        all_to_test = []
        for cand in list(dict.fromkeys(found_candidates)):
            all_to_test.extend(generate_server_variants(cand))

        for stream_url in list(dict.fromkeys(all_to_test)):
            if verify_stream_health(stream_url, session):
                print(f"[STREAM SUCCESS] {stream_url}")
                return stream_url

    except Exception as e:
        print(f"[RESOLVE ERROR] {e}")
    return None

def find_damitv_match_by_team(team_key):
    try:
        keywords = SERIE_A_TEAMS.get(team_key, [team_key])
        today_str = datetime.now().strftime('%Y-%m-%d')

        for kw in keywords:
            # Genera gli slug esatti visti nei log Network
            candidates = [
                f"{today_str}/{kw}",         # es. 2026-09-09/nap-ars (il pattern esatto dello screenshot)
                f"ucl/{today_str}/{kw}",     # es. ucl/2026-09-09/nap-ars
                kw,                          # es. nap-ars
                f"event/{kw}"
            ]
            for cand in candidates:
                stream_url = resolve_damitv_stream(cand)
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
    return "Proxy multi-server attivo.", 200

@app.route('/proxy')
def proxy_m3u8():
    target_url = request.args.get('url')
    if not target_url:
        return "URL mancante", 400
    
    parsed = urlparse(target_url)
    headers = HEADERS_BASE.copy()
    
    # Referer dinamico indispensabile per indianservers/embedindia
    if "indianservers" in parsed.netloc or "embedindia" in parsed.netloc or "workers.dev" in parsed.netloc:
        headers["Referer"] = "https://embedindia.st/"
        headers["Origin"] = "https://embedindia.st"
    else:
        headers["Referer"] = "https://damitv.st/"
        headers["Origin"] = "https://damitv.st"

    try:
        res = requests.get(target_url, headers=headers, timeout=10, stream=True, allow_redirects=True)
        final_url = res.url

        if res.status_code == 200:
            content_type = res.headers.get('Content-Type', '')
            
            # Intercetta playlist HLS anche se restituite come text/plain
            if ".m3u8" in final_url or "mpegurl" in content_type or "apple" in content_type or target_url.endswith(".m3u8"):
                lines = res.text.splitlines()
                new_lines = []
                
                for line in lines:
                    line_str = line.strip()
                    if line_str and not line_str.startswith('#'):
                        full_url = urljoin(final_url, line_str)
                        line_str = f"/proxy?url={requests.utils.quote(full_url)}"
                    new_lines.append(line_str)
                
                rewritten_m3u8 = "\n".join(new_lines)
                response = Response(rewritten_m3u8, mimetype='application/vnd.apple.mpegurl')
                response.headers["Access-Control-Allow-Origin"] = "*"
                return response
            
            response = Response(res.iter_content(chunk_size=1024*64), content_type=content_type or 'video/mp2t')
            response.headers["Access-Control-Allow-Origin"] = "*"
            return response
        else:
            return f"Errore server sorgente: {res.status_code}", res.status_code
    except Exception as e:
        return f"Errore Proxy: {e}", 500

@app.route('/event/<path:event_slug>')
def get_direct_event(event_slug):
    clean_slug = event_slug.replace(".m3u8", "")
    stream_url = resolve_damitv_stream(clean_slug)
    if stream_url:
        return redirect(f"/proxy?url={requests.utils.quote(stream_url)}", code=302)
    return f"Nessun evento attivo per '{clean_slug}'", 404

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

    return f"Nessun evento disponibile per '{channel_name}'", 503

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
