def every_other_word(path: str) -> list[tuple[str, str, bool]]:
    with open(path) as f:
        contents = f.read()
    return [(r.strip(), r.strip(), False) for (i, r) in enumerate(contents.split()) if i % 2 == 0]
