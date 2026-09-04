import re
import requests
from flask import Flask, redirect

app = Flask(__name__)

HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7"
}

def decode_htsport_script(html_content):
    """ Decodifica lo script XOR dinamico di EpiEmbeds """
    try:
        match_il2 = re.search(r'_il2\s*=\s*\[([0-9,\s]+)\]', html_content)
        match_qp4 = re.search(r'_qp4\s*=\s*(\d+)', html_content)
        match_jj5 = re.search(r'_jj5\s*=\s*(\d+)', html_content)

        if match_il2 and match_qp4 and match_jj5:
            il2 = [int(x.strip()) for x in match_il2.group(1).split(',')]
            qp4 = int(match_qp4.group(1))
            jj5 = int(match_jj5.group(1))

            decoded_chars = [chr(((val ^ qp4) - jj5 + 256) & 255) for val in il2]
            decoded_script = "".join(decoded_chars)

            match_m3u8 = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', decoded_script)
            if match_m3u8:
                return match_m3u8.group(1).replace(r'\/', '/')
    except Exception as e:
        print(f"Errore decodifica XOR: {e}")
    return None

# --- ROTTA VECCHIA/DIRETTA PER TVNOW (Per non rompere i link vecchi) ---
@app.route('/<page_name>.m3u8')
def get_direct_stream(page_name):
    return get_twnow247_dynamic(page_name)

# --- ROTTA TWNOW247 ---
@app.route('/twnow247/<page_name>.m3u8')
def get_twnow247_dynamic(page_name):
    clean_name = page_name.replace(".m3u8", "")
    try:
        session = requests.Session()
        session.headers.update(HEADERS_BASE)
        session.headers.update({"Referer": "https://twnow247.com/"})
        
        target_url = f"https://twnow247.top/{clean_name}.php"
        resp = session.get(target_url, timeout=10)
        
        if resp.status_code == 200:
            match_m3u8 = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', resp.text)
            if match_m3u8:
                return redirect(match_m3u8.group(1).replace(r'\/', '/'), code=302)
            
            # Se è in un iframe
            match_iframe = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', resp.text, re.IGNORECASE)
            if match_iframe:
                iframe_url = match_iframe.group(1)
                if iframe_url.startswith("//"): iframe_url = f"https:{iframe_url}"
                iframe_resp = session.get(iframe_url, timeout=10)
                match_m3u8_iframe = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', iframe_resp.text)
                if match_m3u8_iframe:
                    return redirect(match_m3u8_iframe.group(1).replace(r'\/', '/'), code=302)

        return "Impossibile estrare il flusso TWNow247", 404
    except Exception as e:
        return f"Errore TWNow247: {e}", 500

# --- ROTTA HTSPORT ---
@app.route('/htsport/<page_name>.m3u8')
def get_htsport_dynamic(page_name):
    clean_name = page_name.replace(".m3u8", "")
    try:
        session = requests.Session()
        session.headers.update(HEADERS_BASE)
        session.headers.update({"Referer": "https://htsport.org/"})

        target_url = f"https://htsport.org/{clean_name}.htm"
        resp = session.get(target_url, timeout=10)
        
        if resp.status_code != 200:
            return f"Pagina {target_url} non raggiungibile (HTTP {resp.status_code})", 404

        match_iframe = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', resp.text, re.IGNORECASE)
        if not match_iframe:
            return "Iframe HTSport non trovato nella pagina", 404

        iframe_url = match_iframe.group(1)
        if iframe_url.startswith("//"): iframe_url = f"https:{iframe_url}"

        session.headers.update({"Referer": target_url})
        iframe_resp = session.get(iframe_url, timeout=10)

        if iframe_resp.status_code == 200:
            # Tenta decodifica XOR
            stream_url = decode_htsport_script(iframe_resp.text)
            if stream_url:
                return redirect(stream_url, code=302)

            # Tenta ricerca m3u8 in chiaro
            match_m3u8 = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', iframe_resp.text)
            if match_m3u8:
                return redirect(match_m3u8.group(1).replace(r'\/', '/'), code=302)

        return "Impossibile estrarre il flusso HTSport (Player protetto)", 404

    except Exception as e:
        return f"Errore HTSport: {e}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
