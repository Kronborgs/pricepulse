"""Debug script: inspect __NEXT_DATA__ from biltema and jemogfix/bauhaus."""
import httpx
import re
import json
import sys
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

URLS = {
    "biltema": "https://www.biltema.dk/varktoj/trykluft/kompressorer/kompressor-sol24-750-w-2000045124",
    "jemogfix": "https://www.jemogfix.dk/malerrulle-og-penselsaet-med-12-dele-18-cm/6130/9014246/",
    "bauhaus": "https://www.bauhaus.dk/al-ko-buskrydder-bc-400-b-comfort",
    "matas": "https://www.matas.dk/la-roche-posay_786085",
}

PRICE_WORDS = {"price", "pris", "salgspris", "incvat", "displayprice", "salesprice", "listprice", "amount", "retail"}


def find_price_keys(obj, path="", depth=0, results=None):
    if results is None:
        results = []
    if depth > 8:
        return results
    if isinstance(obj, dict):
        for k, v in obj.items():
            if any(x in k.lower() for x in PRICE_WORDS):
                results.append(f"  {path}.{k} = {repr(v)[:100]}")
            find_price_keys(v, f"{path}.{k}", depth + 1, results)
    elif isinstance(obj, list):
        for i, item in enumerate(obj[:5]):
            find_price_keys(item, f"{path}[{i}]", depth + 1, results)
    return results


def check_site(name, url):
    print(f"\n{'='*60}")
    print(f"Site: {name}")
    print(f"URL:  {url}")
    try:
        r = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=15)
        html = r.text
        print(f"Status: {r.status_code}, HTML length: {len(html)}")
    except Exception as e:
        print(f"Fetch error: {e}")
        return

    # Check __NEXT_DATA__
    m = re.search(r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', html, re.DOTALL)
    if m:
        blob = m.group(1)
        print(f"__NEXT_DATA__ length: {len(blob)}")
        try:
            data = json.loads(blob)
            results = find_price_keys(data)
            if results:
                print("Price keys found:")
                for r2 in results[:20]:
                    print(r2)
            else:
                print("No price keys found in __NEXT_DATA__")
                # Print top-level keys
                print("Top-level props keys:", list(data.get("props", {}).keys())[:10])
                pp = data.get("props", {}).get("pageProps", {})
                if pp:
                    print("pageProps keys:", list(pp.keys())[:15])
        except Exception as e:
            print(f"JSON parse error: {e}")
            print("First 500 chars:", blob[:500])
    else:
        print("No __NEXT_DATA__")

    # Check x-magento-init
    mg = re.search(r'x-magento-init.*?(\{.*?\})\s*</script>', html, re.DOTALL)
    if mg:
        print("Magento x-magento-init found, length:", len(mg.group(1)))

    # Check JSON-LD
    jld = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
    if jld:
        try:
            ld = json.loads(jld.group(1))
            ld_str = repr(ld)
            if "price" in ld_str.lower():
                print("JSON-LD has price data:", repr(ld)[:400])
        except Exception:
            pass

    # Search visible text for price patterns (Danish)
    # strip scripts
    no_scripts = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    no_scripts = re.sub(r"<style[^>]*>.*?</style>", " ", no_scripts, flags=re.DOTALL | re.IGNORECASE)
    no_tags = re.sub(r"<[^>]+>", " ", no_scripts)
    clean = re.sub(r"\s{2,}", " ", no_tags).strip()
    # find Danish prices
    danish_prices = re.findall(r"\d[\d\.]*,\d{2}|\d[\d\.]*,-|\d[\d\.]+ kr", clean[:5000])
    if danish_prices:
        print(f"Danish prices in visible text (first 5000 chars): {danish_prices[:10]}")
    else:
        print("No Danish prices in first 5000 chars of text")
    print("First 300 chars of text:", clean[:300])

    # Check og:price:amount / product:price:amount (Strategy 0 i BiltemaParser)
    soup = BeautifulSoup(html, "html.parser")
    for prop in ("product:price:amount", "og:price:amount", "product:price:currency"):
        tag = soup.find("meta", property=prop)
        if tag:
            print(f"Meta {prop} = {tag.get('content')}")
        else:
            print(f"Meta {prop} = NOT FOUND")


for name, url in URLS.items():
    check_site(name, url)

print("\nDone.")
