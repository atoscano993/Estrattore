import re
import requests
from flask import Flask, redirect

app = Flask(__name__)

HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://htsport.org/",
    "Origin": "https://htsport.org"
}

def universal_deobfuscate(html_content):
    """ Tenta di decifrare qualsiasi blocco XOR/Array dinamico trovato nell'HTML """
    try:
        # Cerca qualsiasi array di numeri lungo almeno 20 elementi: [240, 255, 248...]
        arrays = re.findall(r'\[([0-9,\s]{50,})\]', html_content)
        
        # Cerca tutti i numeri isolati assegnati a variabili nei paraggi (es. _qp4=16, _jj5=122)
        vars_found = [int(x) for x in re.findall(r'=\s*(\d{1,3})\s*;', html_content)]
        
        for arr_str in arrays:
            il2 = [int(x.strip()) for x in arr_str.split(',') if x.strip().isdigit()]
            if len(il2) < 20:
                continue

            # Se trova le variabili prova le combinazioni, altrimenti fa un brute-force velocissimo
            for qp4 in (vars_found if vars_found else range(0, 256)):
                for jj5 in range(0, 256):
                    try:
                        decoded_chars = [chr(((val ^ qp4) - jj5 + 256) & 255) for val in il2]
                        decoded_str = "".join(decoded_chars)
                        
                        # Se nella stringa decodificata compare .m3u8 o jwplayer abbiamo fatto centro!
                        if ".m3u8" in decoded_str or "jwplayer" in decoded_str:
                            match_m3u8 = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', decoded_str)
                            if match_m3u8:
                                return match_m3u8.group(1).replace(r'\/', '/')
                    except Exception:
                        continue
    except Exception as e:
        print(f"Errore deobfuscation: {e}")
    return None

@app.route('/htsport/<page_name>.m3u8')
def get_htsport_dynamic(page_name):
    try:
        session = requests.Session()
        session.headers.update(HEADERS_BASE)
        
        # 1. Pagina HTSport
        target_url = f"https://htsport.org/{page_name}.htm"
        resp = session.get(target_url, timeout=10)
        if resp.status_code != 200:
            # Prova la versione senza "hd" o viceversa se fallisce
            alt_name = page_name.replace("hd", "") if "hd" in page_name else f"{page_name}hd"
            target_url = f"https://htsport.org/{alt_name}.htm"
            resp = session.get(target_url, timeout=10)
            if resp.status_code != 200:
                return f"Pagina {page_name} non trovata su HTSport", 404

        # 2. Estrazione Iframe
        match_iframe = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', resp.text, re.IGNORECASE)
        if not match_iframe:
            return "Iframe del player non trovato", 404

        iframe_url = match_iframe.group(1)
        if iframe_url.startswith("//"):
            iframe_url = f"https:{iframe_url}"

        # 3. Download Iframe con Referer corretto
        session.headers.update({
            "Referer": target_url,
            "Sec-Fetch-Dest": "iframe",
            "Sec-Fetch-Mode": "navigate"
        })
        iframe_resp = session.get(iframe_url, timeout=10)
        
        if iframe_resp.status_code == 200:
            html_content = iframe_resp.text

            # Metodo 1: Decodifica Algoritmo JS
            stream_url = universal_deobfuscate(html_content)
            if stream_url:
                return redirect(stream_url, code=302)

            # Metodo 2: Link diretto in chiaro
            match_m3u8 = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', html_content)
            if match_m3u8:
                return redirect(match_m3u8.group(1).replace(r'\/', '/'), code=302)

        return "Impossibile estrarre il flusso .m3u8 dal player", 404

    except Exception as e:
        return f"Errore server: {e}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
