import re


def sanitize_symbol(symbol: str) -> str:
    return re.sub(r'[\/\\\:\*\?\"\<\>\|]', '_', symbol)