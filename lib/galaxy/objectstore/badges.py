from typing import (
    Any,
    Dict,
    List,
    Optional,
    Set,
    Union,
)

from typing_extensions import (
    Literal,
    NotRequired,
    TypedDict,
)

BadgeSourceT = Literal["admin", "galaxy"]
# Badges that can be explicitly set by admins.
AdminBadgeT = Literal[
    "faster",
    "slower",
    "short_term",
    "backed_up",
    "not_backed_up",
    "more_secure",
    "less_secure",
    "more_stable",
    "less_stable",
]

# All badges - so AdminBadgeT plus Galaxy specifiable badges.
BadgeT = Union[
    AdminBadgeT,
    Literal[
        "cloud",
        "quota",
        "no_quota",
        "restricted",
        "user_defined",
    ],
]


class BadgeSpecDict(TypedDict):
    """Describe badges that can be set by Galaxy admins."""

    type: AdminBadgeT
    conflicts: List[AdminBadgeT]


BADGE_SPECIFICATION: List[BadgeSpecDict] = [
    {"type": "faster", "conflicts": ["slower"]},
    {"type": "slower", "conflicts": ["faster"]},
    {"type": "short_term", "conflicts": []},
    {"type": "backed_up", "conflicts": ["not_backed_up"]},
    {"type": "not_backed_up", "conflicts": ["backed_up"]},
    {"type": "more_secure", "conflicts": ["less_secure"]},
    {"type": "less_secure", "conflicts": ["more_secure"]},
    {"type": "more_stable", "conflicts": ["less_stable"]},
    {"type": "less_stable", "conflicts": ["more_stable"]},
]

KNOWN_BADGE_TYPES: List[AdminBadgeT] = [s["type"] for s in BADGE_SPECIFICATION]
BADGE_SPECIFICATION_BY_TYPE: Dict[AdminBadgeT, BadgeSpecDict] = {s["type"]: s for s in BADGE_SPECIFICATION}


class BadgeDict(TypedDict):
    type: BadgeT
    message: Optional[str]
    source: BadgeSourceT


class StoredBadgeDict(TypedDict):
    type: AdminBadgeT
    message: NotRequired[Optional[str]]


def read_badges(config_dict: Dict[str, Any]) -> List[StoredBadgeDict]:
    raw_badges = config_dict.get("badges") or []
    badges: List[StoredBadgeDict] = []
    badge_types: Set[str] = set()
    badge_conflicts: Dict[str, str] = {}
    for badge in raw_badges:
        # when recovering serialized badges, skip ones that are set by Galaxy
        badge_source = badge.get("source")
        if badge_source and badge_source != "admin":
            continue

        assert "type" in badge
        badge_type = badge["type"]
        if badge_type not in KNOWN_BADGE_TYPES:
            raise Exception(f"badge_type {badge_type} unimplemented/unknown {badge}")
        message = badge.get("message", None)
        badges.append({"type": badge_type, "message": message})
        badge_types.add(badge_type)
        if badge_type in badge_conflicts:
            conflicting_badge_type = badge_conflicts[badge_type]
            raise Exception(
                f"Conflicting badge to [{badge_type}] defined on the object store [{conflicting_badge_type}]."
            )
        conflicts = BADGE_SPECIFICATION_BY_TYPE[badge_type]["conflicts"]
        for conflict in conflicts:
            badge_conflicts[conflict] = badge_type
    return badges


def serialize_badges(
    stored_badges: List[StoredBadgeDict], quota_enabled: bool, private: bool, user_defined: bool, cloud: bool
) -> List[BadgeDict]:
    """Produce blended, unified list of badges for target object store entity.

    Combine more free form admin information stored about badges with Galaxy tracked
    information (quota and access restriction information) to produce a unified list
    of badges to be consumed via the API.
    """
    badge_dicts: List[BadgeDict] = []
    for badge in stored_badges:
        badge_dict: BadgeDict = {
            "source": "admin",
            "type": badge["type"],
            "message": badge.get("message"),
        }
        badge_dicts.append(badge_dict)

    quota_badge_dict: BadgeDict
    if quota_enabled:
        quota_badge_dict = {
            "type": "quota",
            "message": None,
            "source": "galaxy",
        }
    else:
        quota_badge_dict = {
            "type": "no_quota",
            "message": None,
            "source": "galaxy",
        }
    badge_dicts.append(quota_badge_dict)
    if private:
        restricted_badge_dict: BadgeDict = {
            "type": "restricted",
            "message": None,
            "source": "galaxy",
        }
        badge_dicts.append(restricted_badge_dict)
    if user_defined:
        user_defined_badge_dict: BadgeDict = {
            "type": "user_defined",
            "message": None,
            "source": "galaxy",
        }
        badge_dicts.append(user_defined_badge_dict)
    if cloud:
        cloud_badge_dict: BadgeDict = {
            "type": "cloud",
            "message": None,
            "source": "galaxy",
        }
        badge_dicts.append(cloud_badge_dict)
    return badge_dicts
