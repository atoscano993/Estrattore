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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    "Sec-Ch-Ua": '"Chromium";v="128", "Not=A?Brand";v="24", "Google Chrome";v="128"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
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
        if any(domain in parsed.netloc for domain in ["indianservers", "embedindia", "workers.dev"]):
            headers["Referer"] = "https://embedindia.st/"
            headers["Origin"] = "https://embedindia.st"
        else:
            headers["Referer"] = "https://damitv.st/"
            headers["Origin"] = "https://damitv.st"

        r = session.get(url, headers=headers, timeout=6, stream=True, allow_redirects=True)
        print(f"[CHECK] {url} -> Status: {r.status_code}")
        
        if r.status_code == 200:
            chunk = next(r.iter_content(chunk_size=512), b"").decode('utf-8', errors='ignore')
            if "#EXTM3U" in chunk or "#EXT-X-" in chunk or ".ts" in chunk or len(chunk) > 10:
                return True
    except Exception as e:
        print(f"[CHECK ERROR] {url} -> {e}")
    return False

def generate_full_test_urls(slug, token="", expire=""):
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    # Mettiamo prima i domini che rispondono dai data center
    base_domains = [
        "messi.damitv.st",
        "damitv.st",
        "embedindia.st"
    ]
    
    paths = [
        f"ucl/{today_str}/{slug}/mono.ts.m3u8",
        f"ucl/{today_str}/{slug}/index.m3u8",
        f"{today_str}/{slug}/index.m3u8",
        f"{slug}/index.m3u8",
        f"papi/tv/live/{slug}.m3u8"
    ]
    
    if token:
        paths.insert(0, f"secure/{token}/{expire}/1788969600/{slug}/tracks-v1a1/mono.ts.m3u8")
    
    clean_paths = [p for p in paths if p]
    urls = []
    
    for domain in base_domains:
        for path in clean_paths:
            urls.append(f"https://{domain}/{path}")
            
    return urls

def resolve_damitv_stream(team_key):
    session = requests.Session()
    headers = HEADERS_BASE.copy()
    headers["Referer"] = "https://damitv.st/"
    headers["Origin"] = "https://damitv.st"
    session.headers.update(headers)

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
        print(f"[TOKEN ERROR] {e}")

    slugs = SERIE_A_TEAMS.get(team_key, [team_key])
    
    for slug in slugs:
        test_urls = generate_full_test_urls(slug, token, expire)
        for url in test_urls:
            if verify_stream_health(url, session):
                print(f"[FOUND SUCCESS STREAM]: {url}")
                return url

    return None

def resolve_tvnow_stream(stream_id):
    try:
        api_url = f"https://chat.cfbu247.sbs/api/resolve-dlstream/{stream_id}"
        response = requests.get(api_url, headers=HEADERS_TVNOW, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("m3u8") or data.get("proxyPlaylistUrl")
    except Exception:
        pass
    return None

@app.route('/')
def home():
    return "Proxy attivo e pronto.", 200

@app.route('/proxy')
def proxy_m3u8():
    target_url = request.args.get('url')
    if not target_url:
        return "URL mancante", 400
    
    parsed = urlparse(target_url)
    headers = HEADERS_BASE.copy()
    
    if any(domain in parsed.netloc for domain in ["indianservers", "embedindia", "workers.dev"]):
        headers["Referer"] = "https://embedindia.st/"
        headers["Origin"] = "https://embedindia.st"
    else:
        headers["Referer"] = "https://damitv.st/"
        headers["Origin"] = "https://damitv.st"

    try:
        res = requests.get(target_url, headers=headers, timeout=12, stream=True, allow_redirects=True)
        final_url = res.url

        if res.status_code == 200:
            content_type = res.headers.get('Content-Type', '')
            
            if ".m3u8" in final_url or "mpegurl" in content_type or "apple" in content_type or target_url.endswith(".m3u8") or "text/plain" in content_type:
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

@app.route('/<channel_name>')
def get_stream(channel_name):
    name_clean = channel_name.replace(".m3u8", "").lower()

    if name_clean in SERIE_A_TEAMS:
        stream_url = resolve_damitv_stream(name_clean)
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
