from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from typing_extensions import (
    Literal,
    Protocol,
)

Impact = Literal["minor", "moderate", "serious", "critical"]

# Axe tests we want to actively pass in Galaxy, the next list controls tests.
BASELINE_AXE_PASSING_IDS = [
    "aria-roles",
]

# check all violations of this level as a baseline 'impact'...
BASELINE_VIOLATION_FILTER: Impact = "critical"
FORMS_VIOLATIONS = ["duplicate-id-aria"]  # https://github.com/galaxyproject/galaxy/issues/16188
# unless they are in this list...
KNOWN_VIOLATIONS = FORMS_VIOLATIONS + [
    "aria-required-attr",
    "aria-required-children",
    "aria-required-parent",
    "image-alt",  # test_workflow_editor.py::TestWorkflowEditor::test_existing_connections
    "label",
    "button-name",
    "select-name",
]
# Over time we hope known violations grows smaller until the violation
# filter can be lowered. Next level would be "serious".
# xref https://github.com/galaxyproject/galaxy/issues/16185


class AxeResult:
    def __init__(self, json: Dict[str, Any]):
        self._json = json

    @property
    def id(self) -> str:
        return self._json["id"]

    @property
    def description(self) -> str:
        return self._json["description"]

    @property
    def impact(self) -> Optional[Impact]:
        return self._json["impact"]

    @property
    def nodes(self):
        return self._json["nodes"]

    def is_impact_at_least(self, impact: Impact) -> bool:
        range_of_impacts = []
        if impact == "minor":
            range_of_impacts = ["minor", "moderate", "serious", "critical"]
        elif impact == "moderate":
            range_of_impacts = ["moderate", "serious", "critical"]
        elif impact == "serious":
            range_of_impacts = ["serious", "critical"]
        elif impact == "critical":
            range_of_impacts = ["critical"]
        return self.impact in range_of_impacts


class Violation(AxeResult):
    @property
    def message(self) -> str:
        nodes = self.nodes
        nodes_str = ", ".join([n["html"] for n in nodes])
        return f"AXE accessibility test violation found [{self.id}] with impact {self.impact}: {self.description}. Problem found in {nodes_str}."


class AxeResults(Protocol):
    def assert_passes(self, id: str) -> None:
        """"""

    def assert_does_not_violate(self, id: str) -> None:
        """"""

    def violations(self) -> List[Violation]:
        """"""

    # these next two could be refactored into a mixin...
    def violations_with_impact_of_at_least(self, impact: Impact) -> List[Violation]:
        """"""

    def assert_no_violations_with_impact_of_at_least(
        self, impact: Impact, excludes: Optional[List[str]] = None
    ) -> None:
        """"""


class RealAxeResults(AxeResults):
    def __init__(self, json: Dict[str, Any]):
        self._json = json

    def assert_passes(self, id: str) -> None:
        passing_results = self._json["passes"]
        result = _check_list_for_id(passing_results, id)
        assert result

    def assert_does_not_violate(self, id: str) -> None:
        violations = self._json["violations"]
        if result := _check_list_for_id(violations, id):
            violation = Violation(result)
            raise AssertionError(violation.message)

    def violations(self) -> List[Violation]:
        violations = self._json["violations"]
        return [Violation(v) for v in violations]

    def violations_with_impact_of_at_least(self, impact: Impact) -> List[Violation]:
        return [v for v in self.violations() if v.is_impact_at_least(impact)]

    def assert_no_violations_with_impact_of_at_least(
        self, impact: Impact, excludes: Optional[List[str]] = None
    ) -> None:
        excludes = excludes or []
        violations = self.violations_with_impact_of_at_least(impact)
        filtered_violations = [v for v in violations if v.id not in excludes]
        if filtered_violations:
            raise AssertionError(filtered_violations[0].message)


class NullAxeResults(AxeResults):
    """All assertions just pass because we're skipping Axe evaluation."""

    def assert_passes(self, id: str) -> None:
        pass

    def assert_does_not_violate(self, id: str) -> None:
        pass

    def violations(self) -> List[Violation]:
        return []

    # these next two could be refactored into a mixin...
    def violations_with_impact_of_at_least(self, impact: Impact) -> List[Violation]:
        return []

    def assert_no_violations_with_impact_of_at_least(
        self, impact: Impact, excludes: Optional[List[str]] = None
    ) -> None:
        pass


def assert_baseline_accessible(axe_results: AxeResults) -> None:
    for passing_id in BASELINE_AXE_PASSING_IDS:
        axe_results.assert_passes(passing_id)
    for violation in axe_results.violations_with_impact_of_at_least(BASELINE_VIOLATION_FILTER):
        violation_id = violation.id
        if violation_id not in KNOWN_VIOLATIONS:
            raise AssertionError(violation.message)


def _check_list_for_id(result_list: List[Dict[str, Any]], id) -> Optional[Dict[str, Any]]:
    for result in result_list:
        if result.get("id") == id:
            return result
    return None
