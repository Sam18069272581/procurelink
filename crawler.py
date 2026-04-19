"""
ProcureLink Crawler v2 — Geizhals.de with idealo.de fallback
Run: python crawler.py
"""
import json, time, random, logging, re
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Optional
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

TARGETS = [
    ("SKU-001", "Druckerpapier A4 80g (500 Bl.)",   "Büromaterial",    "druckerpapier a4 80g 500"),
    ("SKU-002", "Whiteboard-Marker Set 10er",         "Büromaterial",    "whiteboard marker set"),
    ("SKU-003", "Toner HP LaserJet CF226A",           "IT & Elektronik", "toner hp cf226a"),
    ("SKU-004", "USB-Hub 4-Port USB-C",               "IT & Elektronik", "usb hub 4 port"),
    ("SKU-005", "Aktenvernichter Partikelschnitt",    "Büromaterial",    "aktenvernichter büro"),
    ("SKU-006", "Reinigungstücher Bildschirm 100er",  "Reinigung",       "bildschirm reinigungstücher"),
    ("SKU-007", "HDMI-Kabel 2m 4K",                  "IT & Elektronik", "hdmi kabel 2m"),
    ("SKU-008", "Kugelschreiber Blau 50er Pack",      "Büromaterial",    "kugelschreiber set blau"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0",
}

@dataclass
class Offer:
    shop: str
    price: float
    url: str

@dataclass
class ProductResult:
    sku: str
    name: str
    category: str
    offers: list
    best_price: Optional[float]
    best_shop: Optional[str]
    scraped_at: str
    source: str
    error: Optional[str] = None

def parse_price(raw: str) -> Optional[float]:
    cleaned = re.sub(r"[€\s\xa0]", "", raw)
    cleaned = re.sub(r"\.(?=\d{3})", "", cleaned).replace(",", ".")
    try:
        v = float(cleaned)
        return round(v, 2) if v > 0 else None
    except ValueError:
        return None

def scrape_geizhals(query: str, session: requests.Session) -> tuple[list, str]:
    url = f"https://geizhals.de/?fs={requests.utils.quote(query)}&hloc=at&hloc=de&sort=p"
    try:
        resp = session.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 403:
            log.warning("  Geizhals 403 — blocked")
            return [], url
        resp.raise_for_status()
    except requests.RequestException as e:
        log.warning("  Geizhals error: %s", e)
        return [], url

    soup = BeautifulSoup(resp.text, "lxml")
    offers = []

    # Follow first product detail link
    link_el = soup.select_one("a.gh_productname, a.product-name, .listview__name a")
    if link_el:
        href = link_el.get("href", "")
        detail_url = ("https://geizhals.de" + href) if href.startswith("/") else href
        time.sleep(random.uniform(2, 4))
        try:
            dr = session.get(detail_url, headers=HEADERS, timeout=15)
            dr.raise_for_status()
            ds = BeautifulSoup(dr.text, "lxml")
            for row in ds.select("tr.offer, .offer__row, li.offer"):
                se = row.select_one(".merchant__name, .offer__merchant, [itemprop='seller']")
                pe = row.select_one(".price, .offer__price, [itemprop='price']")
                if pe:
                    p = parse_price(pe.get_text())
                    if p:
                        offers.append(Offer(shop=(se.get_text(strip=True)[:60] if se else "shop"), price=p, url=detail_url))
        except Exception:
            pass

    # Inline fallback
    if not offers:
        for card in soup.select(".offer, .listview__item, .product-list__item")[:5]:
            se = card.select_one(".merchant, .shop-name, .listview__merchant")
            pe = card.select_one(".price, .gh_price, .listview__price")
            if pe:
                p = parse_price(pe.get_text())
                if p:
                    offers.append(Offer(shop=(se.get_text(strip=True)[:60] if se else "Geizhals"), price=p, url=url))

    return offers, "geizhals.de"

def scrape_idealo(query: str, session: requests.Session) -> tuple[list, str]:
    url = f"https://www.idealo.de/preisvergleich/MainSearchProductCategory.html?q={requests.utils.quote(query)}"
    try:
        resp = session.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.warning("  Idealo error: %s", e)
        return [], url

    soup = BeautifulSoup(resp.text, "lxml")
    offers = []
    for card in soup.select("div.offerList-item, article.productOffers-listItem, .sr-resultList article")[:5]:
        se = card.select_one(".shop-name, .offerList-item-shop, .ooi-itemInfo")
        pe = card.select_one(".offerList-item-priceMin, .price, .ooi-price")
        if pe:
            p = parse_price(pe.get_text())
            if p:
                offers.append(Offer(shop=(se.get_text(strip=True)[:60] if se else "idealo"), price=p, url=url))
    return offers, "idealo.de"

def scrape_product(sku, name, category, query, session) -> ProductResult:
    now = datetime.now(timezone.utc).isoformat()
    log.info("Scraping: %s — %s", sku, name)

    offers, source = scrape_geizhals(query, session)

    if not offers:
        log.info("  Geizhals empty → trying idealo.de")
        time.sleep(random.uniform(1, 2))
        offers, source = scrape_idealo(query, session)

    offers.sort(key=lambda o: o.price)
    best = offers[0] if offers else None
    log.info("  → %s @ €%.2f (%d offers) [%s]",
             best.shop if best else "n/a", best.price if best else 0, len(offers), source)

    return ProductResult(
        sku=sku, name=name, category=category,
        offers=[asdict(o) for o in offers[:6]],
        best_price=best.price if best else None,
        best_shop=best.shop if best else None,
        scraped_at=now, source=source,
        error=None if offers else "no_offers_found",
    )

def run():
    session = requests.Session()
    log.info("Warming up session (visiting homepage)...")
    try:
        session.get("https://geizhals.de/", headers=HEADERS, timeout=10)
        time.sleep(random.uniform(2, 3))
    except Exception:
        pass

    results = []
    for sku, name, category, query in TARGETS:
        r = scrape_product(sku, name, category, query, session)
        results.append(asdict(r))
        time.sleep(random.uniform(3, 6))

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "geizhals.de / idealo.de",
        "product_count": len(results),
        "results": results,
    }
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    ok = sum(1 for r in results if r["best_price"])
    log.info("Done — %d/%d products have price data → data.json", ok, len(results))

if __name__ == "__main__":
    run()