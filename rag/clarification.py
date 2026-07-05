import re

PRODUCT_PATTERNS: tuple[tuple[str, str], ...] = (
    ("Rove 4", r"\brove\s*4\b"),
    ("Rove 6", r"\brove\s*6\b"),
    ("G3", r"\b(?:inogen\s+one\s+)?g\s*3(?:hf)?\b"),
    ("G4", r"\b(?:inogen\s+one\s+)?g\s*4\b"),
    ("G5", r"\b(?:inogen\s+one\s+)?g\s*5\b|\bone\s+g\s*5\b"),
    ("At Home", r"\bat\s*home\b"),
    ("Voxi 5", r"\bvoxi\s*5\b"),
    ("Inogen One", r"\binogen\s+one\b"),
)

BROAD_PRODUCT_PATTERNS: tuple[str, ...] = (
    r"\ball\s+(products|models|devices|concentrators)\b",
    r"\bwhich\s+(products|models|devices|concentrators)\b",
    r"\bwhat\s+(products|models|devices|concentrators)\b",
    r"\bacross\s+(products|models|devices|concentrators)\b",
    r"\bcompare\s+all\b",
)

MODEL_DEPENDENT_PATTERNS: tuple[str, ...] = (
    r"\b(column|columns|sieve|sieves)\b",
    r"\b(battery|batteries|charge|charging|charger)\b",
    r"\b(alarm|alert|beep|beeping|error|warning|indicator|light)\b",
    r"\b(faa|approved|approval|airline|airplane|flight|travel)\b",
    r"\b(flow|setting|settings|cannula|filter|filters)\b",
    r"\b(clean|cleaning|maintenance|service|warranty)\b",
    r"\b(replace|install|remove|reset|restart|start|turn\s+on|turn\s+off)\b",
    r"\b(troubleshoot|troubleshooting|won't|wont|doesn't|doesnt|not\s+working)\b",
    r"\b(this|my|the)\s+(device|unit|machine|concentrator|model)\b",
)

MODEL_CLARIFICATION_RESPONSE = (
    "I'm happy to help. Can you please provide the Inogen model you're asking about "
    "(for example Rove 4, Rove 6, G4, G5, At Home, or Voxi 5)? Once I have the model, "
    "I can look up the right documentation and cite it."
)


def _normalized_text(value: str | None) -> str:
    return str(value or "").strip().lower()


def is_all_products(product: str | None) -> bool:
    text = _normalized_text(product)
    return not text or text.startswith("all products")


def mentioned_products(message: str) -> list[str]:
    found: list[str] = []
    for product, pattern in PRODUCT_PATTERNS:
        if re.search(pattern, message, flags=re.IGNORECASE):
            found.append(product)
    return found


def asks_across_products(message: str) -> bool:
    return any(re.search(pattern, message, flags=re.IGNORECASE) for pattern in BROAD_PRODUCT_PATTERNS)


def is_model_dependent_question(message: str) -> bool:
    return any(re.search(pattern, message, flags=re.IGNORECASE) for pattern in MODEL_DEPENDENT_PATTERNS)


def should_ask_for_model(message: str, selected_product: str | None = None) -> bool:
    if not message or not message.strip():
        return False
    if not is_all_products(selected_product):
        return False
    if mentioned_products(message):
        return False
    if asks_across_products(message):
        return False
    return is_model_dependent_question(message)
