import json
from pathlib import Path
from typing import Any, Dict, Optional


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
ORDERS_PATH = DATA_DIR / "orders.json"
PRODUCTS_PATH = DATA_DIR / "products.json"


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_order(order_id: str) -> Optional[Dict[str, Any]]:
    orders = _load_json(ORDERS_PATH)
    for o in orders:
        if o.get("order_id") == order_id:
            return o
    return None


def get_product_by_sku(sku: str) -> Optional[Dict[str, Any]]:
    products = _load_json(PRODUCTS_PATH)
    for p in products:
        if p.get("sku") == sku:
            return p
    return None


def enrich_order(order: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adds product metadata (category, is_final_sale, etc.) to each line item.
    """
    enriched = dict(order)
    enriched_items = []
    for item in order.get("items", []):
        sku = item.get("sku")
        product = get_product_by_sku(sku) or {}
        enriched_items.append({**item, "product": product})
    enriched["items"] = enriched_items
    return enriched