import re
import requests
from flask import Flask, redirect

app = Flask(__name__)

HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://htsport.org/",
    "Origin": "https://htsport.org"
}

@app.route('/htsport/<page_name>.m3u8')
def get_htsport_dynamic(page_name):
    try:
        session = requests.Session()
        session.headers.update(HEADERS_BASE)
        
        # 1. Carica la pagina di HTSport (es. dazn1hd.htm)
        target_url = f"https://htsport.org/{page_name}.htm"
        resp = session.get(target_url, timeout=10)
        if resp.status_code != 200:
            return f"Pagina {target_url} non trovata", 404

        # 2. Trova il link dell'iframe (es. epiembeds o altri)
        match_iframe = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', resp.text, re.IGNORECASE)
        if not match_iframe:
            return "Iframe del player non trovato nella pagina", 404

        iframe_url = match_iframe.group(1)
        if iframe_url.startswith("//"):
            iframe_url = f"https:{iframe_url}"

        # 3. Aggiorna il Referer e naviga dentro l'iframe
        session.headers.update({"Referer": target_url})
        iframe_resp = session.get(iframe_url, timeout=10)
        
        if iframe_resp.status_code == 200:
            # 4. Estrae qualsiasi URL .m3u8 presente nel codice HTML/JS dell'iframe
            # Cattura domini dinamici tipo hdesx.cdx-*.website/...
            match_m3u8 = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', iframe_resp.text)
            
            if match_m3u8:
                stream_url = match_m3u8.group(1).replace(r'\/', '/')
                return redirect(stream_url, code=302)

        return "Impossibile estrarre il flusso .m3u8 dinamico dal player", 404

    except Exception as e:
        return f"Errore server: {e}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
