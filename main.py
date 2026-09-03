import re
import requests
from flask import Flask, redirect

app = Flask(__name__)

# Mappatura dei nomi personalizzati agli ID reali per i canali TVNOW
TVNOW_MAP = {
    "sportuno": "461",
    "sportcalcio": "870",
    "sportf1": "577",
    "sportmoto": "575",
    "sportmax": "460",
    "sporttennis": "576
}

# Mappatura per i canali WideIPTV (aggiungiamo qui Sky Sport 24)
WIDE_MAP = {
    "sport24": "SkySport24IT"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://htsport.org/",
    "Origin": "https://htsport.org"
}

@app.route('/<channel_name>.m3u8')
def get_stream(channel_name):
    name_clean = channel_name.lower()
    
    # --- STRATEGIA 1: Canali TVNOW ---
    if name_clean in TVNOW_MAP or name_clean.isdigit():
        stream_id = TVNOW_MAP.get(name_clean, channel_name)
        try:
            api_url = f"https://chat.cfbu247.sbs/api/resolve-dlstream/{stream_id}"
            response = requests.get(api_url, headers=HEADERS, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                stream_url = data.get("m3u8") or data.get("proxyPlaylistUrl")
                if stream_url:
                    return redirect(stream_url, code=302)
        except Exception as e:
            print(f"Errore TVNOW: {e}")

    # --- STRATEGIA 2: Canali WideIPTV (es. Sky Sport 24) ---
    wide_slug = WIDE_MAP.get(name_clean, channel_name)
    try:
        player_url = f"https://wideiptv.top/player/{wide_slug}"
        response = requests.get(player_url, headers=HEADERS, timeout=10)
        
        if response.status_code == 200:
            # Cerca 'streamUrl: "https:\/\/..."' nella pagina HTML di wideiptv
            match = re.search(r'streamUrl:\s*["\']([^"\']+)["\']', response.text)
            if match:
                # Converte i separatori \/ in / per avere un URL m3u8 valido
                stream_url = match.group(1).replace(r'\/', '/')
                return redirect(stream_url, code=302)
    except Exception as e:
        print(f"Errore WideIPTV: {e}")

    return f"Flusso per il canale '{channel_name}' non disponibile su nessun provider", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
