import requests
from flask import Flask, redirect

app = Flask(__name__)

RESOLVE_API_URL = "https://chat.cfbu247.sbs/api/resolve-dlstream/461"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://tvnow247.top/",
    "Origin": "https://tvnow247.top"
}

@app.route('/sportuno.m3u8')
def get_stream():
    try:
        response = requests.get(RESOLVE_API_URL, headers=HEADERS, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # Estrae direttamente il link generato dall'API
            stream_url = data.get("m3u8") or data.get("proxyPlaylistUrl")
            
            if stream_url:
                # Reindirizza IPTV Smarters Pro al flusso attivo
                return redirect(stream_url, code=302)
        
        return "Flusso non disponibile", 404

    except Exception as e:
        return f"Errore server: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
