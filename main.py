import os
import re
import requests
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
# FUNZIONI DI RESOLUTION
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
    """Estrae l'm3u8 nativo tramite API interne di DamITV"""
    try:
        clean_id = damitv_id.lstrip('/')
        match_id = clean_id.split('/')[-1] if '/' in clean_id else clean_id

        session = requests.Session()
        session.headers.update(HEADERS_DAMITV)

        token = ""
        try:
            r_sess = session.get("https://damitv.st/papi/ad-session", timeout=5)
            if r_sess.status_code == 200:
                sid = r_sess.json().get("s", "")
                if sid:
                    r_ver = session.get(f"https://damitv.st/papi/ad-verify?s={sid}", timeout=5)
                    if r_ver.status_code == 200:
                        token = r_ver.json().get("t", "")
        except Exception as e:
            print(f"[DAMITV TOKEN WARN] {e}")

        if "ch=" in clean_id or clean_id.startswith("sky-") or clean_id.startswith("dazn-"):
            ch_id = clean_id.replace("ch=", "")
            url_ch = f"https://damitv.st/papi/tv/resolve/{ch_id}?t={token}"
            r_ch = session.get(url_ch, timeout=5)
            if r_ch.status_code == 200:
                data = r_ch.json()
                if data.get("stream") or data.get("url"):
                    return data.get("stream") or data.get("url")

        extract_url = f"https://damitv.st/papi/extract-url/{clean_id}"
        r_ext = session.get(extract_url, timeout=5)
        
        if r_ext.status_code != 200 and match_id != clean_id:
            extract_url = f"https://damitv.st/papi/extract-url/{match_id}"
            r_ext = session.get(extract_url, timeout=5)

        if r_ext.status_code == 200:
            data = r_ext.json()
            if data.get("success") and data.get("hlsUrl"):
                return data.get("hlsUrl")

    except Exception as e:
        print(f"[DAMITV RESOLVE ERROR] {e}")
    
    return None

def find_damitv_match_by_team(team_key):
    try:
        keywords = SERIE_A_TEAMS.get(team_key, [team_key])
        schedule_url = "https://damitv.st/schedule/"
        res = requests.get(schedule_url, headers=HEADERS_DAMITV, timeout=6)
        if res.status_code == 200:
            html_content = res.text.lower()
            found_urls = re.findall(r'(?:href=["\']|id=)([^"\'\s>]*?(?:seriea|embed|event)[^"\'\s>]*)', html_content, re.IGNORECASE)
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
    return "Estrattore attivo (TVNow + DamITV)", 200

# ROTTA DI DEBUG DEDICATA
@app.route('/debug-dami')
def debug_dami():
    target_id = request.args.get('id', 'seriea/2026-09-07/cag-lec')
    stream_found = resolve_damitv_stream(target_id)
    if stream_found:
        return f"<h3>Stream Estratto con Successo:</h3><p>URL: {stream_found}</p><p><a href='/proxy?url={requests.utils.quote(stream_found)}'>Testa tramite Proxy</a></p>"
    return f"Impossibile estrarre lo stream per '{target_id}' tramite API.", 500

@app.route('/proxy')
def proxy_m3u8():
    """Proxy con spoofing completo degli header di DamITV"""
    target_url = request.args.get('url')
    if not target_url:
        return "URL mancante", 400
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://damitv.st/",
        "Origin": "https://damitv.st",
        "Accept": "*/*",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site"
    }

    try:
        res = requests.get(target_url, headers=headers, timeout=10, stream=True)
        if res.status_code == 200:
            content_type = res.headers.get('Content-Type', '')
            
            if ".m3u8" in target_url or "mpegurl" in content_type:
                base_url = target_url.rsplit('/', 1)[0] + '/'
                lines = res.text.splitlines()
                new_lines = []
                for line in lines:
                    line_str = line.strip()
                    if line_str and not line_str.startswith('#'):
                        if not line_str.startswith('http'):
                            full_segment_url = base_url + line_str
                        else:
                            full_segment_url = line_str
                        line_str = f"/proxy?url={requests.utils.quote(full_segment_url)}"
                    new_lines.append(line_str)
                
                rewritten_m3u8 = "\n".join(new_lines)
                return Response(rewritten_m3u8, mimetype='application/vnd.apple.mpegurl')
            
            return Response(res.iter_content(chunk_size=1024*64), content_type=content_type)
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
