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
        
        # 1. Pagina Principale HTSport
        target_url = f"https://htsport.org/{page_name}.htm"
        resp = session.get(target_url, timeout=10)
        if resp.status_code != 200:
            return f"Pagina {target_url} non trovata", 404

        # 2. Estrazione Iframe
        match_iframe = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', resp.text, re.IGNORECASE)
        if not match_iframe:
            return "Iframe del player non trovato", 404

        iframe_url = match_iframe.group(1)
        if iframe_url.startswith("//"):
            iframe_url = f"https:{iframe_url}"

        # 3. Richiesta al Player Embed
        session.headers.update({"Referer": target_url})
        iframe_resp = session.get(iframe_url, timeout=10)
        
        if iframe_resp.status_code == 200:
            content = iframe_resp.text
            
            # Pattern A: Link diretto .m3u8
            match_m3u8 = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', content)
            if match_m3u8:
                return redirect(match_m3u8.group(1).replace(r'\/', '/'), code=302)

            # Pattern B: Estrazione URL dal dominio dello Stream Host (cdx-*.website)
            match_cdx = re.search(r'["\'](https?://[^"\']*cdx-[^"\']+\.m3u8[^"\']*)["\']', content)
            if match_cdx:
                return redirect(match_cdx.group(1).replace(r'\/', '/'), code=302)

            # Pattern C: Configurazione JS (file: "...", source: "...")
            match_js_source = re.search(r'(?:file|source|src)\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', content)
            if match_js_source:
                stream_url = match_js_source.group(1).replace(r'\/', '/')
                if not stream_url.startswith("http"):
                    stream_url = f"https:{stream_url}" if stream_url.startswith("//") else stream_url
                return redirect(stream_url, code=302)

        return "Impossibile estrarre il flusso dal player JS", 404

    except Exception as e:
        return f"Errore server: {e}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
