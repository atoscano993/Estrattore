import re
import time
from flask import Flask, redirect
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import chromedriver_binary  # Configura automaticamente il path di ChromeDriver

app = Flask(__name__)

def extract_m3u8_with_selenium(target_url, referer_header):
    """
    Apre la pagina tramite Chrome Headless, analizza i log di rete e 
    l'HTML renders per individuare l'URL del flusso .m3u8 tokenizzato.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Abilita la registrazione del traffico di rete nei log di Chrome
    chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = None
    extracted_url = None

    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(15)
        
        # Caricamento della pagina iniziale
        driver.get(target_url)
        time.sleep(3)

        # 1. Cerca l'iframe nell'HTML per reindirizzare la navigazione
        page_source = driver.page_source
        match_iframe = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', page_source, re.IGNORECASE)
        
        if match_iframe:
            iframe_url = match_iframe.group(1)
            if iframe_url.startswith("//"):
                iframe_url = f"https:{iframe_url}"
            driver.get(iframe_url)
            time.sleep(3)

        # 2. Analisi dei log di rete registrati da Chrome per estrarre l'URL .m3u8
        logs = driver.get_log("performance")
        for entry in logs:
            log_message = entry.get("message", "")
            if ".m3u8" in log_message:
                match_url = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', log_message)
                if match_url:
                    extracted_url = match_url.group(1).replace(r'\/', '/')
                    break

        # Fallback: ricerca diretta nel sorgente finale della pagina
        if not extracted_url:
            match_source = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', driver.page_source)
            if match_source:
                extracted_url = match_source.group(1).replace(r'\/', '/')

    except Exception as e:
        print(f"Errore durante l'estrazione Selenium per {target_url}: {e}")
    finally:
        if driver:
            driver.quit()

    return extracted_url


# --- Rotta HTSPORT ---
@app.route('/htsport/<page_name>.m3u8')
def get_htsport_dynamic(page_name):
    clean_name = page_name.replace(".m3u8", "")
    target_url = f"https://htsport.org/{clean_name}.htm"
    
    stream_url = extract_m3u8_with_selenium(target_url, referer_header="https://htsport.org/")
    
    if stream_url:
        return redirect(stream_url, code=302)
    return "Impossibile estrarre il flusso HTSport", 404


# --- Rotta TWNOW247 ---
@app.route('/twnow247/<page_name>.m3u8')
def get_twnow247_dynamic(page_name):
    clean_name = page_name.replace(".m3u8", "")
    target_url = f"https://twnow247.com/{clean_name}.php"
    
    stream_url = extract_m3u8_with_selenium(target_url, referer_header="https://twnow247.com/")
    
    if stream_url:
        return redirect(stream_url, code=302)
    return "Impossibile estrarre il flusso TWNow247", 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
