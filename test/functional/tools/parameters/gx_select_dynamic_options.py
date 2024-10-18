from typing import (
    List,
    Tuple,
)


def every_other_word(path: str) -> List[Tuple[str, str, bool]]:
    with open(path, "r") as f:
        contents = f.read()
    return [(r.strip(), r.strip(), False) for (i, r) in enumerate(contents.split()) if i % 2 == 0]
