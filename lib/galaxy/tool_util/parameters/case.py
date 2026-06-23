import os
from dataclasses import (
    dataclass,
    replace,
)
from re import compile
from typing import (
    Any,
    cast,
    Dict,
    FrozenSet,
    List,
    Optional,
    Set,
    Tuple,
)

from packaging.version import Version
from typing_extensions import Literal

from galaxy.tool_util.parser.interface import (
    TestCollectionDef,
    ToolSource,
    ToolSourceTest,
    ToolSourceTestInput,
    ToolSourceTestInputs,
    xml_data_input_to_json,
    XmlTestCollectionDefDict,
)
from galaxy.tool_util.parser.util import multiple_select_value_split
from galaxy.tool_util_models.parameters import (
    BooleanParameterModel,
    ConditionalParameterModel,
    ConditionalWhen,
    DataCollectionParameterModel,
    DataColumnParameterModel,
    DataParameterModel,
    FloatParameterModel,
    GenomeBuildParameterModel,
    GroupTagParameterModel,
    IntegerParameterModel,
    iter_parameter_models,
    RepeatParameterModel,
    SectionParameterModel,
    SelectParameterModel,
    ToolParameterT,
)
from galaxy.util import (
    asbool,
    string_as_bool,
)
from .factory import input_models_for_tool_source
from .state import TestCaseToolState
from .visitor import (
    flat_state_path,
    repeat_inputs_to_array,
    validate_explicit_conditional_test_value,
)

INTEGER_STR_PATTERN = compile(r"^(\d+)$")
INTEGERS_STR_PATTERN = compile(r"^(\d+)(\s*,\s*(\d+))*$")
COLUMN_NAME_STR_PATTERN = compile(r"^c(\d+): .*$")
# In an effort to squeeze all the ambiguity out of test cases - at some point Marius and John
# agree tools should be using value_json for typed inputs to parameters but John has come around on
# this now that we're validating the parameters as a whole on load. The models are ensuring only
# unambigious test cases are being loaded.
WARN_ON_UNTYPED_XML_STRINGS = False


@dataclass
class TestCaseStateAndWarnings:
    tool_state: TestCaseToolState
    warnings: List[str]
    unhandled_inputs: List[str]


@dataclass
class TestCaseStateValidationResult:
    tool_state: TestCaseToolState
    warnings: List[str]
    validation_error: Optional[Exception]
    tool_parameter_bundle: List[ToolParameterT]
    profile: str

    def to_dict(self):
        tool_state_json = self.tool_state.input_state
        warnings = self.warnings
        validation_error = str(self.validation_error) if self.validation_error else None
        return {
            "tool_state": tool_state_json,
            "warnings": warnings,
            "validation_error": validation_error,
            "validated_with_profile": self.profile,
        }


def legacy_from_string(parameter: ToolParameterT, value: Optional[Any], warnings: List[str], profile: str) -> Any:
    """Convert string values in XML test cases into typed variants.

    This should only be used when parsing XML test cases into a TestCaseToolState object.
    We have to maintain backward compatibility on these for older Galaxy tool profile versions.
    """
    result_value: Any = value
    if isinstance(value, str):
        if isinstance(parameter, (IntegerParameterModel,)):
            if WARN_ON_UNTYPED_XML_STRINGS:
                warnings.append(
                    f"Implicitly converted {parameter.name} to an integer from a string value, please use 'value_json' to define this test input parameter value instead."
                )
            result_value = int(value)
        elif isinstance(parameter, (FloatParameterModel,)):
            if WARN_ON_UNTYPED_XML_STRINGS:
                warnings.append(
                    f"Implicitly converted {parameter.name} to a floating point number from a string value, please use 'value_json' to define this test input parameter value instead."
                )
            result_value = float(value)
        elif isinstance(parameter, (BooleanParameterModel,)):
            if WARN_ON_UNTYPED_XML_STRINGS:
                warnings.append(
                    f"Implicitly converted {parameter.name} to a boolean from a string value, please use 'value_json' to define this test input parameter value instead."
                )
            # Map the parameter's truevalue/falsevalue back to a boolean when the test
            # specified the command-line string rather than 'true'/'false', so the
            # submitted payload is a real boolean.
            if parameter.truevalue is not None and value == parameter.truevalue:
                result_value = True
            elif parameter.falsevalue is not None and value == parameter.falsevalue:
                result_value = False
            else:
                try:
                    result_value = asbool(value)
                except ValueError:
                    if Version(profile) < Version("24.2"):
                        # Coerce a legacy non-boolean placeholder (e.g. "-") via string_as_bool
                        # (any non-true value -> False), matching the synchronous tool API.
                        result_value = string_as_bool(value)
                        warnings.append(
                            f"Non-boolean test value ({value!r}) for {parameter.name} coerced to "
                            f"{result_value} - use 'true' or 'false'."
                        )
                    else:
                        warnings.append(
                            "Likely using deprected truevalue/falsevalue in tool parameter - switch to 'true' or 'false'"
                        )
        elif isinstance(parameter, (GroupTagParameterModel,)):
            if parameter.multiple:
                result_value = multiple_select_value_split(value)
        elif isinstance(parameter, (GenomeBuildParameterModel,)):
            if parameter.multiple:
                result_value = multiple_select_value_split(value)
        elif isinstance(parameter, SelectParameterModel):
            if parameter.multiple and Version(profile) < Version("26.1"):
                # value="" is a legacy convention for "nothing selected"; filter empty parts to produce [].
                # Tools with profile >= 26.1 must use value_json="[]" explicitly.
                result_value = multiple_select_value_split(value)
                if Version(profile) < Version("24.2"):
                    result_value = [_legacy_select_label_to_value(parameter, v) for v in result_value]
            elif Version(profile) < Version("24.2"):
                result_value = _legacy_select_label_to_value(parameter, value)
        elif isinstance(parameter, (DataColumnParameterModel,)):
            if parameter.multiple:
                integers_match = INTEGER_STR_PATTERN.match(value)
                if integers_match:
                    if WARN_ON_UNTYPED_XML_STRINGS:
                        warnings.append(
                            f"Implicitly converted {parameter.name} to a column index integer from a string value, please use 'value_json' to define this test input parameter value instead."
                        )
                    result_value = [int(v.strip()) for v in value.split(",")]
            else:
                integer_match = INTEGER_STR_PATTERN.match(value)
                if integer_match:
                    if WARN_ON_UNTYPED_XML_STRINGS:
                        warnings.append(
                            f"Implicitly converted {parameter.name} to a column index integer from a string value, please use 'value_json' to define this test input parameter value instead."
                        )
                    result_value = int(value)
                elif Version(profile) < Version("24.2"):
                    # allow this for older tools but new tools will just require the integer index
                    warnings.append(
                        f"Using column names as test case values is deprecated, please adjust {parameter.name} to just use an integer column index."
                    )
                    column_name_value_match = COLUMN_NAME_STR_PATTERN.match(value)
                    if column_name_value_match:
                        column_part = column_name_value_match.group(1)
                        result_value = int(column_part)
    return result_value


def _legacy_select_label_to_value(parameter: SelectParameterModel, value: str) -> str:
    if parameter.options is None:
        return value
    for option in parameter.options:
        if option.value == value:
            return value
    for option in parameter.options:
        if option.label == value:
            return option.value
    return value


@dataclass(frozen=True)
class LegacyTestInputResolver:
    """Resolve a (possibly legacy/unqualified) parameter path to the test input that supplies it.

    Owns the raw test inputs and the set of discriminator names already consumed by enclosing
    conditionals, and encapsulates the fuzzy fallback cascade legacy test cases rely on (exact
    name, then suffix / bare short-name / elided-conditional matches). A consumed discriminator
    is excluded from those fallbacks so a nested conditional does not re-match an ancestor's
    discriminator of the same name.

    Immutable: ``consuming`` and ``for_inputs`` return child resolvers, so an exclusion stays
    scoped to one subtree of the parameter walk (a sibling subtree never sees it) and a repeat
    instance can be resolved against its own slice of the inputs.
    """

    inputs: ToolSourceTestInputs
    consumed_discriminators: FrozenSet[str] = frozenset()

    def consuming(self, discriminator_name: Optional[str]) -> "LegacyTestInputResolver":
        if discriminator_name is None:
            return self
        return replace(self, consumed_discriminators=self.consumed_discriminators | {discriminator_name})

    def for_inputs(self, inputs: ToolSourceTestInputs) -> "LegacyTestInputResolver":
        return replace(self, inputs=inputs)

    def input_for(self, flat_state_path: str) -> Optional[ToolSourceTestInput]:
        # Discriminators consumed by enclosing conditionals are excluded from the loose fallbacks
        # below, so a descendant's omitted discriminator does not re-match an ancestor's.
        exclude = self.consumed_discriminators
        for input in self.inputs:
            if input["name"] == flat_state_path:
                return input
        # Fallback for legacy test cases that specify conditional/section params without the
        # pipe-separated prefix (e.g. <param name="fasta"> instead of <param name="mode|fasta">).
        if "|" in flat_state_path:
            suffix_matching_inputs = [
                input
                for input in self.inputs
                if "|" in input["name"]
                and input["name"] not in exclude
                and _path_ends_with_param(flat_state_path, input["name"])
            ]
            resolved = _resolve_matching_inputs(
                suffix_matching_inputs, f"Ambiguous partially qualified test parameter name for ({flat_state_path})"
            )
            if resolved is not None:
                return resolved

            short_name = flat_state_path.rsplit("|", 1)[1]
            matching_inputs = [
                input for input in self.inputs if input["name"] == short_name and input["name"] not in exclude
            ]
            resolved = _resolve_matching_inputs(
                matching_inputs, f"Ambiguous unqualified test parameter name ({short_name}) for ({flat_state_path})"
            )
            if resolved is not None:
                return resolved

            # Fallback for legacy test cases that elide intermediate conditional names but keep
            # the enclosing section/repeat prefix (e.g. <section name="adv"><param name="esf">
            # for a param whose real path is adv|esf_cond|esf). The input name is an ordered
            # subsequence of the qualified path - sharing the head and the leaf - rather than a
            # plain suffix.
            path_segments = flat_state_path.split("|")
            elided_matching_inputs = [
                input
                for input in self.inputs
                if input["name"] not in exclude and _is_conditional_elided_match(input["name"], path_segments)
            ]
            resolved = _resolve_matching_inputs(
                elided_matching_inputs, f"Ambiguous partially qualified test parameter name for ({flat_state_path})"
            )
            if resolved is not None:
                return resolved
        return None


@dataclass(frozen=True)
class MergeContext:
    """The values threaded unchanged through the recursive test-case merge.

    Bundling them keeps ``_merge_into_state`` and friends to their per-node arguments
    (the parameter, the state at this level, the prefix) instead of re-passing the
    resolver, profile, state representation and warnings at every call site. ``warnings``
    is a shared list accumulated across the whole merge; ``consuming`` / ``for_inputs``
    return a child context whose resolver is scoped to a conditional branch or repeat
    instance.
    """

    resolver: LegacyTestInputResolver
    profile: str
    state_representation: Literal["test_case_xml", "test_case_json"]
    warnings: List[str]

    @property
    def inputs(self) -> ToolSourceTestInputs:
        return self.resolver.inputs

    def input_for(self, flat_state_path: str) -> Optional[ToolSourceTestInput]:
        return self.resolver.input_for(flat_state_path)

    def consuming(self, discriminator_name: Optional[str]) -> "MergeContext":
        return replace(self, resolver=self.resolver.consuming(discriminator_name))

    def for_inputs(self, inputs: ToolSourceTestInputs) -> "MergeContext":
        return replace(self, resolver=self.resolver.for_inputs(inputs))


def test_case_state(
    test_dict: ToolSourceTest,
    tool_parameter_bundle: List[ToolParameterT],
    profile: str,
    validate: bool = True,
    name: Optional[str] = None,
) -> TestCaseStateAndWarnings:
    warnings: List[str] = []
    inputs: ToolSourceTestInputs = test_dict["inputs"]
    unhandled_inputs = []
    state: Dict[str, Any] = {}

    state_representation = test_dict.get("value_state_representation", "test_case_xml")
    context = MergeContext(LegacyTestInputResolver(inputs), profile, state_representation, warnings)
    handled_inputs = _merge_level_into_state(tool_parameter_bundle, context, state, None)

    for test_input in inputs:
        input_name = test_input["name"]
        if input_name not in handled_inputs:
            unhandled_inputs.append(input_name)

    tool_state = TestCaseToolState(state)
    if validate:
        tool_state.validate(tool_parameter_bundle, name=name)
        for input_name in unhandled_inputs:
            if not _input_name_was_handled_by_legacy_fallback(input_name, handled_inputs, profile):
                raise Exception(f"Invalid parameter name found {input_name}")
    return TestCaseStateAndWarnings(tool_state, warnings, unhandled_inputs)


def _input_name_was_handled_by_legacy_fallback(input_name: str, handled_inputs: Set[str], profile: str) -> bool:
    """True if a pre-24.2 legacy fallback already covered input_name (loose suffix-match).

    The match is deliberately loose - against every visited path, not consumed inputs - because
    the raw-name->path relation is many-to-many for legacy tests (bare/duplicate names validly
    satisfy multiple params). Only applies below profile 24.2.
    """
    if Version(profile) >= Version("24.2"):
        return False
    for handled_input in handled_inputs:
        if handled_input == input_name or _path_ends_with_param(handled_input, input_name):
            return True
        # conditional names may be elided in the test while the section/repeat prefix is kept
        if "|" in input_name and _is_conditional_elided_match(input_name, handled_input.split("|")):
            return True
    return False


def test_case_validation(
    test_dict: ToolSourceTest, tool_parameter_bundle: List[ToolParameterT], profile: str, name: Optional[str] = None
) -> TestCaseStateValidationResult:
    test_case_state_and_warnings = test_case_state(test_dict, tool_parameter_bundle, profile, validate=False)
    exception: Optional[Exception] = None
    try:
        test_case_state_and_warnings.tool_state.validate(tool_parameter_bundle, name=name)
        for input_name in test_case_state_and_warnings.unhandled_inputs:
            raise Exception(f"Invalid parameter name found {input_name}")
    except Exception as e:
        exception = e
    return TestCaseStateValidationResult(
        test_case_state_and_warnings.tool_state,
        test_case_state_and_warnings.warnings,
        exception,
        tool_parameter_bundle,
        profile,
    )


def _merge_level_into_state(
    tool_inputs: List[ToolParameterT],
    context: MergeContext,
    state_at_level: dict,
    prefix: Optional[str],
) -> Set[str]:
    handled_inputs: Set[str] = set()
    for tool_input in tool_inputs:
        handled_inputs.update(_merge_into_state(tool_input, context, state_at_level, prefix))

    return handled_inputs


def _inputs_as_dict(inputs: ToolSourceTestInputs) -> Dict[str, ToolSourceTestInput]:
    as_dict: Dict[str, ToolSourceTestInput] = {}
    for input in inputs:
        as_dict[input["name"]] = input

    return as_dict


def _merge_into_state(
    tool_input: ToolParameterT,
    context: MergeContext,
    state_at_level: dict,
    prefix: Optional[str],
) -> Set[str]:
    handled_inputs = set()

    input_name = tool_input.name
    state_path = flat_state_path(input_name, prefix)
    handled_inputs.add(state_path)

    if isinstance(tool_input, (ConditionalParameterModel,)):
        conditional_state = state_at_level.get(input_name, {})
        if input_name not in state_at_level:
            state_at_level[input_name] = conditional_state

        when, discriminator_name = _select_which_when(tool_input, conditional_state, context, state_path)
        test_parameter = tool_input.test_parameter
        handled_inputs.update(_merge_into_state(test_parameter, context, conditional_state, state_path))
        # If the discriminator was omitted, record the when _select_which_when chose so the state
        # validates against that branch rather than the phantom __absent__ branch.
        if test_parameter.name not in conditional_state and when.discriminator is not None:
            conditional_state[test_parameter.name] = when.discriminator
        # Mark this conditional's discriminator consumed so a nested conditional's loose fallbacks
        # do not re-match it.
        handled_inputs.update(
            _merge_level_into_state(
                when.parameters, context.consuming(discriminator_name), conditional_state, state_path
            )
        )
    elif isinstance(tool_input, (RepeatParameterModel,)):
        repeat_state_array = state_at_level.get(input_name, [])
        if input_name not in state_at_level:
            state_at_level[input_name] = repeat_state_array

        repeat_instance_inputs = _repeat_inputs_to_array(state_path, tool_input.parameters, context.inputs)
        if tool_input.min is not None:
            while len(repeat_instance_inputs) < tool_input.min:
                repeat_instance_inputs.append([])
        for i, _ in enumerate(repeat_instance_inputs):
            while len(repeat_state_array) <= i:
                repeat_state_array.append({})

            repeat_instance_prefix = f"{state_path}_{i}"
            handled_inputs.update(
                _merge_level_into_state(
                    tool_input.parameters,
                    context.for_inputs(repeat_instance_inputs[i]),
                    repeat_state_array[i],
                    repeat_instance_prefix,
                )
            )
    elif isinstance(tool_input, (SectionParameterModel,)):
        section_state = state_at_level.get(input_name, {})
        if input_name not in state_at_level:
            state_at_level[input_name] = section_state

        handled_inputs.update(_merge_level_into_state(tool_input.parameters, context, section_state, state_path))
    else:
        test_input = context.input_for(state_path)
        if test_input is not None:
            input_value: Any
            if isinstance(tool_input, (DataCollectionParameterModel,)):
                input_value = TestCollectionDef.from_dict(
                    cast(XmlTestCollectionDefDict, test_input.get("attributes", {}).get("collection"))
                ).test_format_to_dict()
            elif isinstance(tool_input, (DataParameterModel,)):
                if tool_input.multiple:
                    value = test_input["value"]
                    input_value_list: List[Any] = []
                    if value:
                        if context.state_representation == "test_case_json":
                            input_value_list = test_input["value"] if test_input["value"] is not None else []
                        else:
                            location = test_input.get("attributes", {}).get("location")
                            if location:
                                # location may be a comma-separated list of URLs; split per URL
                                for single_location in location.split(","):
                                    single_location = single_location.strip()
                                    instance_test_input = cast(ToolSourceTestInput, dict(test_input))
                                    instance_test_input["attributes"] = dict(test_input["attributes"])
                                    instance_test_input["value"] = os.path.basename(single_location)
                                    instance_test_input["attributes"]["location"] = single_location
                                    input_value_json = xml_data_input_to_json(instance_test_input)
                                    input_value_list.append(input_value_json)
                            else:
                                test_input_values = cast(str, value).split(",")
                                for test_input_value in test_input_values:
                                    instance_test_input = test_input.copy()
                                    instance_test_input["value"] = test_input_value
                                    input_value_json = xml_data_input_to_json(instance_test_input)
                                    input_value_list.append(input_value_json)

                    input_value = input_value_list
                else:
                    if context.state_representation == "test_case_json":
                        input_value = test_input["value"]
                    else:
                        input_value = xml_data_input_to_json(test_input)
            else:
                input_value = test_input["value"]
                input_value = legacy_from_string(tool_input, input_value, context.warnings, context.profile)

            state_at_level[input_name] = input_value

    return handled_inputs


def _repeat_inputs_to_array(
    state_path: str, parameters: List[ToolParameterT], inputs: ToolSourceTestInputs
) -> List[ToolSourceTestInputs]:
    inputs_as_dict = _inputs_as_dict(inputs)
    repeat_instance_input_dicts = repeat_inputs_to_array(state_path, inputs_as_dict)
    if not repeat_instance_input_dicts and "|" in state_path:
        # A legacy test may name a repeat inside a conditional/section by its unqualified name.
        # Progressively strip leading conditional/section segments (longest candidate first, to
        # avoid an unrelated like-named repeat) until the repeat's params resolve; input_for()'s
        # suffix match re-attaches them to the qualified path.
        parts = state_path.split("|")
        for start in range(1, len(parts)):
            candidate_path = "|".join(parts[start:])
            repeat_instance_input_dicts = repeat_inputs_to_array(candidate_path, inputs_as_dict)
            if repeat_instance_input_dicts:
                break
    repeat_instance_inputs = [list(instance_inputs.values()) for instance_inputs in repeat_instance_input_dicts]
    if repeat_instance_inputs:
        return repeat_instance_inputs

    legacy_repeat_inputs: List[ToolSourceTestInputs] = []
    for parameter in parameters:
        parameter_name = parameter.name
        matching_inputs = [input for input in inputs if input["name"] == parameter_name]
        for i, input in enumerate(matching_inputs):
            while len(legacy_repeat_inputs) <= i:
                legacy_repeat_inputs.append([])
            synthetic_input = cast(ToolSourceTestInput, dict(input))
            synthetic_input["name"] = f"{state_path}_{i}|{parameter_name}"
            legacy_repeat_inputs[i].append(synthetic_input)
    return legacy_repeat_inputs


def _select_which_when(
    conditional: ConditionalParameterModel,
    state: dict,
    context: MergeContext,
    prefix: str,
) -> Tuple[ConditionalWhen, Optional[str]]:
    """Return the selected when and the name of the test input used as the discriminator
    (or ``None`` if the discriminator was omitted). The discriminator name lets callers mark
    it consumed so descendant conditionals do not re-match it via the loose fallbacks."""
    test_parameter = conditional.test_parameter
    is_boolean = test_parameter.parameter_type == "gx_boolean"
    test_parameter_name = test_parameter.name
    test_parameter_flat_path = flat_state_path(test_parameter_name, prefix)

    test_input = context.input_for(test_parameter_flat_path)
    matched_name = test_input["name"] if test_input else None
    explicit_test_value = test_input["value"] if test_input else None
    if is_boolean and isinstance(explicit_test_value, str):
        explicit_test_value = asbool(explicit_test_value)
    test_value = validate_explicit_conditional_test_value(test_parameter_name, explicit_test_value)
    if test_value is None:
        # Discriminator omitted: infer the active when from the params the test provides (like
        # the synchronous tool API) before falling back to the default when.
        inferred_when = _infer_when_from_inputs(conditional, context.inputs, prefix)
        if inferred_when is not None:
            return inferred_when, matched_name
    for when in conditional.whens:
        if test_value is None and when.is_default_when:
            return when, matched_name
        elif test_value == when.discriminator:
            return when, matched_name
    raise Exception(f"Invalid conditional test value ({explicit_test_value}) for parameter ({test_parameter_name})")


def _leaf_param_short_names(parameters: List[ToolParameterT]) -> Set[str]:
    """Collect the leaf parameter short names reachable from a list of parameters,
    descending into repeats, sections and nested conditionals (including each
    conditional's discriminator)."""
    return {
        parameter.name
        for parameter in iter_parameter_models(parameters)
        if not isinstance(parameter, (RepeatParameterModel, SectionParameterModel, ConditionalParameterModel))
    }


def _infer_when_from_inputs(
    conditional: ConditionalParameterModel, inputs: ToolSourceTestInputs, prefix: Optional[str]
) -> Optional[ConditionalWhen]:
    """When a conditional's discriminator is omitted, pick the when whose parameters the
    test supplies. Returns the best-matching when only when it is a strictly better match
    than the default when; otherwise None so the caller uses the default when."""
    scope = f"{prefix}|" if prefix else ""
    provided_short_names: Set[str] = set()
    for input in inputs:
        name = input["name"]
        # Consider inputs scoped to this conditional, plus legacy unqualified (bare) inputs -
        # a test may supply a non-default branch's param by its short name without the
        # enclosing conditional prefix (e.g. <param name="reference"> for
        # reference_cond|reference). Skip only inputs qualified to a *different* prefix.
        if scope and not name.startswith(scope) and "|" in name:
            continue
        provided_short_names.add(name.rsplit("|", 1)[-1])
    if not provided_short_names:
        return None

    best_when: Optional[ConditionalWhen] = None
    best_score = 0
    default_score = 0
    for when in conditional.whens:
        score = len(_leaf_param_short_names(when.parameters) & provided_short_names)
        if when.is_default_when:
            default_score = score
        if score > best_score:
            best_score = score
            best_when = when
    if best_when is not None and best_score > default_score:
        return best_when
    return None


def _resolve_matching_inputs(
    matching_inputs: List[ToolSourceTestInput], ambiguity_message: str
) -> Optional[ToolSourceTestInput]:
    """Resolve a list of test inputs that matched a parameter to a single input.

    Returns None when nothing matched (so the caller can try the next fallback). A single
    match is returned directly. Multiple matches are tolerated when they are equivalent -
    a duplicate identical entry is a common test-authoring slip and the synchronous tool
    API accepts it - but genuinely conflicting values raise.
    """
    if not matching_inputs:
        return None
    first = matching_inputs[0]
    if len(matching_inputs) == 1:
        return first
    if all(
        input.get("value") == first.get("value") and input.get("attributes") == first.get("attributes")
        for input in matching_inputs[1:]
    ):
        return first
    raise Exception(ambiguity_message)


def _path_ends_with_param(qualified_path: str, param_name: str) -> bool:
    """True if ``param_name`` is the trailing (pipe-separated) segment(s) of ``qualified_path``.

    The legacy unqualified/partially-qualified suffix match, shared by ``input_for`` and
    ``_input_name_was_handled_by_legacy_fallback`` so the rule lives in one place.
    """
    return qualified_path.endswith(f"|{param_name}")


def _is_conditional_elided_match(input_name: str, path_segments: List[str]) -> bool:
    """True if ``input_name`` is the qualified ``path_segments`` with intermediate
    (conditional) segments removed - sharing the head and leaf segments.

    e.g. input_name "advanced_options|esf" matches path ["advanced_options", "esf_cond", "esf"].
    """
    input_segments = input_name.split("|")
    if len(input_segments) < 2 or len(input_segments) >= len(path_segments):
        return False
    if input_segments[0] != path_segments[0] or input_segments[-1] != path_segments[-1]:
        return False
    path_iter = iter(path_segments)
    return all(segment in path_iter for segment in input_segments)


def validate_test_cases_for_tool_source(
    tool_source: ToolSource, use_latest_profile: bool = False, name: Optional[str] = None
) -> List[TestCaseStateValidationResult]:
    name = name or f"PydanticModelFor[{tool_source.parse_id()}]"
    tool_parameter_bundle = input_models_for_tool_source(tool_source)
    if use_latest_profile:
        # this might get old but it is fine, just needs to be updated when test case changes are made
        profile = "26.1"
    else:
        profile = tool_source.parse_profile()
    test_cases: List[ToolSourceTest] = tool_source.parse_tests_to_dict()["tests"]
    results_by_test: List[TestCaseStateValidationResult] = []
    for test_case in test_cases:
        validation_result = test_case_validation(test_case, tool_parameter_bundle.parameters, profile, name=name)
        results_by_test.append(validation_result)
    return results_by_test
