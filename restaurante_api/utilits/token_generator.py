# utils/token_generator.py
import secrets


def generate_numeric_token(length: int = 6) -> str:
    """Gera token numérico seguro."""
    min_value = 10 ** (length - 1)
    max_value = (10**length) - 1
    return str(secrets.randbelow(max_value - min_value + 1) + min_value)
