# searn_web.py
import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urlparse
from flask import Flask, render_template, request, Response
import json
import queue

app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "en-US,en;q=0.9",
}

# ---------------------------
# CONFIG
# ---------------------------
MAX_PASSES = 10
DDG_PAGES = 5

# ---------------------------
# QUERY EXPANSION
# ---------------------------
def generate_queries(q):
    return [
        q,
        f"{q} tutorial",
        f"{q} writeup",
        f"{q} exploit",
        f"site:github.io {q}",
        f'intitle:"index of" {q}',
    ]

# ---------------------------
# DOMAIN ROOT
# ---------------------------
def get_root_domain(url):
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        parts = host.split(".")
        if len(parts) >= 2:
            return parts[-2] + "." + parts[-1]
        return host
    except:
        return None

# ---------------------------
# FILTER
# ---------------------------
def is_valid(url):
    bad = [
        "captcha", "login", "support", "account",
        "consent", "privacy", "terms",
        "duckduckgo.com", "bing.com/aclick"
    ]
    return url.startswith("http") and not any(b in url.lower() for b in bad)

# ---------------------------
# CLEAN DDG REDIRECT
# ---------------------------
def clean_ddg(url):
    if "duckduckgo.com/l/?" in url:
        try:
            import urllib.parse as up
            parsed = up.urlparse(url)
            qs = up.parse_qs(parsed.query)
            return qs.get("uddg", [url])[0]
        except:
            return url
    return url

# ---------------------------
# DUCKDUCKGO
# ---------------------------
def ddg_stream(query, pass_no, seen, counter, send_func):
    send_func(f"\n[DDG][Pass {pass_no}] {query}")
    base = "https://html.duckduckgo.com/html/"

    for page in range(DDG_PAGES):
        data = {"q": query, "s": str(page * 30)}
        try:
            res = requests.post(base, data=data, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(res.text, "lxml")
            for a in soup.select("a.result__a"):
                raw = a.get("href")
                if not raw:
                    continue
                url = clean_ddg(raw)
                if not is_valid(url):
                    continue
                root = get_root_domain(url)
                if root and root not in seen:
                    seen[root] = url
                    counter[0] += 1
                    send_func(f"[{counter[0]:03}] [DDG] {url}")
            time.sleep(1)
        except:
            break

# ---------------------------
# YANDEX
# ---------------------------
def yandex_stream(query, pass_no, seen, counter, send_func):
    send_func(f"\n[Yandex][Pass {pass_no}] {query}")
    try:
        res = requests.get(f"https://yandex.com/search/?text={query}", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "lxml")
        for a in soup.select("a[href]"):
            link = a.get("href")
            if link and link.startswith("http") and is_valid(link):
                root = get_root_domain(link)
                if root and root not in seen:
                    seen[root] = link
                    counter[0] += 1
                    send_func(f"[{counter[0]:03}] [YND] {link}")
    except:
        pass

# ---------------------------
# BING
# ---------------------------
def bing_stream(query, pass_no, seen, counter, send_func):
    send_func(f"\n[BING][Pass {pass_no}] {query}")
    for page in range(3):
        url = f"https://www.bing.com/search?q={query}&first={page*10}"
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(res.text, "lxml")
            for a in soup.select("li.b_algo h2 a"):
                link = a.get("href")
                if link and is_valid(link):
                    root = get_root_domain(link)
                    if root and root not in seen:
                        seen[root] = link
                        counter[0] += 1
                        send_func(f"[{counter[0]:03}] [BING] {link}")
            time.sleep(1)
        except:
            break

# ---------------------------
# BRAVE SEARCH
# ---------------------------
def brave_stream(query, pass_no, seen, counter, send_func):
    send_func(f"\n[BRAVE][Pass {pass_no}] {query}")
    url = f"https://search.brave.com/search?q={query}&source=web"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "lxml")
        for a in soup.select("a[href]"):
            link = a.get("href")
            if link and link.startswith("http") and is_valid(link):
                root = get_root_domain(link)
                if root and root not in seen:
                    seen[root] = link
                    counter[0] += 1
                    send_func(f"[{counter[0]:03}] [BRV] {link}")
    except:
        pass

# ---------------------------
# MAIN SEARCH FUNCTION
# ---------------------------
def perform_search(query, send_func):
    queries = generate_queries(query)
    seen = {}
    counter = [0]

    send_func(f"--- 🔥 MULTI-ENGINE STREAM ---")
    send_func(f"Searching for: {query}")
    
    for pass_no in range(1, MAX_PASSES + 1):
        send_func(f"\n========== PASS {pass_no} ==========")
        
        for q in queries:
            if pass_no <= 3:
                ddg_stream(q, pass_no, seen, counter, send_func)
                yandex_stream(q, pass_no, seen, counter, send_func)
            else:
                bing_stream(q, pass_no, seen, counter, send_func)
                brave_stream(q, pass_no, seen, counter, send_func)
                ddg_stream(q + " advanced", pass_no, seen, counter, send_func)
    
    send_func("\n===================================")
    send_func(f"✅ Total UNIQUE domains collected: {len(seen)}")
    send_func(f"🔗 Total links found: {counter[0]}")
    send_func("[DONE]")

# ---------------------------
# FLASK ROUTES
# ---------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/stream')
def stream():
    query = request.args.get('q', '')
    if not query:
        return "No query provided", 400
    
    def generate():
        q = queue.Queue()
        
        def send_func(message):
            q.put(message)
        
        import threading
        thread = threading.Thread(target=perform_search, args=(query, send_func))
        thread.daemon = True
        thread.start()
        
        while True:
            try:
                message = q.get(timeout=1)
                yield f"data: {json.dumps({'line': message})}\n\n"
                if message == "[DONE]":
                    break
            except:
                yield f"data: {json.dumps({'line': ''})}\n\n"
                continue
    
    return Response(generate(), mimetype="text/event-stream")

if __name__ == '__main__':
    app.run(debug=True, threaded=True, host='127.0.0.1', port=5000)