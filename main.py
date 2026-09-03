import re
import requests
from flask import Flask, redirect

app = Flask(__name__)

PAGE_URL = "https://htsport.org/sportunohd.htm"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://htsport.org/"
}

@app.route('/sportuno.m3u8')
def get_stream():
    try:
        # 1. Scarica la pagina principale
        session = requests.Session()
        res = session.get(PAGE_URL, headers=HEADERS, timeout=10)
        
        # 2. Cerca se c'è un iframe nella pagina
        iframe_match = re.search(r'iframe[^\">]+src=["\']([^"\']+)["\']', res.text, re.IGNORECASE)
        
        target_html = res.text
        if iframe_match:
            iframe_url = iframe_match.group(1)
            if not iframe_url.startswith("http"):
                iframe_url = "https://htsport.org/" + iframe_url.lstrip('/')
            # Scarica il contenuto dell'iframe
            res_iframe = session.get(iframe_url, headers=HEADERS, timeout=10)
            target_html = res_iframe.text

        # 3. Cerca il link .m3u8 nel codice ottenuto
        m3u8_match = re.search(r'(https?://[^\s\'"]+\.m3u8[^\s\'"]*)', target_html)
        
        if m3u8_match:
            final_url = m3u8_match.group(1)
            return redirect(final_url, code=302)
        else:
            return "Impossibile trovare il link m3u8 nella pagina o nell'iframe.", 404

    except Exception as e:
        return f"Errore durante l'estrazione: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
