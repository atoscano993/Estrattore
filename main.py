import re
from flask import Flask, redirect
from playwright.sync_api import sync_playwright

app = Flask(__name__)

def extract_m3u8_with_browser(target_url, referer_header):
    """
    Apre la pagina con un browser Headless, esegue i JavaScript
    e intercetta la prima richiesta .m3u8 generata.
    """
    extracted_url = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            extra_http_headers={"Referer": referer_header}
        )
        page = context.new_page()

        # Ascolta le richieste di rete in background
        def handle_request(request):
            nonlocal extracted_url
            if ".m3u8" in request.url and not extracted_url:
                extracted_url = request.url

        page.on("request", handle_request)

        try:
            # 1. Carica la pagina principale
            page.goto(target_url, timeout=15000, wait_until="domcontentloaded")
            
            # 2. Se c'è un iframe, entra nell'iframe per velocizzare la generazione dell'm3u8
            content = page.content()
            match_iframe = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE)
            
            if match_iframe:
                iframe_url = match_iframe.group(1)
                if iframe_url.startswith("//"):
                    iframe_url = f"https:{iframe_url}"
                page.goto(iframe_url, timeout=15000, wait_until="networkidle")
            else:
                page.wait_for_timeout(4000)

        except Exception as e:
            print(f"Errore caricamento pagina ({target_url}): {e}")
        finally:
            browser.close()

    return extracted_url


# --- Rotta HTSPORT ---
@app.route('/htsport/<page_name>.m3u8')
def get_htsport_dynamic(page_name):
    clean_name = page_name.replace(".m3u8", "")
    target_url = f"https://htsport.org/{clean_name}.htm"
    
    stream_url = extract_m3u8_with_browser(target_url, referer_header="https://htsport.org/")
    
    if stream_url:
        return redirect(stream_url, code=302)
    return "Impossibile estrarre il flusso HTSport", 404


# --- Rotta TWNOW247 ---
@app.route('/twnow247/<page_name>.m3u8')
def get_twnow247_dynamic(page_name):
    clean_name = page_name.replace(".m3u8", "")
    # Costruisci l'URL di twnow247 (adatta la struttura URL se diversa)
    target_url = f"https://twnow247.com/{clean_name}.php"
    
    stream_url = extract_m3u8_with_browser(target_url, referer_header="https://twnow247.com/")
    
    if stream_url:
        return redirect(stream_url, code=302)
    return "Impossibile estrarre il flusso TWNow247", 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
