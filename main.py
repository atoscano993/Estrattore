import re
import requests
from flask import Flask, redirect

app = Flask(__name__)

# URL dell'embed interno che genera le chiavi temporanee
EMBED_URL = "https://tvnow247.top/embed/sky-sport-uno-italy/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://htsport.org/",
    "Origin": "https://htsport.org"
}

@app.route('/sportuno.m3u8')
def get_stream():
    try:
        session = requests.Session()
        
        # 1. Effettua la richiesta all'embed di tvnow247.top
        response = session.get(EMBED_URL, headers=HEADERS, timeout=10)
        html = response.text

        # 2. Cerca il flusso m3u8 direttamente o tramite regex sui parametri
        m3u8_match = re.search(r'(https?://[^\s\'"]+\.m3u8[^\s\'"]*)', html)
        
        if m3u8_match:
            final_url = m3u8_match.group(1)
            # Gestisce eventuali virgolette residue nel matching
            final_url = final_url.split('"')[0].split("'")[0]
            return redirect(final_url, code=302)

        # 3. Se il link m3u8 è spezzato/costruito in variabili JS, estraiamo le componenti (id stream, e, k)
        stream_id_match = re.search(r'live/(\d+)/index\.m3u8', html) or re.search(r'id:\s*["\'](\d+)["\']', html)
        e_match = re.search(r'[?&]e=(\d+)', html) or re.search(r'e\s*:\s*["\']?(\d+)["\']?', html)
        k_match = re.search(r'[?&]k=([a-f0-9]+)', html) or re.search(r'k\s*:\s*["\']?([a-f0-9]+)["\']?', html)

        if e_match and k_match:
            stream_id = stream_id_match.group(1) if stream_id_match else "461"
            e_val = e_match.group(1)
            k_val = k_match.group(1)
            constructed_url = f"https://live.tv247.site/live/{stream_id}/index.m3u8?v=1&e={e_val}&k={k_val}"
            return redirect(constructed_url, code=302)

        return "Impossibile estrarre i parametri del flusso video", 404

    except Exception as e:
        return f"Errore server: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
