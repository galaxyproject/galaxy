from pydantic import ConfigDict

alias_lookup = {
    "assert_contents": "asserts",
    "element": "element_tests",
}


class BaseSetting:
    __pydantic_config__ = ConfigDict(
        extra="forbid", alias_generator=lambda field_name: alias_lookup.get(field_name, field_name)
    )
