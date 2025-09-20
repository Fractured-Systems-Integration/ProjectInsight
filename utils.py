def bytes_to_gb(b):
    """Converts bytes to gigabytes."""
    return b // (2 ** 30)

def safe_int(value, fallback=0):
    """
    Safely convert a string to an integer.
    Returns `fallback` if conversion fails.
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return fallback
