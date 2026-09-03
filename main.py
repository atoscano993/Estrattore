import requests
from flask import Flask, redirect

app = Flask(__name__)

# Mappatura dei nomi personalizzati agli ID reali del sito (facoltativo ma comodo)
CHANNEL_MAP = {
    "sportuno": "461",
    "sportcalcio": "870"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://tvnow247.top/",
    "Origin": "https://tvnow247.top"
}

@app.route('/<channel_name>.m3u8')
def get_stream(channel_name):
    try:
        # Se il nome è nella mappa usiamo l'ID associato, altrimenti usiamo direttamente l'ID passato nell'URL
        stream_id = CHANNEL_MAP.get(channel_name.lower(), channel_name)
        
        # Chiamata dinamica all'API usando lo stream_id
        api_url = f"https://chat.cfbu247.sbs/api/resolve-dlstream/{stream_id}"
        response = requests.get(api_url, headers=HEADERS, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            stream_url = data.get("m3u8") or data.get("proxyPlaylistUrl")
            
            if stream_url:
                return redirect(stream_url, code=302)
        
        return f"Flusso per il canale '{channel_name}' (ID: {stream_id}) non disponibile", 404

    except Exception as e:
        return f"Errore server: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
