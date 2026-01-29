import random
import string


def random_str() -> str:
    alphabet = string.ascii_lowercase + string.digits
    size = random.randint(5, 10)
    return "".join(random.choices(alphabet, k=size))


def random_email() -> str:
    text = random_str()
    return f"{text}@galaxy.testing"
