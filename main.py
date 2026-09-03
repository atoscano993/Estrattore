import requests
from flask import Flask, redirect, jsonify

app = Flask(__name__)

# API reale per risolvere il flusso del canale 461
RESOLVE_API_URL = "https://chat.cfbu247.sbs/api/resolve-dlstream/461"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://tvnow247.top/",
    "Origin": "https://tvnow247.top"
}

@app.route('/sportuno.m3u8')
def get_stream():
    try:
        # 1. Richiedi i dati aggiornati all'API
        response = requests.get(RESOLVE_API_URL, headers=HEADERS, timeout=10)
        
        if response.status_code != 200:
            return f"Errore risposta API: status {response.status_code}", 502

        data = response.json()

        # 2. Estrai l'URL m3u8 o componilo se l'API restituisce i token separati
        stream_url = data.get("url") or data.get("stream") or data.get("file") or data.get("result")

        # Se l'API restituisce l'URL completo
        if stream_url and ".m3u8" in stream_url:
            return redirect(stream_url, code=302)

        # Se l'API restituisce i token (es. {"e": "...", "k": "..."})
        if "e" in data and "k" in data:
            e_val = data["e"]
            k_val = data["k"]
            stream_id = data.get("id", "461")
            constructed_url = f"https://live.tv247.site/live/{stream_id}/index.m3u8?v=1&e={e_val}&k={k_val}"
            return redirect(constructed_url, code=302)

        # Se la struttura JSON è imprevista, la mostriamo per il debug
        return jsonify(data)

    except Exception as e:
        return f"Errore durante l'estrazione: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
