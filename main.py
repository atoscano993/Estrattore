import os
import re
import requests
from datetime import datetime
from urllib.parse import urljoin, urlparse
from flask import Flask, redirect, Response, request
from fp.fp import FreeProxy

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
        "com-rbl", "rbl-com", "com-lei", "lei-com",
        "fey-com", "com-fey",
        "com-mun", "mun-com",
        "len-com", "com-len",
        "com-aek", "aek-com",
        "bet-com", "com-bet",
        "com-psg", "psg-com",
        "bar-com", "com-bar"
    ],
    "fiorentina": ["fiorentina", "fio"],
    "frosinone": ["frosinone", "fro"],
    "genoa": ["genoa", "gen"],
    "inter": [
        "inter", "int", 
        "rma-int", "int-rma",
        "int-bru", "bru-int",
        "int-shk", "shk-int",
        "fey-int", "int-fey",
        "int-stu", "stu-int",
        "bvb-int", "int-bvb", "dor-int", "int-dor",
        "int-liv", "liv-int",
        "slo-int", "int-slo"
    ],
    "juventus": ["juventus", "juve", "juv"],
    "lazio": ["lazio", "laz"],
    "lecce": ["lecce", "lec"],
    "milan": ["milan", "mil"],
    "monza": ["monza", "mon"],
    "napoli": [
        "napoli", "nap",
        "nap-ars", "ars-nap",
        "vil-nap", "nap-vil",
        "nap-bod", "bod-nap",
        "por-nap", "nap-por",
        "mci-nap", "nap-mci",
        "nap-bru", "bru-nap",
        "sab-nap", "nap-sab",
        "nap-vik", "vik-nap"
    ],
    "parma": ["parma", "par"],
    "roma": [
        "roma", "rom",
        "fen-rom", "rom-fen",
        "rom-rma", "rma-rom",
        "rom-slo", "slo-rom",
        "mun-rom", "rom-mun",
        "psg-rom", "rom-psg",
        "rom-spo", "spo-rom", "rom-scp", "scp-rom",
        "aek-rom", "rom-aek",
        "rom-lil", "lil-rom"
    ],
    "sassuolo": ["sassuolo", "sas"],
    "torino": ["torino", "tor"],
    "udinese": ["udinese", "udi"],
    "venezia": ["venezia", "ven"]
}

# ==========================================
# UTILITY PROXY E STREAM
# ==========================================

def get_working_proxy():
    """Trova un proxy HTTP attivo per superare i blocchi IP del Cloud"""
    try:
        proxy_url = FreeProxy(country_id=['IT', 'DE', 'FR', 'NL'], https=True, timeout=2).get()
        return {"http": proxy_url, "https": proxy_url}
    except Exception as e:
        print(f"[PROXY FETCH ERROR] Nessun proxy trovato: {e}")
        return None

def verify_stream_health(url, session):
    try:
        parsed = urlparse(url)
        headers = HEADERS_BASE.copy()
        
        is_restricted = any(domain in parsed.netloc for domain in ["futtv", "indianservers", "embedindia", "workers.dev"])
        
        if is_restricted:
             headers["Referer"] = "https://embedindia.st/"
             headers["Origin"] = "https://embedindia.st"
        else:
            headers["Referer"] = "https://damitv.st/"
            headers["Origin"] = "https://damitv.st"

        # Tenta prima la chiamata diretta
        r = session.get(url, headers=headers, timeout=5, stream=True, allow_redirects=True)
        
        # Se riceve 403 sui domini restrittivi, ritenta passando da un Proxy
        if r.status_code == 403 and is_restricted:
            print(f"[PROXY TRIGGER] 403 Rilevato su {parsed.netloc}. Tentativo con Proxy...")
            proxy = get_working_proxy()
            if proxy:
                r = requests.get(url, headers=headers, proxies=proxy, timeout=5, stream=True, allow_redirects=True)

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
    
    # Priorità ai domini che rispondono 200 senza blocchi da Render
    base_domains = [
        "messi.damitv.st",
        "damitv.st",
        "india.futtv.nx.kg"
    ]
    
    paths = [
        f"{slug}/tracks-v1a1/mono.m3u8",
        f"{slug}/tracks-v1a1/mono.ts.m3u8",
        f"ucl/{today_str}/{slug}/mono.m3u8",
        f"ucl/{today_str}/{slug}/tracks-v1a1/mono.m3u8",
        f"ucl/{today_str}/{slug}/mono.ts.m3u8",
        f"ucl/{today_str}/{slug}/index.m3u8",
        f"{today_str}/{slug}/index.m3u8",
        f"{slug}/index.m3u8"
    ]
    
    if token:
        paths.append(f"secure/{token}/{expire}/1788969600/{slug}/tracks-v1a1/mono.ts.m3u8")
    
    urls = []
    for domain in base_domains:
        for path in paths:
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

# ==========================================
# ROTTE FLASK
# ==========================================

@app.route('/')
def home():
    return "Proxy attivo e pronto.", 200

@app.route('/debug/<path:slug>')
def debug_slug(slug):
    """Rotta per verificare in diretta quali server rispondono 200 o 403"""
    clean_slug = slug.replace(".m3u8", "")
    session = requests.Session()
    urls_to_test = generate_full_test_urls(clean_slug)
    
    report = [f"=== TEST DIAGNOSTICO PER SLUG: '{clean_slug}' ==="]
    
    for url in urls_to_test:
        parsed = urlparse(url)
        headers = HEADERS_BASE.copy()
        is_restricted = any(domain in parsed.netloc for domain in ["futtv", "indianservers", "embedindia"])
        headers["Referer"] = "https://embedindia.st/" if is_restricted else "https://damitv.st/"
        
        try:
            r = session.get(url, headers=headers, timeout=3, stream=True)
            status = r.status_code
            
            if status == 403 and is_restricted:
                proxy = get_working_proxy()
                if proxy:
                    r_proxy = requests.get(url, headers=headers, proxies=proxy, timeout=4, stream=True)
                    report.append(f"[PROXY TEST] {url} -> Diretto: 403 | Con Proxy: {r_proxy.status_code}")
                else:
                    report.append(f"[BLOCCATO 403] {url} (Nessun proxy disponibile)")
            else:
                report.append(f"[STATUS {status}] -> {url}")
        except Exception as e:
            report.append(f"[FAIL] -> {url} ({e})")
            
    return "<br>".join(report), 200

@app.route('/proxy')
def proxy_m3u8():
    target_url = request.args.get('url')
    if not target_url:
        return "URL mancante", 400
    
    parsed = urlparse(target_url)
    headers = HEADERS_BASE.copy()
    
    if any(domain in parsed.netloc for domain in ["futtv", "indianservers", "embedindia", "workers.dev"]):
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
