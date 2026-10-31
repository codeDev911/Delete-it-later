#!/usr/bin/env python3
"""
Build a big list of Pakistan Shopify store domains.

Usage:
    pip install requests
    python build_list.py                 # crawl pages 1..1230, save all Pakistan stores
    python build_list.py --pk-only       # keep only .pk domains
    python build_list.py --verify        # also confirm each domain is really Shopify
    python build_list.py --start 1 --end 300 --delay 3

Output: list.txt (one domain per line, deduplicated, resumable)
"""
import argparse, os, re, time
import requests

BASE = "https://www.storecensus.com/stores/country/pakistan?page={}"
DOMAIN_RE = re.compile(r"storecensus\.com/stores/([a-z0-9][a-z0-9.-]*\.[a-z]{2,})\b", re.I)
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}


def load(path):
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        return {l.strip().lower() for l in f if l.strip()}


def is_shopify(domain):
    """True if the site serves Shopify assets or a Shopify products.json."""
    for url in (f"https://{domain}/products.json?limit=1", f"https://{domain}/"):
        try:
            r = requests.get(url, headers=HEADERS, timeout=12)
            if "cdn.shopify.com" in r.text or "Shopify.theme" in r.text:
                return True
            if url.endswith("limit=1") and r.ok and '"products"' in r.text[:200]:
                return True
        except requests.RequestException:
            continue
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--end", type=int, default=1230)  # ~24,500 stores / 20 per page
    ap.add_argument("--delay", type=float, default=2.5)
    ap.add_argument("--out", default="list.txt")
    ap.add_argument("--pk-only", action="store_true")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()

    found = load(a.out)
    print(f"Starting with {len(found)} saved domains")

    for page in range(a.start, a.end + 1):
        try:
            r = requests.get(BASE.format(page), headers=HEADERS, timeout=20)
        except requests.RequestException as e:
            print(f"page {page}: {e}")
            time.sleep(10)
            continue
        if r.status_code == 429:
            print("Rate limited, sleeping 60s")
            time.sleep(60)
            continue

        domains = {d.lower() for d in DOMAIN_RE.findall(r.text)}
        if a.pk_only:
            domains = {d for d in domains if d.endswith(".pk")}
        new = domains - found

        if a.verify:
            new = {d for d in new if is_shopify(d)}

        if new:
            with open(a.out, "a") as f:
                f.write("\n".join(sorted(new)) + "\n")
            found |= new
        print(f"page {page}: +{len(new)} (total {len(found)})")
        time.sleep(a.delay)

    print(f"Done. {len(found)} domains in {a.out}")


if __name__ == "__main__":
    main()
