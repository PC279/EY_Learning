# tools.py
# ------------------------------------------------------------
# Tools (plain Python functions) that our AI agents can call.
# The agent framework shows each function's name, docstring and
# parameter descriptions to the LLM so it knows when/how to call it.
#
# Design rules:
#   1. Return text (JSON strings), because the LLM reads text.
#   2. Return error messages instead of raising exceptions, so the
#      agent can read the problem and explain it to the customer.
# ------------------------------------------------------------

import json                    # read products.json and return JSON text
from pathlib import Path       # build file paths that work from any folder
from typing import Annotated   # lets us attach a description to a parameter
from pydantic import Field     # Field(description=...) is what the LLM sees


# ============================================================
# STEP 1: Load the product data
# ============================================================

# Path to products.json, relative to THIS file (tools.py).
# This avoids "file not found" errors if PyCharm runs from another folder.
PRODUCTS_FILE = Path(__file__).parent / "products.json"


def load_products() -> list[dict]:
    """Read products.json and return the list of product dictionaries."""
    with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# Load once when the module is imported (32 products is tiny, so this is fine)
PRODUCTS = load_products()


# ============================================================
# STEP 2: Tool 1 - search_products()
# ============================================================

def search_products(
    query: Annotated[str, Field(description="Product name or category to search for, e.g. 'laptop' or 'headphones'")],
) -> str:
    """Search the product catalogue by product name or category.
    Returns matching products with product ID, name, category, price (INR),
    stock, an in_stock flag and rating."""

    # Normalise the search text: remove extra spaces, make lowercase
    q = query.strip().lower()

    # Reject an empty search straight away
    if not q:
        return json.dumps({"status": "error",
                           "message": "Please provide a product name or category."})

    # Search terms: the original word, plus its singular form
    # so "laptops" also matches the category "Laptop"
    terms = {q}
    if q.endswith("s"):
        terms.add(q[:-1])

    matches = []
    for p in PRODUCTS:
        name = p["name"].lower()
        category = p["category"].lower()

        # A product matches if any search term appears in its name or category
        if any(t in name or t in category for t in terms):
            matches.append({
                "product_id": p["id"],            # the JSON file uses "id"
                "name": p["name"],
                "category": p["category"],
                "price_inr": p["price_inr"],      # the JSON file uses "price_inr"
                "stock": p["stock"],
                "in_stock": p["stock"] > 0,       # True/False flag so agents can't miss out-of-stock items
                "rating": p["rating"],
            })

    # Nothing found: return a message the agent can pass on to the customer
    if not matches:
        return json.dumps({"status": "not_found",
                           "message": f"No products found matching '{query}'."})

    # Sort: highest rating first; if ratings tie, cheaper first.
    # (This mirrors the Recommendation Agent's rule, which helps later agents.)
    matches.sort(key=lambda m: (-m["rating"], m["price_inr"]))

    # ensure_ascii=False keeps characters like ₹ readable
    return json.dumps({"status": "ok", "count": len(matches), "products": matches},
                      indent=2, ensure_ascii=False)


# ============================================================
# STEP 3: Tool 2 - calculate_order_total()
# ============================================================

def calculate_order_total(
    product_id: Annotated[str, Field(description="Product ID exactly as returned by search_products, e.g. 'P101'")],
    quantity: Annotated[int, Field(description="Number of units the customer wants (must be 1 or more)")],
) -> str:
    """Calculate the total cost of buying a quantity of one product.
    First checks that the quantity is valid, the product exists and enough stock
    is available. The total is calculated ONLY when the order can be fulfilled."""

    # ---------- Gate 1: valid quantity ----------
    # Quantity must be a whole number of at least 1.
    # (In Python, True/False count as ints, so we exclude bool explicitly.)
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
        return json.dumps({
            "status": "invalid_quantity",
            "message": f"Quantity must be a whole number of 1 or more (got {quantity!r}).",
        })

    # ---------- Gate 2: product exists ----------
    # Compare as lowercase strings so 'p101' matches 'P101'
    wanted_id = str(product_id).strip().lower()
    product = None
    for p in PRODUCTS:
        if str(p["id"]).lower() == wanted_id:
            product = p
            break   # found it, stop looping

    if product is None:
        return json.dumps({
            "status": "not_found",
            "message": f"Product ID '{product_id}' does not exist.",
        })

    # Save stock in a variable since we use it in several checks below
    stock = product["stock"]

    # ---------- Gate 3: product is in stock at all ----------
    if stock == 0:
        return json.dumps({
            "status": "out_of_stock",
            "product_id": product["id"],
            "name": product["name"],
            "stock_available": 0,
            "quantity_requested": quantity,
            "message": f"{product['name']} is out of stock. No units are available in the inventory.",
        }, ensure_ascii=False)

    # ---------- Gate 4: enough stock for this order ----------
    if quantity > stock:
        return json.dumps({
            "status": "insufficient_stock",
            "product_id": product["id"],
            "name": product["name"],
            "stock_available": stock,
            "quantity_requested": quantity,
            "message": (f"Insufficient stock for {product['name']}: {quantity} requested, "
                        f"but only {stock} unit(s) left."),
        }, ensure_ascii=False)

    # ---------- All gates passed: NOW calculate the price ----------
    unit_price = product["price_inr"]
    total = unit_price * quantity

    return json.dumps({
        "status": "ok",
        "product_id": product["id"],
        "name": product["name"],
        "unit_price_inr": unit_price,
        "quantity_requested": quantity,
        "stock_available": stock,
        "total_cost_inr": total,
        "rating": product["rating"],
    }, indent=2, ensure_ascii=False)


# ============================================================
# STEP 4: Manual tests - run "python tools.py" to see the output.
# This block only runs when tools.py is executed directly,
# NOT when agents.py imports it later.
# ============================================================

if __name__ == "__main__":
    print("=== search: laptops (plural) ===")
    print(search_products("laptops"))            # expect 6 laptops, highest rated first

    print("\n=== search: category that doesn't exist ===")
    print(search_products("spaceship"))          # expect not_found

    print("\n=== total: valid order ===")
    print(calculate_order_total("P101", 2))      # NovaBook Air 14 x2 -> expect 104000, ok

    print("\n=== total: zero quantity ===")
    print(calculate_order_total("P101", 0))      # expect invalid_quantity

    print("\n=== total: more than stock ===")
    print(calculate_order_total("P101", 100))    # only 8 in stock -> expect insufficient_stock

    print("\n=== total: out-of-stock product ===")
    print(calculate_order_total("P103", 1))      # stock is 0 -> expect out_of_stock

    print("\n=== total: bad product ID ===")
    print(calculate_order_total("XYZ999", 1))    # expect not_found

    print("\n=== total: lowercase ID ===")
    print(calculate_order_total("p102", 1))      # should still find P102 -> 68000, ok