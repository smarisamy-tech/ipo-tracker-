import re
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

BASE = "https://www.investorgain.com"
MAINBOARD_URL = "https://www.investorgain.com/report/ipo-subscription-live/333/ipo/"
SUBSCRIPTION_MIN = 100.0
PROFIT_MIN = 500.0
TIMEOUT = 25

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/156.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-IN,en;q=0.9",
    "Cache-Control": "no-cache",
}

session = requests.Session()
session.headers.update(HEADERS)

def txt(node):
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip() if node else ""

def num(value):
    if value is None:
        return None
    m = re.search(r"-?[\d,]+(?:\.\d+)?", str(value))
    return float(m.group(0).replace(",", "")) if m else None

def money(value):
    if value is None:
        return None
    m = re.search(r"₹\s*(-?[\d,]+(?:\.\d+)?)", str(value))
    return float(m.group(1).replace(",", "")) if m else None

def clean_name(value):
    value = re.sub(r"\s+", " ", value or "").strip()
    return re.sub(r"\s+IPO$", "", value, flags=re.I).strip()


def find_mainboard_table(soup):
    for table in soup.find_all("table"):
        headers = [txt(x).lower() for x in table.find_all("th")]
        joined = " | ".join(headers)
        if "total" in joined and ("ipo price" in joined or "closing date" in joined):
            return table
    raise ValueError("Mainboard subscription table not found")

def extract_mainboard_rows():
    r = session.get(MAINBOARD_URL, timeout=TIMEOUT)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    table = find_mainboard_table(soup)

    rows = []
    for tr in table.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) < 2:
            continue

        # InvestorGain links the company name to:
        # /subscription/<slug>/<id>/
        subscription_link = None
        for a in cells[0].find_all("a", href=True):
            href = a.get("href", "")
            if "/subscription/" in href:
                subscription_link = urljoin(BASE, href)
                company_name = clean_name(txt(a))
                break

        if not subscription_link:
            continue

        subscription = num(txt(cells[1]))
        if not company_name or subscription is None:
            continue

        ipo_price = None
        if len(cells) >= 10:
            ipo_price = num(txt(cells[9]))

        # Same slug and numeric ID are used by InvestorGain for GMP pages.
        # Example:
        # /subscription/bls-polymers-ipo/1849/
        # -> /gmp/bls-polymers-ipo/1849/
        gmp_url = subscription_link.replace("/subscription/", "/gmp/", 1)

        rows.append({
            "ipo_name": company_name,
            "ipo_type": "Mainboard",
            "subscription": subscription,
            "upper_price": ipo_price,
            "subscription_url": subscription_link,
            "gmp_url": gmp_url,
        })

    if not rows:
        raise ValueError("No Mainboard rows parsed")
    return rows

def parse_latest_gmp(url, fallback_upper_price=None):
    r = session.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    page_text = txt(soup)

    upper = fallback_upper_price
    m = re.search(r"upper price-₹\s*([\d,]+(?:\.\d+)?)", page_text, flags=re.I)
    if m:
        upper = float(m.group(1).replace(",", ""))

    table = None
    for t in soup.find_all("table"):
        body = txt(t)
        if "GMP Date" in body and "Est. Profit" in body and "Trend" in body:
            table = t
            break
    if not table:
        raise ValueError("Daily GMP trend table not found")

    for tr in table.find_all("tr")[1:]:
        cells = tr.find_all(["td", "th"])
        if len(cells) < 5:
            continue
        vals = [txt(c) for c in cells[:5]]
        gmp_value = money(vals[1])
        listing = money(vals[2])
        profit = money(vals[3])
        if gmp_value is None and profit is None:
            continue
        return {
            "gmp_date": vals[0],
            "gmp": gmp_value,
            "upper_price": upper,
            "estimated_listing_price": listing,
            "estimated_profit": profit,
            "trend": vals[4] or "Unknown",
            "gmp_url": url,
        }
    raise ValueError("Latest GMP row not found")

def get_live_data():
    payload = {
        "source": "InvestorGain",
        "source_url": MAINBOARD_URL,
        "rules": {
            "ipo_type": "Mainboard",
            "subscription_min_x": SUBSCRIPTION_MIN,
            "estimated_profit_min_rupees_exclusive": PROFIT_MIN,
        },
        "status": "ok",
        "checked": 0,
        "qualified": [],
        "rejected": [],
        "errors": [],
    }

    try:
        rows = extract_mainboard_rows()
    except Exception as e:
        payload["status"] = "error"
        payload["errors"].append(f"Mainboard page: {type(e).__name__}: {e}")
        return payload

    payload["checked"] = len(rows)

    for item in rows:
        if item["subscription"] < SUBSCRIPTION_MIN:
            item["qualifies"] = False
            item["rejection_reason"] = f"Subscription {item['subscription']:.2f}x < {SUBSCRIPTION_MIN:.0f}x"
            payload["rejected"].append(item)
            continue

        if not item["gmp_url"]:
            item["qualifies"] = False
            item["rejection_reason"] = "GMP page link was not found in InvestorGain Mainboard row"
            payload["rejected"].append(item)
            payload["errors"].append(f"{item['ipo_name']}: GMP link missing")
            continue

        try:
            g = parse_latest_gmp(item["gmp_url"], item.get("upper_price"))
            item.update(g)
            profit = item.get("estimated_profit")
            if profit is not None and profit > PROFIT_MIN:
                item["qualifies"] = True
                item["rejection_reason"] = None
                payload["qualified"].append(item)
            else:
                item["qualifies"] = False
                shown = "unavailable" if profit is None else f"₹{profit:,.0f}"
                item["rejection_reason"] = f"Estimated profit {shown} is not > ₹{PROFIT_MIN:,.0f}"
                payload["rejected"].append(item)
        except Exception as e:
            item["qualifies"] = False
            item["rejection_reason"] = "Could not parse latest GMP row"
            payload["rejected"].append(item)
            payload["errors"].append(f"{item['ipo_name']}: {type(e).__name__}: {e}")

    payload["qualified"].sort(
        key=lambda x: (x.get("subscription") or 0, x.get("estimated_profit") or 0),
        reverse=True
    )
    payload["rejected"].sort(key=lambda x: x.get("subscription") or 0, reverse=True)

    if payload["errors"]:
        payload["status"] = "partial"
    return payload
