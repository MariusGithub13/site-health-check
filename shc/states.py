"""Three states per check. A failed or missing measurement is never 'passed'."""
PASSED, FAILED, UNKNOWN = "passed", "failed", "unknown"

DEFAULT_PAGES, HARD_MAX_PAGES = 10, 25


def aggregate(states):
    """failed beats unknown beats passed. An empty list is unknown: nothing was measured."""
    states = list(states)
    if FAILED in states:
        return FAILED
    if not states or UNKNOWN in states:
        return UNKNOWN
    return PASSED


def clamp_pages(value, default=DEFAULT_PAGES, hard_max=HARD_MAX_PAGES):
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(n, hard_max))
