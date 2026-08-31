from typing import Any

from app.schemas import SearchRole, SearchTerm, SearchTerms


# Run llm schema extractions

# Form T E I C blocks

# Construct sqlite queries Search db

# RRF results


# completion.choices[0].message.content is { terms: [list of dictionaries that are the schema object SearchRole, SearchTerm, SearchTerms]}


data = {
    "need_search": False,
    "terms": [
        {
            "text": "George Washington's heroism",
            "role": "target_entity",
            "is_phrase": False,
            "variants": ["Washington's heroism", "heroism of George Washington"],
        },
        {
            "text": "stoic mentality",
            "role": "essential",
            "is_phrase": False,
            "variants": ["stoicism", "stoic character"],
        },
        {
            "text": "from youth",
            "role": "important",
            "is_phrase": False,
            "variants": ["youthful", "in his youth", "young George Washington"],
        },
        {
            "text": "key features",
            "role": "important",
            "is_phrase": False,
            "variants": ["characteristics", "qualities"],
        },
        {
            "text": "On the Glorious River",
            "role": "source_reference",
            "is_phrase": True,
            "variants": [],
        },
        {
            "text": "Steve Young",
            "role": "source_reference",
            "is_phrase": True,
            "variants": [],
        },
    ],
}


new_style_data = {
    "terms": [
        {
            "text": "Q2 slide deck",
            "role": "source_reference",
            "is_phrase": True,
            "variants": [
                "Q2 earnings presentation",
                "Q2 investor deck",
                "second quarter slide deck",
            ],
        },
        {
            "text": "new manufacturing lines",
            "role": "essential",
            "is_phrase": True,
            "variants": [
                "new production lines",
                "new manufacturing facilities",
                "new assembly lines",
            ],
        },
        {
            "text": "robotics",
            "role": "important",
            "is_phrase": False,
            "variants": ["robots", "robotic systems", "automation"],
        },
        {
            "text": "autos",
            "role": "important",
            "is_phrase": False,
            "variants": ["automotive", "automobile", "car manufacturing"],
        },
    ]
}


def render_form(text: str, is_phrase: bool) -> str:
    esc = lambda s: '"' + s.replace('"', '""') + '"'
    words = text.split()
    if is_phrase or len(words) == 1:
        return esc(text)  # "marcus aurelius"
    return "(" + " AND ".join(esc(w) for w in words) + ")"  # ("giving" AND "advice")


def block(term: dict[str, Any]) -> str:
    forms = [render_form(term["text"], term["is_phrase"])]
    forms += [render_form(v, term["is_phrase"]) for v in term["variants"]]
    return "(" + " OR ".join(forms) + ")"


def join(blocks: list[str | None], op: str) -> str | None:
    """Combine block expressions into a single parenthesized clause.

    Args:
        blocks: Candidate expressions to combine; empty ones are dropped.
        op: SQL boolean operator used to join the remaining expressions.

    Returns:
        The combined expression, or None if every block was empty —
        signaling that this group contributed nothing to the query.

    """
    blocks = [b for b in blocks if b]
    if not blocks:
        return None  # important: signals "this group is empty"
    if len(blocks) == 1:
        return blocks[0]
    return "(" + f" {op} ".join(blocks) + ")"


def process_lexical_query(terms: list[dict[str, Any]]) -> dict[str, str]:
    """Build tiered FTS5 MATCH candidates from role-classified search terms.

    Terms are grouped by role into T(arget)/E(ssential)/I(mportant)/
    C(ontextual) blocks, then combined into progressively broader query
    candidates so a caller can fall back from strict to permissive
    matching if a stricter tier returns no results.

    Args:
        terms: Search terms as produced by SearchTerm.model_dump(), each
            with "text", "role", "is_phrase", and "variants" keys.

    Returns:
        Mapping of candidate name ("target", "essential", "core",
        "core_supporting") to its FTS5 MATCH expression. Tiers whose
        expression is empty or duplicates an earlier tier are omitted.

    """

    T: list[str] = [block(t) for t in terms if t["role"] == "target_entity"]
    E: list[str] = [block(t) for t in terms if t["role"] == "essential"]
    I: list[str] = [block(t) for t in terms if t["role"] == "important"]
    C: list[str] = [block(t) for t in terms if t["role"] == "contextual"]

    T_all, T_any = join(T, "AND"), join(T, "OR")
    E_all, E_any = join(E, "AND"), join(E, "OR")
    I_any, C_any = join(I, "OR"), join(C, "OR")

    I_any_OR_C_any = join([I_any, C_any], "OR")

    candidates = [
        ("target", T_any),  # target only
        ("essential", E_any),  # essentials only
        ("core", join([T_any, E_any], "AND")),  # core
        (
            "core_supporting",
            join([T_any, E_any, I_any_OR_C_any], "AND"),
        ),  # core + supporting
    ]

    seen: set[str] = set()
    queries: dict[str, str] = {}

    for x in candidates:
        name, expr = x
        if expr and expr not in seen:
            seen.add(expr)
            queries[name] = expr

    return queries


if __name__ == "__main__":
    searchterms = new_style_data["terms"]
    print(process_lexical_query([x for x in searchterms]))
