"""
PriceScout - compare a product across shopping platforms and recommend the cheapest.

Run:
    pip install -r requirements.txt
    python app.py
(API only; the React frontend lives in ../frontend)

How it works:
    * Each store is a "provider" class with a search(query) method that returns Offer objects.
    * All providers run in parallel; one failing provider never breaks the rest.
    * Offers are ranked by effective price = price + shipping - discount.
    * SampleProvider ships with demo data. To go live, fill in ApiProvider (below)
      with a real, permitted data source (official/affiliate API) and add it to PROVIDERS.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict

from flask import Flask, jsonify, request

app = Flask(__name__)


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
@dataclass
class Offer:
    store: str
    product: str
    price: float
    shipping: float = 0.0
    discount: float = 0.0
    rating: float | None = None
    delivery: str = "-"
    in_stock: bool = True
    url: str = ""

    @property
    def effective(self) -> float:
        return max(0.0, self.price + self.shipping - self.discount)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["effective"] = self.effective
        return d


# --------------------------------------------------------------------------- #
# Providers
# --------------------------------------------------------------------------- #
class Provider(ABC):
    name = "base"

    @abstractmethod
    def search(self, query: str) -> list[Offer]:
        ...


# (store, price, shipping, discount, rating, delivery, in_stock)
SAMPLE = {
    "Sony WH-1000XM5": [
        ("Amazon.in", 26990, 0, 1500, 4.5, "Tomorrow", True),
        ("Flipkart", 27490, 0, 2000, 4.4, "2 days", True),
        ("Croma", 29990, 0, 1000, 4.3, "3 days", True),
        ("Reliance Digital", 28490, 99, 1500, 4.3, "3 days", True),
        ("Sony Center", 29990, 0, 0, 4.6, "4 days", False),
    ],
    "iPhone 15 (128 GB)": [
        ("Amazon.in", 65900, 0, 3000, 4.6, "Tomorrow", True),
        ("Flipkart", 64999, 0, 4000, 4.6, "2 days", True),
        ("Croma", 66990, 0, 2500, 4.5, "2 days", True),
        ("Reliance Digital", 67900, 0, 3000, 4.5, "3 days", True),
        ("Apple Store", 69900, 0, 0, 4.8, "2 days", True),
    ],
    "Samsung 55 inch 4K Smart TV": [
        ("Amazon.in", 43990, 0, 3000, 4.2, "3 days", True),
        ("Flipkart", 42490, 0, 2500, 4.3, "4 days", True),
        ("Croma", 44990, 0, 3500, 4.1, "2 days", True),
        ("Vijay Sales", 41990, 499, 1000, 4.2, "5 days", True),
        ("Reliance Digital", 45490, 0, 4000, 4.2, "3 days", False),
    ],
    "boAt Airdopes 141": [
        ("Amazon.in", 1299, 0, 100, 4.1, "Tomorrow", True),
        ("Flipkart", 1199, 40, 100, 4.0, "2 days", True),
        ("boAt Store", 1499, 0, 300, 4.2, "3 days", True),
        ("Myntra", 1349, 0, 150, 4.0, "3 days", True),
        ("Croma", 1599, 0, 0, 4.0, "4 days", True),
    ],
}


def match_sample(query: str) -> str | None:
    words = query.lower().split()
    best, best_score = None, 0
    for name in SAMPLE:
        score = sum(w in name.lower() for w in words)
        if score > best_score:
            best, best_score = name, score
    return best


class SampleProvider(Provider):
    """Demo data so the app works out of the box."""

    name = "sample"

    def search(self, query: str) -> list[Offer]:
        key = match_sample(query)
        if not key:
            return []
        return [Offer(s, key, p, sh, d, r, dl, st) for s, p, sh, d, r, dl, st in SAMPLE[key]]


class ApiProvider(Provider):
    """
    TEMPLATE for a real store. Use an official / affiliate API or a licensed
    price-data service (e.g. Amazon Product Advertising API, Flipkart Affiliate API,
    or aggregators like SerpApi / Rainforest). Check each site's terms before
    scraping; many forbid it.
    """

    name = "example-api"

    def __init__(self, store: str, base_url: str, api_key: str):
        self.store, self.base_url, self.api_key = store, base_url, api_key

    def search(self, query: str) -> list[Offer]:
        import requests

        resp = requests.get(
            self.base_url,
            params={"q": query},
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=8,
        )
        resp.raise_for_status()
        offers = []
        for item in resp.json().get("results", []):  # adapt to the API's real JSON shape
            offers.append(
                Offer(
                    store=self.store,
                    product=item["title"],
                    price=float(item["price"]),
                    shipping=float(item.get("shipping", 0)),
                    discount=float(item.get("discount", 0)),
                    rating=item.get("rating"),
                    delivery=item.get("delivery", "-"),
                    in_stock=item.get("in_stock", True),
                    url=item.get("url", ""),
                )
            )
        return offers


# Add real providers here, e.g.:
# PROVIDERS = [ApiProvider("Amazon.in", "https://api.example.com/amazon", "KEY"), ...]
PROVIDERS: list[Provider] = [SampleProvider()]


# --------------------------------------------------------------------------- #
# Comparison logic
# --------------------------------------------------------------------------- #
def gather(query: str) -> tuple[list[Offer], list[str]]:
    offers, errors = [], []

    def run(p: Provider):
        try:
            return p.search(query)
        except Exception as exc:  # keep going if one store fails
            errors.append(f"{p.name}: {exc}")
            return []

    with ThreadPoolExecutor(max_workers=max(1, len(PROVIDERS))) as pool:
        for result in pool.map(run, PROVIDERS):
            offers.extend(result)
    return offers, errors


def compare(query: str) -> dict:
    offers, errors = gather(query)
    if not offers:
        return {"found": False, "errors": errors}

    in_stock = sorted((o for o in offers if o.in_stock), key=lambda o: o.effective)
    out_stock = [o for o in offers if not o.in_stock]
    if not in_stock:
        return {"found": True, "product": offers[0].product, "best": None,
                "offers": [o.to_dict() for o in out_stock], "errors": errors}

    best, worst = in_stock[0], in_stock[-1]
    return {
        "found": True,
        "product": best.product,
        "best": best.to_dict(),
        "savings": worst.effective - best.effective,
        "close_call": len(in_stock) > 1 and in_stock[1].effective - best.effective <= 0.01 * best.effective,
        "offers": [o.to_dict() for o in in_stock + out_stock],
        "errors": errors,
    }


# --------------------------------------------------------------------------- #
# Web app
# --------------------------------------------------------------------------- #
@app.get("/api/compare")
def api_compare():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"found": False, "errors": ["Empty query"]}), 400
    return jsonify(compare(q))


@app.get("/api/suggestions")
def api_suggestions():
    return jsonify(list(SAMPLE))


@app.get("/")
def health():
    return jsonify({"status": "ok", "endpoints": ["/api/compare?q=...", "/api/suggestions"]})


if __name__ == "__main__":
    app.run(port=5000, debug=True)
