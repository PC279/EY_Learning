import json                      # built-in module for reading/writing JSON files
from pathlib import Path         # built-in module for working with file paths safely

from langchain.tools import tool # decorator that turns a normal function into a LangChain tool

from guardrails import validate_guest_count  # tool guardrail: guests must be 1-20

# Build the path to restaurants.json relative to THIS file (tools.py),
# so it works no matter which folder Python was started from.
DATA_FILE = Path(__file__).parent / "restaurants.json"

# Never send more than this many restaurants back to the model at once
# (keeps the answer readable and saves tokens).
MAX_RESULTS = 10


def load_restaurants() -> list[dict]:
    """Read the restaurant list from the JSON file."""
    # "with" opens the file and closes it automatically when the block ends.
    # encoding="utf-8" avoids problems with special characters on Windows.
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)  # converts the JSON text into a Python list of dicts


def format_restaurant(r: dict) -> str:
    """Turn one restaurant dict into a single readable line."""
    seats = r["available_seats"]
    # Conditional expression: pick one text or the other in a single line.
    seat_text = f"{seats} seats available" if seats > 0 else "fully booked"
    # The two f-strings inside the parentheses are joined automatically
    # into one string (Python glues adjacent string literals together).
    return (
        f"{r['id']} | {r['name']} | {r['cuisine']} | {r['location']} | "
        f"Rs.{r['price_per_person']} per person | {seat_text}"
    )


@tool  # makes this function visible to the model; the docstring becomes its description
def search_restaurants(keyword: str, location: str = "") -> str:
    """Search restaurants by cuisine type or restaurant name.

    Args:
        keyword: A cuisine (e.g. "Indian", "Italian") or part of a restaurant name (e.g. "Spice Garden").
        location: Optional city to narrow results (e.g. "Hyderabad"). Leave empty to search all cities.
    """
    # Normalise the input: remove extra spaces and make it lowercase,
    # so " Indian", "INDIAN" and "indian" are all treated the same.
    keyword = keyword.strip().lower()
    location = location.strip().lower()

    restaurants = load_restaurants()  # all 240 restaurants

    # Step 0: if a city was given, keep only that city's restaurants.
    # (An empty string counts as False, so this is skipped when no city is given.)
    if location:
        restaurants = [r for r in restaurants if r["location"].lower() == location]

    # Step 1: one combined search over BOTH the name and the cuisine.
    # "keyword in text" checks whether the keyword appears ANYWHERE inside the text:
    #   "indian" in "south indian"  -> True  (so North/South Indian are included)
    #   "cafe"   in "harvest cafe"  -> True  (name matches are never skipped)
    # A restaurant is kept if the keyword is in its name OR in its cuisine.
    matches = [
        r for r in restaurants
        if keyword in r["name"].lower() or keyword in r["cuisine"].lower()
    ]

    # Step 2: nothing found? Return a clear message so the model doesn't invent results.
    if not matches:
        # Add " in <city>" to the message only if a city was searched.
        where = f" in {location}" if location else ""
        return f"No restaurants found matching '{keyword}'{where}."

    # Step 3: format at most MAX_RESULTS restaurants, one line each.
    # matches[:MAX_RESULTS] is a slice: "items from the start up to (not including) index 10".
    lines = [format_restaurant(r) for r in matches[:MAX_RESULTS]]

    # "\n".join(lines) puts a newline between every line, turning the list into one block of text.
    # len(matches) is the TOTAL number found, even if we only show 10.
    result = f"Found {len(matches)} matching restaurant(s):\n" + "\n".join(lines)

    # Step 4: if we cut the list short, say so, so the model can ask the user to narrow it down.
    if len(matches) > MAX_RESULTS:
        result += f"\n(Showing first {MAX_RESULTS}. Ask for a specific city to narrow the results.)"

    # RETURN (not print): the returned text is what the model reads.
    return result


@tool
def calculate_dining_cost(restaurant_id: str, guests: int) -> str:
    """Calculate the estimated total dining cost for a group at one restaurant.

    Args:
        restaurant_id: The restaurant's ID, e.g. "R101". If you only know the name,
            use search_restaurants first to find the ID.
        guests: Number of people dining.
    """
    # GUARDRAIL (tool validation): check the guest count BEFORE doing anything else.
    # If it's invalid, we return the error text instead of calculating.
    # The model reads this message and explains the limit to the user.
    error = validate_guest_count(guests)
    if error:
        return error

    # IDs in the JSON are uppercase ("R101"), so accept "r101", " R101 " etc.
    restaurant_id = restaurant_id.strip().upper()

    # Go through every restaurant looking for the matching ID.
    for r in load_restaurants():
        if r["id"] == restaurant_id:
            # Found it: the core calculation.
            total = r["price_per_person"] * guests
            result = (
                f"{r['name']} ({r['id']}): Rs.{r['price_per_person']} x {guests} guests "
                f"= Rs.{total} estimated total."
            )
            # Honest extra info: warn if the group is bigger than the free seats.
            # (We don't book anything; we just report it.)
            if guests > r["available_seats"]:
                result += f" Note: only {r['available_seats']} seats are currently available."
            # "return" inside the loop exits the whole function immediately,
            # so we stop searching as soon as we've found the restaurant.
            return result

    # We only reach this line if the loop finished WITHOUT returning,
    # which means no restaurant had that ID.
    return f"No restaurant found with ID '{restaurant_id}'. Please search for the restaurant first."


# This block runs ONLY when you run tools.py directly.
# When agent.py does "from tools import ...", it is skipped.
if __name__ == "__main__":
    # Show what the model will "see" about the tool
    print("Tool name:", search_restaurants.name)
    print("Tool args:", search_restaurants.args)
    print()

    # After @tool, the functions are LangChain tool objects:
    # call them with .invoke() and a dict of arguments, exactly like LangChain does.
    print(search_restaurants.invoke({"keyword": "Indian"}))                          # all cities: Indian + North + South Indian (72 found, 10 shown)
    print()
    print(search_restaurants.invoke({"keyword": "Indian", "location": "Hyderabad"})) # cuisine + city filter
    print()
    print(search_restaurants.invoke({"keyword": "spice garden"}))                    # partial match on the name
    print()
    print(calculate_dining_cost.invoke({"restaurant_id": "R101", "guests": 4}))     # normal case
    print(calculate_dining_cost.invoke({"restaurant_id": "r101", "guests": 6}))     # lowercase ID still works
    print(calculate_dining_cost.invoke({"restaurant_id": "R999", "guests": 4}))     # ID that doesn't exist
    print(calculate_dining_cost.invoke({"restaurant_id": "R101", "guests": 50}))    # blocked by the guest-count guardrail