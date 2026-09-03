import re
import requests
from flask import Flask, redirect

app = Flask(__name__)

# URL della pagina sorgente
PAGE_URL = "https://htsport.org/sportunohd.htm"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://htsport.org/"
}

@app.route('/sportuno.m3u8')
def get_stream():
    try:
        # 1. Scarica la pagina web
        response = requests.get(PAGE_URL, headers=HEADERS, timeout=10)
        html = response.text
        
        # 2. Cerca il link .m3u8 usando un'espressione regolare nel codice sorgente
        match = re.search(r'(https?://[^\s\'"]+\.m3u8[^\s\'"]*)', html)
        
        if match:
            m3u8_url = match.group(1)
            # Reindirizza il lettore IPTV direttamente al link video trovato
            return redirect(m3u8_url, code=302)
        else:
            return "Link m3u8 non trovato nella pagina", 404
            
    except Exception as e:
        return f"Errore durante l'estrazione: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
