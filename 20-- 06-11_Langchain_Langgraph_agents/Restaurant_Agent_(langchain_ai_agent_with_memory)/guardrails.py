import json                 # to read restaurants.json
import re                   # "regular expressions": a mini-language for searching text patterns
from pathlib import Path    # safe file paths (same idea as in tools.py)

# =============================================================================
# SETTINGS
# =============================================================================
DATA_FILE = Path(__file__).parent / "restaurants.json"
MAX_INPUT_CHARS = 500       # anything longer than this is rejected as "excessively long"

# General restaurant-related words. If the message contains any of these,
# we treat it as on-topic. Single words only (they are compared word by word).
GENERAL_KEYWORDS = {
    "restaurant", "restaurants", "food", "cuisine", "cuisines",
    "dine", "dining", "eat", "eating", "meal", "meals",
    "lunch", "dinner", "breakfast", "brunch", "hungry",
    "cost", "costs", "price", "prices", "budget", "cheap", "expensive",
    "guest", "guests", "people", "person", "persons", "party", "group",
    "seat", "seats", "table", "tables", "menu",
    "reservation", "reserve", "book", "booking",
    "recommend", "suggest", "veg", "vegetarian",
}

# Words that typically start a short follow-up reply ("yes", "no thanks", "ok 6 then"...)
FOLLOW_UP_STARTERS = {
    "yes", "no", "ok", "okay", "sure", "yeah", "yep", "nope",
    "fine", "thanks", "thank", "great", "perfect", "alright",
}

# Number words, so "make it six" counts as a follow-up just like "make it 6"
NUMBER_WORDS = {
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen", "twenty",
}

MAX_FOLLOW_UP_WORDS = 6     # follow-ups are short; long messages must stand on their own

# --- Part 2 settings ---------------------------------------------------------
MIN_GUESTS = 1              # the PDF's tool-validation limits
MAX_GUESTS = 20

# Email pattern, piece by piece:
#   [A-Za-z0-9._%+-]+   the name part: letters, digits and . _ % + -   ("john.doe")
#   @                   the @ sign
#   [A-Za-z0-9.-]+      the domain                                    ("example")
#   \.[A-Za-z]{2,}      a dot and at least 2 letters                  (".com", ".in")
# re.compile turns the pattern into a reusable object (faster when used many times).
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# Phone "candidate" pattern: an optional +, then a digit, then 8 or more
# digits/spaces/dashes, ending in a digit. Examples it catches:
#   9876543210   +91 98765 43210   040-23456789
# It is deliberately loose; we then COUNT the digits to decide (see _is_phone_number).
PHONE_CANDIDATE_PATTERN = re.compile(r"\+?\d[\d\s-]{8,}\d")
MIN_PHONE_DIGITS = 10       # Indian mobiles have 10 digits
MAX_PHONE_DIGITS = 13       # 10 digits + country code like 91 (or a few more)


# =============================================================================
# HELPERS
# =============================================================================
def _load_known_phrases() -> set[str]:
    """Collect every restaurant name, cuisine, city and ID from the JSON file (lowercase).

    The leading underscore in the name is a Python convention meaning
    "internal helper - not meant to be used from other files".
    """
    with open(DATA_FILE, encoding="utf-8") as f:
        restaurants = json.load(f)

    phrases = set()                       # a set automatically ignores duplicates
    for r in restaurants:
        phrases.add(r["name"].lower())      # e.g. "spice garden"
        phrases.add(r["cuisine"].lower())   # e.g. "south indian"
        phrases.add(r["location"].lower())  # e.g. "hyderabad"
        phrases.add(r["id"].lower())        # e.g. "r101"
    return phrases


# Loaded ONCE when this file is imported, not on every message (faster).
KNOWN_PHRASES = _load_known_phrases()


def get_words(text: str) -> list[str]:
    """Split text into lowercase words and numbers, dropping punctuation.

    "Make that 6 people!" -> ["make", "that", "6", "people"]
    [a-z0-9]+ means "one or more letters or digits in a row".
    """
    return re.findall(r"[a-z0-9]+", text.lower())


def contains_phrase(text: str, phrase: str) -> bool:
    """True if `phrase` appears in `text` as whole word(s), not inside another word.

    \\b is a "word boundary", so "eat" will NOT match inside "great" or "weather".
    re.escape makes any special characters in the phrase safe to search for.
    """
    pattern = rf"\b{re.escape(phrase)}\b"
    return re.search(pattern, text.lower()) is not None


# =============================================================================
# GUARDRAIL 1: INPUT VALIDATION (empty / too long)
# =============================================================================
def validate_input(text: str) -> str | None:
    """Return an error message if the input is empty or too long, otherwise None."""
    if not text.strip():                           # empty or only spaces
        return "Please type a question about restaurants."
    if len(text) > MAX_INPUT_CHARS:
        return f"Your message is too long ({len(text)} characters). Please keep it under {MAX_INPUT_CHARS}."
    return None                                    # None = "no problem found"


# =============================================================================
# GUARDRAIL 2: DOMAIN RESTRICTION (restaurant topics only)
# =============================================================================
def is_restaurant_related(text: str) -> bool:
    """True if the message mentions a restaurant word, or a known name/cuisine/city/ID."""
    words = set(get_words(text))

    # Check 1: any general keyword? (set & set = the words both sets have in common)
    if words & GENERAL_KEYWORDS:
        return True

    # Check 2: any restaurant name, cuisine, city or ID from our data?
    # any() stops as soon as it finds the first True, so it's quick.
    return any(contains_phrase(text, phrase) for phrase in KNOWN_PHRASES)


# =============================================================================
# GUARDRAIL 3: CONTEXT HANDLING (short follow-ups like "yes", "6 people")
# =============================================================================
def is_follow_up(text: str) -> bool:
    """True if the message looks like a short reply to the previous turn."""
    words = get_words(text)

    if not words or len(words) > MAX_FOLLOW_UP_WORDS:
        return False

    # Contains a number? ("6", "what about 8", "make it six")
    if any(w.isdigit() or w in NUMBER_WORDS for w in words):
        return True

    # Starts like a reply? ("yes", "no thanks", "ok")
    return words[0] in FOLLOW_UP_STARTERS


# =============================================================================
# COMBINED INPUT CHECK - this is what agent.py will call
# =============================================================================
def check_input(text: str, has_history: bool) -> str | None:
    """Run all input guardrails in order.

    Returns None if the message may go to the agent,
    or an error message to show the user if it must be blocked.

    has_history: True if this conversation already has earlier messages.
                 A lone "yes" only makes sense as a reply to something.
    """
    # 1) Basic validation first - no point checking the topic of an empty message
    error = validate_input(text)
    if error:
        return error

    # 2) Clearly about restaurants -> allow
    if is_restaurant_related(text):
        return None

    # 3) Not obviously about restaurants, but a short follow-up in an ongoing chat -> allow
    if has_history and is_follow_up(text):
        return None

    # 4) Everything else is off-topic -> block
    return "Sorry, I can only help with restaurant searches and dining cost estimates."


# =============================================================================
# GUARDRAIL 4: TOOL VALIDATION (guest count must be 1-20)
# =============================================================================
def validate_guest_count(guests: int) -> str | None:
    """Return an error message if the guest count is outside the allowed range, otherwise None.

    This will be called INSIDE calculate_dining_cost (Part 3), so even if the
    model asks for 50 guests, the calculation never runs.
    """
    if guests < MIN_GUESTS or guests > MAX_GUESTS:
        return (
            f"Invalid guest count: {guests}. "
            f"Estimates are only available for {MIN_GUESTS} to {MAX_GUESTS} guests."
        )
    return None


# =============================================================================
# GUARDRAIL 5: PII DETECTION (emails and phone numbers)
# =============================================================================
# PII = "Personally Identifiable Information": data that identifies a real person.
def _is_phone_number(candidate: str) -> bool:
    """True if the matched text has a realistic number of digits for a phone number."""
    digit_count = sum(1 for ch in candidate if ch.isdigit())   # count only the digits
    return MIN_PHONE_DIGITS <= digit_count <= MAX_PHONE_DIGITS


def find_emails(text: str) -> list[str]:
    """Return every email address found in the text."""
    return EMAIL_PATTERN.findall(text)        # findall returns a list of all matches


def find_phone_numbers(text: str) -> list[str]:
    """Return every phone number found in the text."""
    candidates = PHONE_CANDIDATE_PATTERN.findall(text)
    # Keep only candidates with a phone-like digit count
    # (this stops things like a long price from being treated as a phone number).
    return [c.strip() for c in candidates if _is_phone_number(c)]


def detect_pii(text: str) -> list[str]:
    """Return the TYPES of PII found, e.g. ["email address", "phone number"]. Empty list = none."""
    found = []
    if find_emails(text):
        found.append("email address")
    if find_phone_numbers(text):
        found.append("phone number")
    return found


# =============================================================================
# GUARDRAIL 6: OUTPUT GUARDRAIL (redact emails and phone numbers)
# =============================================================================
def redact_pii(text: str) -> str:
    """Replace every email and phone number in the text with a placeholder.

    Used on the agent's final answer before it is printed (Part 3),
    and on user input before it is sent to the model.
    """
    # Emails FIRST: an email like "raj9876543210@mail.com" contains a long number.
    # Replacing the email first means the phone check can't grab part of it.
    text = EMAIL_PATTERN.sub("[EMAIL REDACTED]", text)

    # For phones we need the digit-count check, so instead of a fixed replacement
    # we give re.sub a function. It is called once per match and returns
    # what that match should be replaced with.
    def replace_phone(match: re.Match) -> str:
        found = match.group(0)                 # the exact text that matched
        return "[PHONE REDACTED]" if _is_phone_number(found) else found

    return PHONE_CANDIDATE_PATTERN.sub(replace_phone, text)


# =============================================================================
# MANUAL TESTS (only run when this file is executed directly)
# =============================================================================
if __name__ == "__main__":
    # Each test: (message, has_history)
    tests = [
        ("", False),                                                      # empty
        ("a" * 600, False),                                               # too long
        ("Show me Indian restaurants.", False),                           # general keyword
        ("What is the estimated cost for 4 people at Spice Garden?", False),
        ("Tell me about Spice Garden", False),                            # restaurant name only
        ("Make that 6 people.", True),                                    # follow-up with keyword
        ("yes", True),                                                    # follow-up in a conversation
        ("yes", False),                                                   # same word, but nothing to reply to
        ("make it six", True),                                            # number word follow-up
        ("What is the largest mammal?", False),                           # off-topic
        ("What is the weather in Delhi?", False),                         # predict this one!
    ]

    for message, has_history in tests:
        result = check_input(message, has_history)
        status = "ALLOWED" if result is None else f"BLOCKED -> {result}"
        shown = message if len(message) < 60 else message[:20] + "..."   # don't print 600 a's
        print(f"[history={has_history!s:5}] {shown!r:62} {status}")

    # ---- Part 2 tests --------------------------------------------------------
    print("\n--- Guest count validation ---")
    for guests in [0, 1, 6, 20, 21, 50]:
        error = validate_guest_count(guests)
        print(f"{guests:>3} guests -> {'OK' if error is None else error}")

    print("\n--- PII detection and redaction ---")
    pii_tests = [
        "My email is john@example.com.",
        "Call me on 9876543210",
        "My number is +91 98765 43210, email priya.s@mail.co.in",
        "Office line 040-23456789",
        "Spice Garden for 6 people costs Rs.4800",   # numbers, but no PII
        "Table for 4 on 12 11 2026",                  # a date-like number: should NOT be a phone
    ]
    for text in pii_tests:
        print(f"Text:     {text}")
        print(f"Detected: {detect_pii(text) or 'nothing'}")   # `or` shows 'nothing' for an empty list
        print(f"Redacted: {redact_pii(text)}\n")