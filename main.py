import re
import requests
from flask import Flask, redirect

app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7"
}

@app.route('/twnow247/<page_name>.m3u8')
def debug_twnow(page_name):
    clean_name = page_name.replace(".m3u8", "")
    target_url = f"https://tvnow247.top/{clean_name}.php"
    
    session = requests.Session()
    session.headers.update(HEADERS)
    session.headers.update({"Referer": "https://tvnow247.top/"})
    
    try:
        resp = session.get(target_url, timeout=10)
        
        # Cerca link m3u8 o iframe nel sorgente HTML
        match_m3u8 = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', resp.text)
        if match_m3u8:
            return redirect(match_m3u8.group(1).replace(r'\/', '/'), code=302)
            
        match_iframe = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', resp.text, re.IGNORECASE)
        if match_iframe:
            iframe_url = match_iframe.group(1)
            if iframe_url.startswith("//"): iframe_url = f"https:{iframe_url}"
            
            # Chiamata all'iframe
            session.headers.update({"Referer": target_url})
            iframe_resp = session.get(iframe_url, timeout=10)
            
            match_m3u8_iframe = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', iframe_resp.text)
            if match_m3u8_iframe:
                return redirect(match_m3u8_iframe.group(1).replace(r'\/', '/'), code=302)
                
            # Mostra l'HTML dell'iframe per capire come nascondono il flusso
            return f"<b>Contenuto dell'iframe ({iframe_url}):</b><br><textarea style='width:100%;height:300px;'>{iframe_resp.text}</textarea>"

        # Mostra l'HTML della pagina principale se non c'è iframe
        return f"<b>Nessun iframe o m3u8 trovato in {target_url}:</b><br><textarea style='width:100%;height:300px;'>{resp.text}</textarea>"

    except Exception as e:
        return f"Errore di connessione: {e}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
