import requests
from flask import Flask

app = Flask(__name__)

EMBED_URL = "https://tvnow247.top/embed/sky-sport-uno-italy/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://htsport.org/",
    "Origin": "https://htsport.org"
}

@app.route('/sportuno.m3u8')
def get_stream():
    try:
        response = requests.get(EMBED_URL, headers=HEADERS, timeout=10)
        # Mostra il testo della pagina web direttamente a schermo
        return f"<pre>{response.text[:2000]}</pre>"
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
