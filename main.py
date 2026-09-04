import re
import requests
from flask import Flask, redirect

app = Flask(__name__)

HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://htsport.org/",
    "Origin": "https://htsport.org"
}

def decode_obfuscated_script(html_content):
    """ Decodifica lo script XOR dinamico di EpiEmbeds """
    try:
        # Cerca l'array di interi _il2 e le variabili di cifratura _qp4 e _jj5
        match_il2 = re.search(r'_il2\s*=\s*\[([0-9,\s]+)\]', html_content)
        match_qp4 = re.search(r'_qp4\s*=\s*(\d+)', html_content)
        match_jj5 = re.search(r'_jj5\s*=\s*(\d+)', html_content)

        if match_il2 and match_qp4 and match_jj5:
            il2 = [int(x.strip()) for x in match_il2.group(1).split(',')]
            qp4 = int(match_qp4.group(1))
            jj5 = int(match_jj5.group(1))

            # Algoritmo di decodifica replica esatta del JS: ((val ^ _qp4) - _jj5 + 256) & 255
            decoded_chars = []
            for val in il2:
                char_code = ((val ^ qp4) - jj5 + 256) & 255
                decoded_chars.append(chr(char_code))

            decoded_script = "".join(decoded_chars)
            
            # Estrarre l'URL .m3u8 dal codice decodificato
            match_m3u8 = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', decoded_script)
            if match_m3u8:
                return match_m3u8.group(1).replace(r'\/', '/')
    except Exception as e:
        print(f"Errore durante la decodifica XOR: {e}")
    return None


@app.route('/htsport/<page_name>.m3u8')
def get_htsport_dynamic(page_name):
    try:
        session = requests.Session()
        session.headers.update(HEADERS_BASE)
        
        # 1. Carica la pagina principale HTSport (es. dazn1hd.htm o dazn1.htm)
        target_url = f"https://htsport.org/{page_name}.htm"
        resp = session.get(target_url, timeout=10)
        if resp.status_code != 200:
            return f"Pagina {target_url} non trovata", 404

        # 2. Cerca l'iframe di EpiEmbeds
        match_iframe = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', resp.text, re.IGNORECASE)
        if not match_iframe:
            return "Iframe del player non trovato", 404

        iframe_url = match_iframe.group(1)
        if iframe_url.startswith("//"):
            iframe_url = f"https:{iframe_url}"

        # 3. Scarica il codice dell'iframe
        session.headers.update({"Referer": target_url})
        iframe_resp = session.get(iframe_url, timeout=10)
        
        if iframe_resp.status_code == 200:
            html_content = iframe_resp.text

            # Tentativo 1: Decodifica dello script obfuscato EpiEmbeds
            stream_url = decode_obfuscated_script(html_content)
            if stream_url:
                return redirect(stream_url, code=302)

            # Tentativo 2: Ricerca diretta in chiaro
            match_m3u8 = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', html_content)
            if match_m3u8:
                return redirect(match_m3u8.group(1).replace(r'\/', '/'), code=302)

        return "Impossibile estrarre il flusso .m3u8 dal player", 404

    except Exception as e:
        return f"Errore server: {e}", 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
