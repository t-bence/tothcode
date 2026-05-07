def truncate(s: str, limit: int) -> str:
    return s[:limit] + ("…" if len(s) > limit else "")
