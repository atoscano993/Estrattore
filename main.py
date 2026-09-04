# --- 3. ROTTA DINAMICA HTSPORT (UNIVERSALE PER TVNOW & WIDEIPTV) ---
@app.route('/htsport/<page_name>.m3u8')
def get_htsport_dynamic(page_name):
    try:
        target_url = f"https://htsport.org/{page_name}.htm"
        page_resp = requests.get(target_url, headers=HEADERS_HTSPORT, timeout=7)
        
        if page_resp.status_code != 200:
            return f"Pagina {target_url} non trovata (HTTP {page_resp.status_code})", 404
            
        html = page_resp.text

        # 1. CASO A: Il player è TVNow/CFBU (cerca l'ID nel codice o negli iframe)
        match_tvnow = re.search(r'(?:resolve-dlstream/|id=)(\d+)', html)
        if match_tvnow:
            stream_id = match_tvnow.group(1)
            api_url = f"https://chat.cfbu247.sbs/api/resolve-dlstream/{stream_id}"
            resp = requests.get(api_url, headers=HEADERS_TVNOW, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                stream_url = data.get("m3u8") or data.get("proxyPlaylistUrl")
                if stream_url:
                    return redirect(stream_url, code=302)

        # 2. CASO B: Il player è WideIPTV
        match_wide = re.search(r'src=["\'](https?://wideiptv\.top/player/[^"\']+)["\']', html)
        if match_wide:
            player_url = match_wide.group(1)
            headers_wide = {
                "User-Agent": HEADERS_HTSPORT["User-Agent"],
                "Referer": "https://htsport.org/",
                "Origin": "https://htsport.org"
            }
            player_resp = requests.get(player_url, headers=headers_wide, timeout=7)
            if player_resp.status_code == 200:
                match_stream = re.search(r'streamUrl:\s*["\']([^"\']+)["\']', player_resp.text)
                if match_stream:
                    stream_url = match_stream.group(1).replace(r'\/', '/')
                    return redirect(stream_url, code=302)

        # 3. CASO C: Iframe generico verso TVNow o servizi simili
        iframe_src = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if iframe_src:
            sub_url = iframe_src.group(1)
            if not sub_url.startswith("http"):
                sub_url = f"https://htsport.org/{sub_url.lstrip('/')}"
            
            sub_resp = requests.get(sub_url, headers=HEADERS_HTSPORT, timeout=7)
            if sub_resp.status_code == 200:
                # Ricerca ID TVNow nell'iframe di secondo livello
                match_sub_tvnow = re.search(r'resolve-dlstream/(\d+)', sub_resp.text)
                if match_sub_tvnow:
                    stream_id = match_sub_tvnow.group(1)
                    api_url = f"https://chat.cfbu247.sbs/api/resolve-dlstream/{stream_id}"
                    resp = requests.get(api_url, headers=HEADERS_TVNOW, timeout=5)
                    if resp.status_code == 200:
                        stream_url = resp.json().get("m3u8") or resp.json().get("proxyPlaylistUrl")
                        if stream_url:
                            return redirect(stream_url, code=302)

        return "Nessun player compatibile estratto dalla pagina HTSport", 404

    except Exception as e:
        return f"Errore Dynamic: {e}", 500
