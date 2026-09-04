import re
import requests
from flask import Flask, redirect

app = Flask(__name__)

HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7"
}

# --- ROTTA VECCHIA / DIRETTA (Compatibilità) ---
@app.route('/<page_name>.m3u8')
def get_direct_stream(page_name):
    return get_twnow247_dynamic(page_name)

# --- ROTTA TWNOW247 ---
@app.route('/twnow247/<page_name>.m3u8')
def get_twnow247_dynamic(page_name):
    clean_name = page_name.replace(".m3u8", "")
    try:
        session = requests.Session()
        session.headers.update(HEADERS_BASE)
        session.headers.update({"Referer": "https://tvnow247.top/"})
        
        target_url = f"https://tvnow247.top/{clean_name}.php"
        resp = session.get(target_url, timeout=10)
        
        if resp.status_code == 200:
            match_m3u8 = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', resp.text)
            if match_m3u8:
                return redirect(match_m3u8.group(1).replace(r'\/', '/'), code=302)
            
            # Controllo eventuale iframe interno
            match_iframe = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', resp.text, re.IGNORECASE)
            if match_iframe:
                iframe_url = match_iframe.group(1)
                if iframe_url.startswith("//"): iframe_url = f"https:{iframe_url}"
                iframe_resp = session.get(iframe_url, timeout=10)
                match_m3u8_iframe = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', iframe_resp.text)
                if match_m3u8_iframe:
                    return redirect(match_m3u8_iframe.group(1).replace(r'\/', '/'), code=302)

        return "Impossibile estrarre il flusso TWNow247", 404
    except Exception as e:
        return f"Errore TWNow247: {e}", 500

# --- ROTTA HTSPORT ---
@app.route('/htsport/<page_name>.m3u8')
def get_htsport_dynamic(page_name):
    clean_name = page_name.replace(".m3u8", "")
    try:
        session = requests.Session()
        session.headers.update(HEADERS_BASE)
        session.headers.update({"Referer": "https://htsport.org/"})

        target_url = f"https://htsport.org/{clean_name}.htm"
        resp = session.get(target_url, timeout=10)
        
        if resp.status_code != 200:
            return f"Pagina HTSport non trovata (HTTP {resp.status_code})", 404

        # 1. Trova l'iframe del player
        match_iframe = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', resp.text, re.IGNORECASE)
        if not match_iframe:
            return "Iframe HTSport non trovato nella pagina", 404

        iframe_url = match_iframe.group(1)
        if iframe_url.startswith("//"): iframe_url = f"https:{iframe_url}"

        # 2. Visita l'iframe con il Referer della pagina madre
        session.headers.update({"Referer": target_url})
        iframe_resp = session.get(iframe_url, timeout=10)

        if iframe_resp.status_code == 200:
            # Ricerca diretta nell'HTML/JS dell'iframe
            match_m3u8 = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', iframe_resp.text)
            if match_m3u8:
                return redirect(match_m3u8.group(1).replace(r'\/', '/'), code=302)

            # Ricerca eventuale chiamata ad API interna del player
            match_api = re.search(r'["\'](https?://[^"\']+/api/[^"\']+)["\']', iframe_resp.text)
            if match_api:
                api_url = match_api.group(1).replace(r'\/', '/')
                session.headers.update({"Referer": iframe_url})
                api_resp = session.get(api_url, timeout=10)
                if api_resp.status_code == 200:
                    match_m3u8_api = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', api_resp.text)
                    if match_m3u8_api:
                        return redirect(match_m3u8_api.group(1).replace(r'\/', '/'), code=302)

        return "Impossibile estrarre il flusso HTSport", 404

    except Exception as e:
        return f"Errore HTSport: {e}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
